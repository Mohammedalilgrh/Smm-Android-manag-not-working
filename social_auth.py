from flask import Blueprint, request, redirect, url_for, flash, session, jsonify, render_template
from flask_login import login_required, current_user
from models import SocialAccount
from app import db
from social_media_api import get_oauth_url, handle_oauth_callback, refresh_access_token
import logging
from datetime import datetime

social_bp = Blueprint('social', __name__)

@social_bp.route('/connect/<platform>')
@login_required
def connect_platform(platform):
    """Initiate OAuth connection to a social media platform"""
    if platform not in ['tiktok', 'instagram', 'youtube']:
        flash('Unsupported platform', 'danger')
        return redirect(url_for('social.manage_accounts'))
    
    try:
        # Check if already connected
        existing_account = SocialAccount.query.filter_by(
            user_id=current_user.id, 
            platform=platform, 
            is_active=True
        ).first()
        
        if existing_account:
            flash(f'You are already connected to {platform.title()}', 'info')
            return redirect(url_for('social.manage_accounts'))
        
        # Get OAuth URL
        oauth_url, state = get_oauth_url(platform)
        if not oauth_url:
            flash(f'Failed to connect to {platform.title()}. Please try again later.', 'danger')
            return redirect(url_for('social.manage_accounts'))
        
        # Store state in session for security
        session[f'{platform}_oauth_state'] = state
        
        return redirect(oauth_url)
    
    except Exception as e:
        logging.error(f"Error connecting to {platform}: {e}")
        flash(f'Failed to connect to {platform.title()}', 'danger')
        return redirect(url_for('social.manage_accounts'))

@social_bp.route('/callback/<platform>')
@login_required
def oauth_callback(platform):
    """Handle OAuth callback from social media platforms"""
    if platform not in ['tiktok', 'instagram', 'youtube']:
        flash('Invalid platform', 'danger')
        return redirect(url_for('social.manage_accounts'))
    
    try:
        # Verify state parameter
        state = request.args.get('state')
        expected_state = session.get(f'{platform}_oauth_state')
        
        if not state or state != expected_state:
            flash('Security check failed. Please try connecting again.', 'danger')
            return redirect(url_for('social.manage_accounts'))
        
        # Handle authorization code
        code = request.args.get('code')
        error = request.args.get('error')
        
        if error:
            flash(f'Authorization denied for {platform.title()}', 'warning')
            return redirect(url_for('social.manage_accounts'))
        
        if not code:
            flash('Authorization code not received', 'danger')
            return redirect(url_for('social.manage_accounts'))
        
        # Exchange code for access token
        token_data = handle_oauth_callback(platform, code)
        if not token_data:
            flash(f'Failed to get access token from {platform.title()}', 'danger')
            return redirect(url_for('social.manage_accounts'))
        
        # Check if this account is already connected to another user
        existing_account = SocialAccount.query.filter_by(
            platform=platform,
            platform_user_id=token_data['user_id']
        ).first()
        
        if existing_account and existing_account.user_id != current_user.id:
            flash(f'This {platform.title()} account is already connected to another user', 'danger')
            return redirect(url_for('social.manage_accounts'))
        
        # Create or update social account
        if existing_account:
            # Reactivate existing account
            existing_account.access_token = token_data['access_token']
            existing_account.refresh_token = token_data.get('refresh_token')
            existing_account.token_expires_at = token_data.get('expires_at')
            existing_account.is_active = True
            existing_account.last_used = datetime.utcnow()
            account = existing_account
        else:
            # Create new account
            account = SocialAccount(
                user_id=current_user.id,
                platform=platform,
                platform_user_id=token_data['user_id'],
                platform_username=token_data.get('username'),
                access_token=token_data['access_token'],
                refresh_token=token_data.get('refresh_token'),
                token_expires_at=token_data.get('expires_at')
            )
            db.session.add(account)
        
        db.session.commit()
        
        # Clean up session
        session.pop(f'{platform}_oauth_state', None)
        
        flash(f'Successfully connected to {platform.title()}!', 'success')
        return redirect(url_for('social.manage_accounts'))
    
    except Exception as e:
        logging.error(f"OAuth callback error for {platform}: {e}")
        flash(f'Failed to connect to {platform.title()}', 'danger')
        return redirect(url_for('social.manage_accounts'))

@social_bp.route('/disconnect/<platform>', methods=['POST'])
@login_required
def disconnect_platform(platform):
    """Disconnect from a social media platform"""
    try:
        account = SocialAccount.query.filter_by(
            user_id=current_user.id,
            platform=platform,
            is_active=True
        ).first()
        
        if not account:
            return jsonify({'error': 'Account not found'}), 404
        
        # Deactivate instead of deleting to preserve history
        account.is_active = False
        db.session.commit()
        
        flash(f'Disconnected from {platform.title()}', 'info')
        return jsonify({'success': True})
    
    except Exception as e:
        logging.error(f"Error disconnecting from {platform}: {e}")
        return jsonify({'error': 'Failed to disconnect'}), 500

@social_bp.route('/accounts')
@login_required
def manage_accounts():
    """Manage connected social media accounts"""
    platforms = ['tiktok', 'instagram', 'youtube']
    connected_accounts = {}
    
    for platform in platforms:
        account = SocialAccount.query.filter_by(
            user_id=current_user.id,
            platform=platform,
            is_active=True
        ).first()
        connected_accounts[platform] = account
    
    return render_template('accounts/manage.html', 
                         platforms=platforms, 
                         connected_accounts=connected_accounts)

@social_bp.route('/refresh-token/<platform>', methods=['POST'])
@login_required
def refresh_token(platform):
    """Refresh access token for a platform"""
    try:
        account = SocialAccount.query.filter_by(
            user_id=current_user.id,
            platform=platform,
            is_active=True
        ).first()
        
        if not account:
            return jsonify({'error': 'Account not found'}), 404
        
        # Refresh token
        new_token_data = refresh_access_token(platform, account.refresh_token)
        if new_token_data:
            account.access_token = new_token_data['access_token']
            if 'refresh_token' in new_token_data:
                account.refresh_token = new_token_data['refresh_token']
            account.token_expires_at = new_token_data.get('expires_at')
            account.last_used = datetime.utcnow()
            db.session.commit()
            
            return jsonify({'success': True, 'message': 'Token refreshed successfully'})
        else:
            return jsonify({'error': 'Failed to refresh token'}), 500
    
    except Exception as e:
        logging.error(f"Error refreshing token for {platform}: {e}")
        return jsonify({'error': 'Failed to refresh token'}), 500
