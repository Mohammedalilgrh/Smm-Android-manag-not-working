"""
Enhanced routes with real social media integration and bulk upload
"""

from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash, session
from flask_login import login_required, current_user
from datetime import datetime, timedelta
from typing import Dict, Any
import os
import logging
from werkzeug.utils import secure_filename
import json

from app import db
from models import User, Post, SocialAccount, BulkUpload
from social_media_integrations import social_media, SocialMediaError
from bulk_upload_service import bulk_processor

logger = logging.getLogger(__name__)

# Create blueprint
main_bp = Blueprint('main', __name__)
api_bp = Blueprint('api', __name__, url_prefix='/api')
auth_bp = Blueprint('social_auth', __name__, url_prefix='/auth')

# File upload configuration
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'csv', 'xlsx', 'xls', 'png', 'jpg', 'jpeg', 'gif', 'mp4', 'mov', 'avi'}
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@main_bp.route('/')
def index():
    """Landing page"""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    return render_template('index.html')

@main_bp.route('/dashboard')
@login_required
def dashboard():
    """Main dashboard"""
    return render_template('dashboard.html')

# API Routes for AJAX calls

@api_bp.route('/stats')
@login_required
def get_stats():
    """Get user statistics"""
    total_posts = Post.query.filter_by(user_id=current_user.id).count()
    scheduled_posts = Post.query.filter_by(user_id=current_user.id, status='scheduled').count()
    posted_posts = Post.query.filter_by(user_id=current_user.id, status='posted').count()
    connected_accounts = SocialAccount.query.filter_by(user_id=current_user.id, is_active=True).count()
    
    return jsonify({
        'total_posts': total_posts,
        'scheduled_posts': scheduled_posts,
        'posted_posts': posted_posts,
        'connected_accounts': connected_accounts
    })

@api_bp.route('/posts', methods=['GET'])
@login_required
def get_posts():
    """Get user's posts"""
    posts = Post.query.filter_by(user_id=current_user.id).order_by(Post.created_at.desc()).all()
    
    posts_data = []
    for post in posts:
        posts_data.append({
            'id': post.id,
            'content': post.content,
            'scheduled_time': post.scheduled_time.isoformat(),
            'status': post.status,
            'target_platforms': post.target_platforms or [],
            'posting_results': post.posting_results,
            'created_at': post.created_at.isoformat(),
            'hashtags': post.hashtags or [],
            'bulk_upload_id': post.bulk_upload_id
        })
    
    return jsonify(posts_data)

@api_bp.route('/posts', methods=['POST'])
@login_required
def create_post():
    """Create a new post"""
    try:
        data = request.get_json()
        
        content = data.get('content', '').strip()
        platforms = data.get('platforms', [])
        schedule_type = data.get('scheduleType', 'now')
        schedule_time = data.get('scheduleTime')
        
        if not content:
            return jsonify({'error': 'Content is required'}), 400
        
        if not platforms:
            return jsonify({'error': 'At least one platform must be selected'}), 400
        
        # Validate user has connected accounts for selected platforms
        user_accounts = SocialAccount.query.filter_by(
            user_id=current_user.id,
            is_active=True
        ).all()
        
        connected_platforms = {acc.platform for acc in user_accounts}
        missing_platforms = set(platforms) - connected_platforms
        
        if missing_platforms:
            return jsonify({
                'error': f'Please connect your {", ".join(missing_platforms)} account(s) first'
            }), 400
        
        # Set scheduled time
        if schedule_type == 'now':
            scheduled_time = datetime.now()
        else:
            try:
                scheduled_time = datetime.fromisoformat(schedule_time.replace('Z', '+00:00'))
            except ValueError:
                return jsonify({'error': 'Invalid schedule time format'}), 400
        
        # Create post
        post = Post(
            user_id=current_user.id,
            content=content,
            scheduled_time=scheduled_time,
            target_platforms=platforms,
            status='scheduled' if schedule_type == 'later' else 'scheduled'  # Will be processed immediately if 'now'
        )
        
        db.session.add(post)
        db.session.commit()
        
        return jsonify({
            'message': 'Post created successfully!',
            'post_id': post.id
        })
        
    except Exception as e:
        logger.error(f"Error creating post: {str(e)}")
        return jsonify({'error': 'Failed to create post'}), 500

@api_bp.route('/posts/<int:post_id>', methods=['DELETE'])
@login_required
def delete_post(post_id):
    """Delete a post"""
    post = Post.query.filter_by(id=post_id, user_id=current_user.id).first()
    
    if not post:
        return jsonify({'error': 'Post not found'}), 404
    
    db.session.delete(post)
    db.session.commit()
    
    return jsonify({'message': 'Post deleted successfully'})

