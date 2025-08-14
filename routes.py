from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, send_file
from flask_login import login_required, current_user
from models import Post, BulkUpload, SocialAccount, PostQueue
from app import db, scheduler
from datetime import datetime, timedelta
import csv
import io
import json
from scheduler import schedule_post, process_bulk_upload
import logging

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    return render_template('index.html')

@main_bp.route('/dashboard')
@login_required
def dashboard():
    # Get user statistics
    total_posts = current_user.posts.count()
    scheduled_posts = current_user.posts.filter_by(status='scheduled').count()
    posted_count = current_user.posts.filter_by(status='posted').count()
    failed_count = current_user.posts.filter_by(status='failed').count()
    
    # Get connected platforms
    connected_platforms = current_user.get_connected_platforms()
    
    # Get recent posts
    recent_posts = current_user.posts.order_by(Post.created_at.desc()).limit(5).all()
    
    # Get upcoming posts
    upcoming_posts = current_user.posts.filter(
        Post.status == 'scheduled',
        Post.scheduled_for > datetime.utcnow()
    ).order_by(Post.scheduled_for).limit(5).all()
    
    stats = {
        'total_posts': total_posts,
        'scheduled_posts': scheduled_posts,
        'posted_count': posted_count,
        'failed_count': failed_count,
        'connected_platforms': len(connected_platforms),
        'platforms': connected_platforms
    }
    
    return render_template('dashboard.html', 
                         stats=stats, 
                         recent_posts=recent_posts,
                         upcoming_posts=upcoming_posts)

@main_bp.route('/schedule-post', methods=['GET', 'POST'])
@login_required
def schedule_post_route():
    if request.method == 'POST':
        content = request.form.get('content', '').strip()
        platforms = request.form.getlist('platforms')
        hashtags = request.form.get('hashtags', '').strip()
        schedule_type = request.form.get('schedule_type', 'now')
        
        if not content:
            flash('Content is required', 'danger')
            return redirect(url_for('main.schedule_post_route'))
        
        if not platforms:
            flash('Please select at least one platform', 'danger')
            return redirect(url_for('main.schedule_post_route'))
        
        # Validate platforms
        connected_platforms = current_user.get_connected_platforms()
        invalid_platforms = [p for p in platforms if p not in connected_platforms]
        if invalid_platforms:
            flash(f'Please connect to these platforms first: {", ".join(invalid_platforms)}', 'warning')
            return redirect(url_for('social.manage_accounts'))
        
        # Determine scheduled time
        if schedule_type == 'now':
            scheduled_for = datetime.utcnow() + timedelta(minutes=1)
        elif schedule_type == 'custom':
            date_str = request.form.get('schedule_date')
            time_str = request.form.get('schedule_time')
            try:
                scheduled_for = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
                if scheduled_for <= datetime.utcnow():
                    flash('Scheduled time must be in the future', 'danger')
                    return redirect(url_for('main.schedule_post_route'))
            except ValueError:
                flash('Invalid date or time format', 'danger')
                return redirect(url_for('main.schedule_post_route'))
        else:
            flash('Invalid schedule type', 'danger')
            return redirect(url_for('main.schedule_post_route'))
        
        # Create post
        try:
            post = Post(
                user_id=current_user.id,
                content=content,
                hashtags=hashtags,
                scheduled_for=scheduled_for
            )
            post.set_platforms(platforms)
            
            db.session.add(post)
            db.session.commit()
            
            # Schedule the post
            schedule_post(post.id)
            
            flash(f'Post scheduled successfully for {scheduled_for.strftime("%Y-%m-%d %H:%M")}', 'success')
            return redirect(url_for('main.posts'))
        
        except Exception as e:
            db.session.rollback()
            logging.error(f"Error scheduling post: {e}")
            flash('Failed to schedule post. Please try again.', 'danger')
    
    connected_platforms = current_user.get_connected_platforms()
    return render_template('posts/schedule.html', connected_platforms=connected_platforms)

