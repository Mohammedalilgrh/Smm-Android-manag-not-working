from app import scheduler, db
from models import Post, PostQueue, BulkUpload
from social_media_api import post_to_platform
from datetime import datetime, timedelta
import logging
from flask import current_app

def schedule_post(post_id):
    """Schedule a post for publishing"""
    try:
        post = Post.query.get(post_id)
        if not post:
            logging.error(f"Post {post_id} not found")
            return False
        
        # Create job ID
        job_id = f"post_{post_id}_{int(datetime.utcnow().timestamp())}"
        
        # Schedule the job
        scheduler.add_job(
            func=publish_post,
            trigger='date',
            run_date=post.scheduled_for,
            args=[post_id],
            id=job_id,
            replace_existing=True
        )
        
        # Update post with job ID
        post.job_id = job_id
        db.session.commit()
        
        logging.info(f"Post {post_id} scheduled for {post.scheduled_for}")
        return True
    
    except Exception as e:
        logging.error(f"Error scheduling post {post_id}: {e}")
        return False

def publish_post(post_id):
    """Publish a post to all selected platforms"""
    with current_app.app_context():
        try:
            post = Post.query.get(post_id)
            if not post:
                logging.error(f"Post {post_id} not found for publishing")
                return
            
            if post.status != 'scheduled':
                logging.warning(f"Post {post_id} is not in scheduled status: {post.status}")
                return
            
            # Update status to posting
            post.status = 'posting'
            db.session.commit()
            
            platforms = post.get_platforms()
            success_count = 0
            platform_results = {}
            
            for platform in platforms:
                # Create queue item for each platform
                queue_item = PostQueue(
                    post_id=post_id,
                    platform=platform,
                    status='processing'
                )
                db.session.add(queue_item)
                db.session.commit()
                
                # Attempt to post
                result = post_to_platform(post, platform)
                
                if result['success']:
                    success_count += 1
                    platform_results[platform] = result.get('post_id')
                    queue_item.status = 'completed'
                    queue_item.completed_at = datetime.utcnow()
                else:
                    queue_item.status = 'failed'
                    queue_item.error_message = result.get('error', 'Unknown error')
                    queue_item.attempts += 1
                    
                    # Schedule retry if not max attempts
                    if queue_item.attempts < queue_item.max_attempts:
                        queue_item.next_attempt = datetime.utcnow() + timedelta(minutes=30)
                        schedule_retry(queue_item.id)
                
                db.session.commit()
            
            # Update post status
            if success_count == len(platforms):
                post.status = 'posted'
                post.posted_at = datetime.utcnow()
            elif success_count > 0:
                post.status = 'partial'
                post.posted_at = datetime.utcnow()
            else:
                post.status = 'failed'
                post.error_message = 'Failed to post to any platform'
            
            # Store platform post IDs
            if platform_results:
                post.set_platform_post_ids(platform_results)
            
            db.session.commit()
            logging.info(f"Post {post_id} published to {success_count}/{len(platforms)} platforms")
        
        except Exception as e:
            logging.error(f"Error publishing post {post_id}: {e}")
            post = Post.query.get(post_id)
            if post:
                post.status = 'failed'
                post.error_message = str(e)
                db.session.commit()

def schedule_retry(queue_id):
    """Schedule a retry for failed post"""
    try:
        queue_item = PostQueue.query.get(queue_id)
        if not queue_item or not queue_item.next_attempt:
            return
        
        job_id = f"retry_{queue_id}_{int(datetime.utcnow().timestamp())}"
        
        scheduler.add_job(
            func=retry_post,
            trigger='date',
            run_date=queue_item.next_attempt,
            args=[queue_id],
            id=job_id,
            replace_existing=True
        )
        
        logging.info(f"Retry scheduled for queue item {queue_id}")
    
    except Exception as e:
        logging.error(f"Error scheduling retry for queue {queue_id}: {e}")