@api_bp.route('/accounts', methods=['GET'])
@login_required
def get_accounts():
    """Get user's connected social media accounts"""
    accounts = SocialAccount.query.filter_by(user_id=current_user.id, is_active=True).all()
    
    accounts_data = []
    for account in accounts:
        accounts_data.append({
            'id': account.id,
            'platform': account.platform,
            'platform_username': account.platform_username,
            'connected_at': account.created_at.isoformat()
        })
    
    return jsonify(accounts_data)

@api_bp.route('/accounts', methods=['POST'])
@login_required
def connect_account():
    """Initiate account connection"""
    try:
        data = request.get_json()
        platform = data.get('platform')
        
        if platform not in ['tiktok', 'instagram', 'youtube']:
            return jsonify({'error': 'Invalid platform'}), 400
        
        # Store platform in session for callback
        session[f'{platform}_auth_user'] = current_user.id
        
        # Get authorization URL
        auth_url = social_media.get_authorization_url(platform, state=f'{platform}_{current_user.id}')
        
        return jsonify({
            'auth_url': auth_url,
            'message': f'Please complete {platform} authentication'
        })
        
    except Exception as e:
        logger.error(f"Error initiating {platform} connection: {str(e)}")
        return jsonify({'error': f'Failed to connect {platform}'}), 500

@api_bp.route('/accounts/<int:account_id>/disconnect', methods=['POST'])
@login_required
def disconnect_account(account_id):
    """Disconnect social media account"""
    account = SocialAccount.query.filter_by(
        id=account_id,
        user_id=current_user.id
    ).first()
    
    if not account:
        return jsonify({'error': 'Account not found'}), 404
    
    account.is_active = False
    db.session.commit()
    
    return jsonify({'message': f'{account.platform} account disconnected'})

# Bulk Upload Routes

@api_bp.route('/bulk-upload', methods=['POST'])
@login_required
def bulk_upload():
    """Handle bulk upload of posts"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file uploaded'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not bulk_processor.validate_file(file):
            return jsonify({'error': 'Invalid file format. Please upload CSV or Excel files.'}), 400
        
        # Get form data
        schedule_type = request.form.get('schedule_type', 'daily')
        start_date_str = request.form.get('start_date')
        platforms = request.form.getlist('platforms')
        
        if not platforms:
            platforms = ['tiktok', 'instagram', 'youtube']
        
        # Parse start date
        start_date = None
        if start_date_str:
            try:
                start_date = datetime.fromisoformat(start_date_str)
            except ValueError:
                start_date = datetime.now()
        else:
            start_date = datetime.now()
        
        # Process bulk upload
        bulk_upload_record = bulk_processor.process_bulk_upload(
            user_id=current_user.id,
            file=file,
            schedule_type=schedule_type,
            start_date=start_date,
            target_platforms=platforms
        )
        
        return jsonify({
            'message': f'Successfully uploaded {bulk_upload_record.total_posts} posts!',
            'bulk_upload_id': bulk_upload_record.id,
            'processed_posts': bulk_upload_record.processed_posts
        })
        
    except Exception as e:
        logger.error(f"Bulk upload error: {str(e)}")
        return jsonify({'error': f'Bulk upload failed: {str(e)}'}), 500

@api_bp.route('/bulk-uploads', methods=['GET'])
@login_required
def get_bulk_uploads():
    """Get user's bulk upload history"""
    uploads = BulkUpload.query.filter_by(user_id=current_user.id).order_by(BulkUpload.created_at.desc()).all()
    
    uploads_data = []
    for upload in uploads:
        uploads_data.append({
            'id': upload.id,
            'name': upload.name,
            'total_posts': upload.total_posts,
            'processed_posts': upload.processed_posts,
            'status': upload.status,
            'schedule_type': upload.schedule_type,
            'target_platforms': upload.target_platforms,
            'created_at': upload.created_at.isoformat()
        })
    
    return jsonify(uploads_data)

# Social Media OAuth Callbacks

@auth_bp.route('/tiktok/callback')
def tiktok_callback():
    """Handle TikTok OAuth callback"""
    return handle_oauth_callback('tiktok')

@auth_bp.route('/instagram/callback')
def instagram_callback():
    """Handle Instagram OAuth callback"""
    return handle_oauth_callback('instagram')

@auth_bp.route('/youtube/callback')
def youtube_callback():
    """Handle YouTube OAuth callback"""
    return handle_oauth_callback('youtube')