@main_bp.route('/bulk-upload', methods=['GET', 'POST'])
@login_required
def bulk_upload():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file selected', 'danger')
            return redirect(url_for('main.bulk_upload'))
        
        file = request.files['file']
        if file.filename == '':
            flash('No file selected', 'danger')
            return redirect(url_for('main.bulk_upload'))
        
        if not file.filename.lower().endswith('.csv'):
            flash('Please upload a CSV file', 'danger')
            return redirect(url_for('main.bulk_upload'))
        
        upload_type = request.form.get('upload_type', 'daily')
        start_date = request.form.get('start_date')
        
        try:
            # Read and validate CSV
            stream = io.StringIO(file.stream.read().decode("UTF8"), newline=None)
            csv_input = csv.DictReader(stream)
            
            posts_data = []
            required_fields = ['content']
            
            for row_num, row in enumerate(csv_input, 1):
                if not any(row.values()):  # Skip empty rows
                    continue
                
                # Validate required fields
                missing_fields = [field for field in required_fields if not row.get(field, '').strip()]
                if missing_fields:
                    flash(f'Row {row_num}: Missing required fields: {", ".join(missing_fields)}', 'danger')
                    return redirect(url_for('main.bulk_upload'))
                
                posts_data.append({
                    'content': row.get('content', '').strip(),
                    'platforms': [p.strip() for p in row.get('platforms', '').split(',') if p.strip()],
                    'hashtags': row.get('hashtags', '').strip()
                })
            
            if not posts_data:
                flash('No valid posts found in the CSV file', 'danger')
                return redirect(url_for('main.bulk_upload'))
            
            # Create bulk upload record
            bulk_upload_record = BulkUpload(
                user_id=current_user.id,
                filename=file.filename,
                total_posts=len(posts_data),
                upload_type=upload_type,
                start_date=datetime.strptime(start_date, '%Y-%m-%d') if start_date else datetime.utcnow()
            )
            
            db.session.add(bulk_upload_record)
            db.session.commit()
            
            # Process bulk upload in background
            process_bulk_upload(bulk_upload_record.id, posts_data)
            
            flash(f'Bulk upload started! Processing {len(posts_data)} posts.', 'success')
            return redirect(url_for('main.bulk_uploads'))
        
        except Exception as e:
            logging.error(f"Bulk upload error: {e}")
            flash('Failed to process bulk upload. Please check your CSV format.', 'danger')
    
    return render_template('posts/bulk_upload.html')

@main_bp.route('/posts')
@login_required
def posts():
    page = request.args.get('page', 1, type=int)
    status_filter = request.args.get('status', 'all')
    
    query = current_user.posts
    
    if status_filter != 'all':
        query = query.filter_by(status=status_filter)
    
    posts = query.order_by(Post.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    
    return render_template('posts/list.html', posts=posts, status_filter=status_filter)

@main_bp.route('/bulk-uploads')
@login_required
def bulk_uploads():
    uploads = current_user.bulk_uploads.order_by(BulkUpload.created_at.desc()).all()
    return render_template('posts/bulk_uploads.html', uploads=uploads)

@main_bp.route('/download-template')
def download_template():
    return send_file('static/bulk_template.csv', as_attachment=True)

@main_bp.route('/api/post/<int:post_id>/delete', methods=['POST'])
@login_required
def delete_post(post_id):
    post = Post.query.filter_by(id=post_id, user_id=current_user.id).first()
    if not post:
        return jsonify({'error': 'Post not found'}), 404
    
    # Cancel scheduled job if exists
    if post.job_id and post.status == 'scheduled':
        try:
            scheduler.remove_job(post.job_id)
        except:
            pass
    
    db.session.delete(post)
    db.session.commit()
    
    return jsonify({'success': True})

@main_bp.route('/api/stats')
@login_required
def api_stats():
    stats = {
        'total_posts': current_user.posts.count(),
        'scheduled_posts': current_user.posts.filter_by(status='scheduled').count(),
        'posted_count': current_user.posts.filter_by(status='posted').count(),
        'failed_count': current_user.posts.filter_by(status='failed').count(),
        'connected_platforms': len(current_user.get_connected_platforms())
    }
    return jsonify(stats)