def retry_post(queue_id):
    """Retry posting to a specific platform"""
    with current_app.app_context():
        try:
            queue_item = PostQueue.query.get(queue_id)
            if not queue_item:
                return
            
            post = queue_item.post
            if not post:
                return
            
            queue_item.status = 'processing'
            queue_item.attempts += 1
            db.session.commit()
            
            # Attempt to post
            result = post_to_platform(post, queue_item.platform)
            
            if result['success']:
                queue_item.status = 'completed'
                queue_item.completed_at = datetime.utcnow()
                
                # Update post platform results
                platform_results = post.get_platform_post_ids()
                platform_results[queue_item.platform] = result.get('post_id')
                post.set_platform_post_ids(platform_results)
                
                # Check if all platforms completed
                total_queue = PostQueue.query.filter_by(post_id=post.id).count()
                completed_queue = PostQueue.query.filter_by(post_id=post.id, status='completed').count()
                
                if completed_queue == total_queue:
                    post.status = 'posted'
                    post.posted_at = datetime.utcnow()
                elif completed_queue > 0 and post.status == 'failed':
                    post.status = 'partial'
                    post.posted_at = datetime.utcnow()
            
            else:
                queue_item.status = 'failed'
                queue_item.error_message = result.get('error', 'Unknown error')
                
                # Schedule another retry if not max attempts
                if queue_item.attempts < queue_item.max_attempts:
                    queue_item.next_attempt = datetime.utcnow() + timedelta(hours=1)
                    schedule_retry(queue_item.id)
            
            db.session.commit()
            logging.info(f"Retry completed for queue item {queue_id}")
        
        except Exception as e:
            logging.error(f"Error in retry for queue {queue_id}: {e}")

def process_bulk_upload(bulk_upload_id, posts_data):
    """Process bulk upload in background"""
    try:
        bulk_upload = BulkUpload.query.get(bulk_upload_id)
        if not bulk_upload:
            return
        
        # Get user's connected platforms
        from models import User
        user = User.query.get(bulk_upload.user_id)
        connected_platforms = user.get_connected_platforms()
        
        # Process each post
        for i, post_data in enumerate(posts_data):
            try:
                # Determine platforms
                requested_platforms = post_data.get('platforms', [])
                if not requested_platforms:
                    # Use all connected platforms if none specified
                    platforms = connected_platforms
                else:
                    # Use only requested platforms that are connected
                    platforms = [p for p in requested_platforms if p in connected_platforms]
                
                if not platforms:
                    bulk_upload.failed_posts += 1
                    continue
                
                # Calculate scheduled time
                if bulk_upload.upload_type == 'daily':
                    # Distribute posts daily starting from start_date
                    days_offset = i
                    scheduled_for = bulk_upload.start_date + timedelta(days=days_offset)
                    # Set time to 9 AM
                    scheduled_for = scheduled_for.replace(hour=9, minute=0, second=0, microsecond=0)
                elif bulk_upload.upload_type == 'immediate':
                    # Schedule all posts within next few minutes
                    scheduled_for = datetime.utcnow() + timedelta(minutes=i * 2)
                else:
                    # Custom scheduling (implement as needed)
                    scheduled_for = datetime.utcnow() + timedelta(hours=i)
                
                # Create post
                post = Post(
                    user_id=bulk_upload.user_id,
                    content=post_data['content'],
                    hashtags=post_data.get('hashtags', ''),
                    scheduled_for=scheduled_for
                )
                post.set_platforms(platforms)
                
                db.session.add(post)
                db.session.commit()
                
                # Schedule the post
                if schedule_post(post.id):
                    bulk_upload.processed_posts += 1
                else:
                    bulk_upload.failed_posts += 1
            
            except Exception as e:
                logging.error(f"Error processing bulk upload post {i}: {e}")
                bulk_upload.failed_posts += 1
        
        # Update bulk upload status
        bulk_upload.status = 'completed'
        bulk_upload.completed_at = datetime.utcnow()
        db.session.commit()
        
        logging.info(f"Bulk upload {bulk_upload_id} completed: {bulk_upload.processed_posts} processed, {bulk_upload.failed_posts} failed")
    
    except Exception as e:
        logging.error(f"Error processing bulk upload {bulk_upload_id}: {e}")
        bulk_upload = BulkUpload.query.get(bulk_upload_id)
        if bulk_upload:
            bulk_upload.status = 'failed'
            bulk_upload.error_message = str(e)
            db.session.commit()