def handle_oauth_callback(platform: str):
    """Generic OAuth callback handler"""
    try:
        code = request.args.get('code')
        state = request.args.get('state')
        error = request.args.get('error')
        
        if error:
            flash(f'{platform} connection failed: {error}', 'error')
            return redirect(url_for('main.dashboard'))
        
        if not code:
            flash(f'{platform} connection failed: No authorization code received', 'error')
            return redirect(url_for('main.dashboard'))
        
        # Verify state and get user ID
        if not state or not state.startswith(f'{platform}_'):
            flash(f'{platform} connection failed: Invalid state', 'error')
            return redirect(url_for('main.dashboard'))
        
        user_id = int(state.split('_')[1])
        user = User.query.get(user_id)
        
        if not user:
            flash(f'{platform} connection failed: User not found', 'error')
            return redirect(url_for('main.dashboard'))
        
        # Exchange code for token
        token_data = social_media.exchange_code_for_token(platform, code)
        access_token = token_data.get('access_token')
        refresh_token = token_data.get('refresh_token')
        
        if not access_token:
            flash(f'{platform} connection failed: No access token received', 'error')
            return redirect(url_for('main.dashboard'))
        
        # Get user info from platform
        user_info = social_media.get_user_info(platform, access_token)
        
        # Save or update account
        existing_account = SocialAccount.query.filter_by(
            user_id=user_id,
            platform=platform
        ).first()
        
        if existing_account:
            # Update existing account
            existing_account.access_token = access_token
            existing_account.refresh_token = refresh_token
            existing_account.platform_username = extract_username(platform, user_info)
            existing_account.platform_user_id = extract_user_id(platform, user_info)
            existing_account.is_active = True
            existing_account.updated_at = datetime.now()
        else:
            # Create new account
            new_account = SocialAccount(
                user_id=user_id,
                platform=platform,
                access_token=access_token,
                refresh_token=refresh_token,
                platform_username=extract_username(platform, user_info),
                platform_user_id=extract_user_id(platform, user_info),
                is_active=True
            )
            db.session.add(new_account)
        
        db.session.commit()
        
        flash(f'{platform} account connected successfully!', 'success')
        return redirect(url_for('main.dashboard'))
        
    except Exception as e:
        logger.error(f"OAuth callback error for {platform}: {str(e)}")
        flash(f'{platform} connection failed: {str(e)}', 'error')
        return redirect(url_for('main.dashboard'))

def extract_username(platform: str, user_info: Dict) -> str:
    """Extract username from platform user info"""
    if platform == 'tiktok':
        return user_info.get('data', {}).get('display_name', '')
    elif platform == 'instagram':
        return user_info.get('username', '')
    elif platform == 'youtube':
        items = user_info.get('items', [])
        if items:
            return items[0].get('snippet', {}).get('title', '')
    return ''

def extract_user_id(platform: str, user_info: Dict) -> str:
    """Extract user ID from platform user info"""
    if platform == 'tiktok':
        return user_info.get('data', {}).get('open_id', '')
    elif platform == 'instagram':
        return user_info.get('id', '')
    elif platform == 'youtube':
        items = user_info.get('items', [])
        if items:
            return items[0].get('id', '')
    return ''

# Media Upload Route
@api_bp.route('/upload-media', methods=['POST'])
@login_required
def upload_media():
    """Handle media file uploads"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file uploaded'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({'error': 'Invalid file type'}), 400
        
        # Save file
        filename = secure_filename(file.filename)
        timestamp = int(datetime.now().timestamp())
        filename = f"{current_user.id}_{timestamp}_{filename}"
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        
        file.save(file_path)
        
        # Return file URL
        file_url = f"/uploads/{filename}"
        
        return jsonify({
            'file_url': file_url,
            'filename': filename
        })
        
    except Exception as e:
        logger.error(f"Media upload error: {str(e)}")
        return jsonify({'error': 'File upload failed'}), 500

# Auto-scheduling configuration
@api_bp.route('/auto-schedule', methods=['GET'])
@login_required
def get_auto_schedule_config():
    """Get user's auto-scheduling configuration"""
    return jsonify({
        'auto_schedule_enabled': current_user.auto_schedule_enabled,
        'daily_post_times': current_user.daily_post_times or ['09:00', '18:00'],
        'timezone': current_user.timezone or 'UTC'
    })

@api_bp.route('/auto-schedule', methods=['POST'])
@login_required
def update_auto_schedule_config():
    """Update user's auto-scheduling configuration"""
    try:
        data = request.get_json()
        
        current_user.auto_schedule_enabled = data.get('auto_schedule_enabled', False)
        current_user.daily_post_times = data.get('daily_post_times', ['09:00', '18:00'])
        current_user.timezone = data.get('timezone', 'UTC')
        
        db.session.commit()
        
        return jsonify({'message': 'Auto-schedule settings updated successfully'})
        
    except Exception as e:
        logger.error(f"Auto-schedule config update error: {str(e)}")
        return jsonify({'error': 'Failed to update settings'}), 500