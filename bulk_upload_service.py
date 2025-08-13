"""
Bulk Upload Service for Social Media Scheduler
Handles CSV/Excel uploads and automatic daily scheduling
"""

import csv
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from werkzeug.datastructures import FileStorage
import os
import logging
from flask import current_app
from app import db
from models import User, Post, BulkUpload, SocialAccount
import json
import threading
import time

logger = logging.getLogger(__name__)

class BulkUploadProcessor:
    """Process bulk uploads and create scheduled posts"""
    
    def __init__(self):
        self.supported_formats = ['.csv', '.xlsx', '.xls']
    
    def validate_file(self, file: FileStorage) -> bool:
        """Validate uploaded file format"""
        if not file or not file.filename:
            return False
        
        ext = os.path.splitext(file.filename)[1].lower()
        return ext in self.supported_formats
    
    def parse_csv_file(self, file_path: str) -> List[Dict[str, Any]]:
        """Parse CSV file and extract post data"""
        posts = []
        
        with open(file_path, 'r', encoding='utf-8') as csvfile:
            # Try to detect delimiter
            sample = csvfile.read(1024)
            csvfile.seek(0)
            
            sniffer = csv.Sniffer()
            delimiter = sniffer.sniff(sample).delimiter
            
            reader = csv.DictReader(csvfile, delimiter=delimiter)
            
            for row_num, row in enumerate(reader, 1):
                try:
                    post_data = self._extract_post_data(row, row_num)
                    if post_data:
                        posts.append(post_data)
                except Exception as e:
                    logger.warning(f"Error parsing row {row_num}: {str(e)}")
                    continue
        
        return posts
    
    def parse_excel_file(self, file_path: str) -> List[Dict[str, Any]]:
        """Parse Excel file and extract post data"""
        posts = []
        
        try:
            df = pd.read_excel(file_path)
            
            for index, row in df.iterrows():
                try:
                    post_data = self._extract_post_data(row.to_dict(), index + 1)
                    if post_data:
                        posts.append(post_data)
                except Exception as e:
                    logger.warning(f"Error parsing row {index + 1}: {str(e)}")
                    continue
        
        except Exception as e:
            logger.error(f"Error reading Excel file: {str(e)}")
            raise
        
        return posts
    
    def _extract_post_data(self, row: Dict[str, Any], row_num: int) -> Optional[Dict[str, Any]]:
        """Extract and validate post data from a row"""
        # Flexible column mapping - handle various column names
        content_fields = ['content', 'text', 'post', 'caption', 'description']
        platform_fields = ['platforms', 'platform', 'targets', 'social_media']
        hashtag_fields = ['hashtags', 'tags', 'hash_tags']
        
        # Find content
        content = None
        for field in content_fields:
            for key in row.keys():
                if key.lower().strip() == field:
                    content = str(row[key]).strip()
                    break
            if content:
                break
        
        if not content or content.lower() in ['', 'nan', 'none']:
            return None
        
        # Find platforms
        platforms = []
        for field in platform_fields:
            for key in row.keys():
                if key.lower().strip() == field:
                    platform_str = str(row[key]).strip().lower()
                    if platform_str and platform_str not in ['nan', 'none']:
                        # Parse comma-separated platforms
                        platforms = [p.strip() for p in platform_str.split(',')]
                        # Standardize platform names
                        platforms = [self._standardize_platform_name(p) for p in platforms]
                        platforms = [p for p in platforms if p]  # Remove None values
                    break
            if platforms:
                break
        
        # Default to all platforms if none specified
        if not platforms:
            platforms = ['tiktok', 'instagram', 'youtube']
        
        # Find hashtags
        hashtags = []
        for field in hashtag_fields:
            for key in row.keys():
                if key.lower().strip() == field:
                    hashtag_str = str(row[key]).strip()
                    if hashtag_str and hashtag_str.lower() not in ['nan', 'none']:
                        # Parse hashtags
                        hashtags = self._parse_hashtags(hashtag_str)
                    break
            if hashtags:
                break
        
        return {
            'content': content,
            'platforms': platforms,
            'hashtags': hashtags,
            'row_number': row_num
        }
    
    def _standardize_platform_name(self, platform: str) -> Optional[str]:
        """Standardize platform names"""
        platform = platform.lower().strip()
        
        if platform in ['tiktok', 'tik tok', 'tt']:
            return 'tiktok'
        elif platform in ['instagram', 'insta', 'ig']:
            return 'instagram'
        elif platform in ['youtube', 'yt', 'you tube']:
            return 'youtube'
        
        return None
    
    def _parse_hashtags(self, hashtag_str: str) -> List[str]:
        """Parse hashtags from string"""
        hashtags = []
        
        # Split by common delimiters
        for delimiter in [',', ';', ' ', '\n']:
            if delimiter in hashtag_str:
                parts = hashtag_str.split(delimiter)
                break
        else:
            parts = [hashtag_str]
        
        for part in parts:
            tag = part.strip()
            if tag:
                # Add # if not present
                if not tag.startswith('#'):
                    tag = '#' + tag
                hashtags.append(tag)
        
        return hashtags
    
    def process_bulk_upload(self, user_id: int, file: FileStorage, 
                          schedule_type: str = 'daily', 
                          start_date: datetime = None,
                          target_platforms: List[str] = None) -> BulkUpload:
        """Process bulk upload and create scheduled posts"""
        
        # Save uploaded file temporarily
        upload_dir = 'uploads'
        os.makedirs(upload_dir, exist_ok=True)
        
        file_ext = os.path.splitext(file.filename)[1].lower()
        temp_filename = f"bulk_upload_{user_id}_{int(datetime.now().timestamp())}{file_ext}"
        temp_path = os.path.join(upload_dir, temp_filename)
        
        try:
            file.save(temp_path)
            
            # Parse file based on extension
            if file_ext == '.csv':
                posts_data = self.parse_csv_file(temp_path)
            else:
                posts_data = self.parse_excel_file(temp_path)
            
            if not posts_data:
                raise ValueError("No valid posts found in the uploaded file")
            
            # Create bulk upload record
            bulk_upload = BulkUpload(
                user_id=user_id,
                name=file.filename,
                total_posts=len(posts_data),
                status='processing',
                start_date=start_date or datetime.now(),
                schedule_type=schedule_type,
                target_platforms=target_platforms or ['tiktok', 'instagram', 'youtube']
            )
            db.session.add(bulk_upload)
            db.session.commit()
            
            # Create scheduled posts
            self._create_scheduled_posts(bulk_upload, posts_data, start_date)
            
            # Update bulk upload status
            bulk_upload.status = 'completed'
            bulk_upload.processed_posts = len(posts_data)
            db.session.commit()
            
            return bulk_upload
            
        except Exception as e:
            logger.error(f"Error processing bulk upload: {str(e)}")
            if 'bulk_upload' in locals():
                bulk_upload.status = 'failed'
                db.session.commit()
            raise
        
        finally:
            # Clean up temporary file
            if os.path.exists(temp_path):
                os.remove(temp_path)
    
    def _create_scheduled_posts(self, bulk_upload: BulkUpload, posts_data: List[Dict[str, Any]], 
                              start_date: datetime = None):
        """Create individual scheduled posts from bulk data"""
        
        start_date = start_date or datetime.now()
        user = User.query.get(bulk_upload.user_id)
        
        # Get user's posting preferences
        daily_times = user.daily_post_times or ['09:00', '18:00']
        
        current_date = start_date
        post_time_index = 0
        
        for i, post_data in enumerate(posts_data):
            # Calculate posting time
            if bulk_upload.schedule_type == 'daily':
                # Distribute posts across daily time slots
                time_str = daily_times[post_time_index % len(daily_times)]
                hour, minute = map(int, time_str.split(':'))
                
                scheduled_time = current_date.replace(hour=hour, minute=minute, second=0, microsecond=0)
                
                # Move to next time slot or next day
                post_time_index += 1
                if post_time_index % len(daily_times) == 0:
                    current_date += timedelta(days=1)
                    
            elif bulk_upload.schedule_type == 'immediate':
                # Schedule for immediate posting with small delays
                scheduled_time = start_date + timedelta(minutes=i * 2)
            
            else:  # custom scheduling
                # Use provided start_date for all posts (user can modify later)
                scheduled_time = start_date + timedelta(hours=i)
            
            # Determine platforms for this post
            platforms = post_data.get('platforms', bulk_upload.target_platforms)
            
            # Create post
            post = Post(
                user_id=bulk_upload.user_id,
                content=post_data['content'],
                scheduled_time=scheduled_time,
                target_platforms=platforms,
                hashtags=post_data.get('hashtags', []),
                bulk_upload_id=bulk_upload.id
            )
            
            db.session.add(post)
        
        db.session.commit()


class SchedulingService:
    """Background service for processing scheduled posts"""
    
    def __init__(self):
        self.running = False
        self.thread = None
    
    def start(self):
        """Start the scheduling service"""
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self._run_scheduler, daemon=True)
            self.thread.start()
            logger.info("Scheduling service started")
    
    def stop(self):
        """Stop the scheduling service"""
        self.running = False
        if self.thread:
            self.thread.join()
        logger.info("Scheduling service stopped")
    
    def _run_scheduler(self):
        """Main scheduler loop"""
        while self.running:
            try:
                with current_app.app_context():
                    self._process_due_posts()
                time.sleep(60)  # Check every minute
            except Exception as e:
                logger.error(f"Scheduler error: {str(e)}")
                time.sleep(60)
    
    def _process_due_posts(self):
        """Process posts that are due for posting"""
        # Find posts that are scheduled and due
        due_posts = Post.query.filter(
            Post.status == 'scheduled',
            Post.scheduled_time <= datetime.now()
        ).limit(10).all()  # Process 10 at a time to avoid overload
        
        for post in due_posts:
            try:
                self._process_single_post(post)
            except Exception as e:
                logger.error(f"Error processing post {post.id}: {str(e)}")
                post.status = 'failed'
                db.session.commit()
    
    def _process_single_post(self, post: Post):
        """Process a single post for publishing"""
        from social_media_integrations import social_media
        
        post.status = 'posting'
        db.session.commit()
        
        results = {}
        success_count = 0
        
        # Get user's connected accounts
        user_accounts = SocialAccount.query.filter_by(
            user_id=post.user_id,
            is_active=True
        ).all()
        
        account_map = {acc.platform: acc for acc in user_accounts}
        
        for platform in post.target_platforms:
            if platform not in account_map:
                results[platform] = {
                    'status': 'failed',
                    'error': f'No connected {platform} account'
                }
                continue
            
            account = account_map[platform]
            
            try:
                # Post to platform
                result = social_media.post_content(
                    platform=platform,
                    access_token=account.access_token,
                    content=post.content,
                    media_path=post.media_url
                )
                
                if result.get('success'):
                    results[platform] = {
                        'status': 'posted',
                        'platform_post_id': result.get('post_id'),
                        'share_url': result.get('share_url')
                    }
                    success_count += 1
                else:
                    results[platform] = {
                        'status': 'failed',
                        'error': result.get('error', 'Unknown error')
                    }
                    
            except Exception as e:
                results[platform] = {
                    'status': 'failed',
                    'error': str(e)
                }
        
        # Update post status
        post.posting_results = results
        
        if success_count > 0:
            post.status = 'posted' if success_count == len(post.target_platforms) else 'partial'
            post.posted_at = datetime.now()
        else:
            post.status = 'failed'
        
        db.session.commit()


# Global instances
bulk_processor = BulkUploadProcessor()
scheduler = SchedulingService()


def init_scheduler():
    """Initialize the scheduler (call this from your app startup)"""
    scheduler.start()


def cleanup_scheduler():
    """Cleanup scheduler (call this when shutting down)"""
    scheduler.stop()