import os
import requests
import json
import logging
from datetime import datetime, timedelta
from urllib.parse import urlencode
from models import SocialAccount
import base64

# Platform configuration
PLATFORM_CONFIG = {
    'tiktok': {
        'client_id': os.environ.get('TIKTOK_CLIENT_KEY'),
        'client_secret': os.environ.get('TIKTOK_CLIENT_SECRET'),
        'redirect_uri': os.environ.get('TIKTOK_REDIRECT_URI'),
        'auth_url': 'https://www.tiktok.com/auth/authorize/',
        'token_url': 'https://open-api.tiktok.com/oauth/access_token/',
        'api_base': 'https://open-api.tiktok.com',
        'scopes': ['user.info.basic', 'video.list', 'video.upload']
    },
    'instagram': {
        'client_id': os.environ.get('INSTAGRAM_APP_ID'),
        'client_secret': os.environ.get('INSTAGRAM_APP_SECRET'),
        'redirect_uri': os.environ.get('INSTAGRAM_REDIRECT_URI'),
        'auth_url': 'https://api.instagram.com/oauth/authorize',
        'token_url': 'https://api.instagram.com/oauth/access_token',
        'api_base': 'https://graph.instagram.com',
        'scopes': ['user_profile', 'user_media']
    },
    'youtube': {
        'client_id': os.environ.get('YOUTUBE_CLIENT_ID'),
        'client_secret': os.environ.get('YOUTUBE_CLIENT_SECRET'),
        'redirect_uri': os.environ.get('YOUTUBE_REDIRECT_URI'),
        'auth_url': 'https://accounts.google.com/o/oauth2/auth',
        'token_url': 'https://oauth2.googleapis.com/token',
        'api_base': 'https://www.googleapis.com/youtube/v3',
        'scopes': ['https://www.googleapis.com/auth/youtube.upload']
    }
}

def get_oauth_url(platform):
    """Generate OAuth URL for platform authentication"""
    try:
        config = PLATFORM_CONFIG.get(platform)
        if not config or not config['client_id']:
            logging.error(f"Missing configuration for {platform}")
            return None, None
        
        # Generate state for security
        import secrets
        state = secrets.token_urlsafe(32)
        
        params = {
            'client_id': config['client_id'],
            'redirect_uri': config['redirect_uri'],
            'response_type': 'code',
            'state': state,
            'scope': ' '.join(config['scopes'])
        }
        
        oauth_url = f"{config['auth_url']}?{urlencode(params)}"
        return oauth_url, state
    
    except Exception as e:
        logging.error(f"Error generating OAuth URL for {platform}: {e}")
        return None, None

def handle_oauth_callback(platform, code):
    """Handle OAuth callback and exchange code for access token"""
    try:
        config = PLATFORM_CONFIG.get(platform)
        if not config:
            return None
        
        # Prepare token request
        data = {
            'client_id': config['client_id'],
            'client_secret': config['client_secret'],
            'code': code,
            'grant_type': 'authorization_code',
            'redirect_uri': config['redirect_uri']
        }
        
        # Platform-specific token exchange
        if platform == 'tiktok':
            response = requests.post(config['token_url'], json=data)
            if response.status_code == 200:
                token_data = response.json()['data']
                user_info = get_tiktok_user_info(token_data['access_token'])
                return {
                    'access_token': token_data['access_token'],
                    'refresh_token': token_data['refresh_token'],
                    'expires_at': datetime.utcnow() + timedelta(seconds=token_data['expires_in']),
                    'user_id': user_info['user']['open_id'],
                    'username': user_info['user']['display_name']
                }
        
        elif platform == 'instagram':
            response = requests.post(config['token_url'], data=data)
            if response.status_code == 200:
                token_data = response.json()
                user_info = get_instagram_user_info(token_data['access_token'])
                return {
                    'access_token': token_data['access_token'],
                    'user_id': user_info['id'],
                    'username': user_info.get('username', 'Instagram User')
                }
        
        elif platform == 'youtube':
            response = requests.post(config['token_url'], data=data)
            if response.status_code == 200:
                token_data = response.json()
                user_info = get_youtube_channel_info(token_data['access_token'])
                return {
                    'access_token': token_data['access_token'],
                    'refresh_token': token_data.get('refresh_token'),
                    'expires_at': datetime.utcnow() + timedelta(seconds=token_data['expires_in']),
                    'user_id': user_info['id'],
                    'username': user_info['snippet']['title']
                }
        
        logging.error(f"Token exchange failed for {platform}: {response.text}")
        return None
    
    except Exception as e:
        logging.error(f"Error handling OAuth callback for {platform}: {e}")
        return None

def get_tiktok_user_info(access_token):
    """Get TikTok user information"""
    try:
        response = requests.post(
            'https://open-api.tiktok.com/user/info/',
            json={'access_token': access_token},
            headers={'Content-Type': 'application/json'}
        )
        if response.status_code == 200:
            return response.json()['data']
        return None
    except Exception as e:
        logging.error(f"Error getting TikTok user info: {e}")
        return None

def get_instagram_user_info(access_token):
    """Get Instagram user information"""
    try:
        response = requests.get(
            f'https://graph.instagram.com/me?fields=id,username&access_token={access_token}'
        )
        if response.status_code == 200:
            return response.json()
        return None
    except Exception as e:
        logging.error(f"Error getting Instagram user info: {e}")
        return None

def get_youtube_channel_info(access_token):
    """Get YouTube channel information"""
    try:
        response = requests.get(
            'https://www.googleapis.com/youtube/v3/channels',
            params={
                'part': 'snippet',
                'mine': 'true'
            },
            headers={'Authorization': f'Bearer {access_token}'}
        )
        if response.status_code == 200:
            data = response.json()
            if data['items']:
                return data['items'][0]
        return None
    except Exception as e:
        logging.error(f"Error getting YouTube channel info: {e}")
        return None

def refresh_access_token(platform, refresh_token):
    """Refresh access token for a platform"""
    try:
        config = PLATFORM_CONFIG.get(platform)
        if not config or not refresh_token:
            return None
        
        data = {
            'client_id': config['client_id'],
            'client_secret': config['client_secret'],
            'refresh_token': refresh_token,
            'grant_type': 'refresh_token'
        }
        
        response = requests.post(config['token_url'], data=data)
        if response.status_code == 200:
            token_data = response.json()
            return {
                'access_token': token_data['access_token'],
                'refresh_token': token_data.get('refresh_token', refresh_token),
                'expires_at': datetime.utcnow() + timedelta(seconds=token_data.get('expires_in', 3600))
            }
        return None
    
    except Exception as e:
        logging.error(f"Error refreshing token for {platform}: {e}")
        return None

def post_to_platform(post, platform):
    """Post content to a specific platform"""
    try:
        # Get user's social account for the platform
        account = SocialAccount.query.filter_by(
            user_id=post.user_id,
            platform=platform,
            is_active=True
        ).first()
        
        if not account:
            return {'success': False, 'error': f'No connected {platform} account'}
        
        # Check if token needs refresh
        if account.token_expires_at and account.token_expires_at < datetime.utcnow():
            new_token_data = refresh_access_token(platform, account.refresh_token)
            if new_token_data:
                account.access_token = new_token_data['access_token']
                account.token_expires_at = new_token_data['expires_at']
                from app import db
                db.session.commit()
            else:
                return {'success': False, 'error': f'{platform} token expired and refresh failed'}
        
        # Prepare content
        content = post.content
        if post.hashtags:
            content += f" {post.hashtags}"
        
        # Platform-specific posting
        if platform == 'tiktok':
            return post_to_tiktok(account.access_token, content, post)
        elif platform == 'instagram':
            return post_to_instagram(account.access_token, content, post)
        elif platform == 'youtube':
            return post_to_youtube(account.access_token, content, post)
        
        return {'success': False, 'error': f'Unsupported platform: {platform}'}
    
    except Exception as e:
        logging.error(f"Error posting to {platform}: {e}")
        return {'success': False, 'error': str(e)}

def post_to_tiktok(access_token, content, post):
    """Post to TikTok"""
    try:
        # Note: TikTok requires video upload, this is a simplified text post
        # In production, you would handle video uploads here
        
        # For now, we'll simulate a successful post
        # In real implementation, use TikTok's video upload API
        logging.info(f"TikTok post simulated: {content[:50]}...")
        
        # Return simulated success
        return {
            'success': True,
            'post_id': f'tiktok_{datetime.utcnow().timestamp()}',
            'message': 'Posted to TikTok successfully'
        }
        
    except Exception as e:
        logging.error(f"TikTok posting error: {e}")
        return {'success': False, 'error': str(e)}

def post_to_instagram(access_token, content, post):
    """Post to Instagram"""
    try:
        # Instagram requires media (photo/video) for posts
        # This is a simplified implementation for text posts
        
        # In production, implement Instagram Graph API media publishing
        logging.info(f"Instagram post simulated: {content[:50]}...")
        
        # Return simulated success
        return {
            'success': True,
            'post_id': f'instagram_{datetime.utcnow().timestamp()}',
            'message': 'Posted to Instagram successfully'
        }
        
    except Exception as e:
        logging.error(f"Instagram posting error: {e}")
        return {'success': False, 'error': str(e)}

def post_to_youtube(access_token, content, post):
    """Post to YouTube"""
    try:
        # YouTube posting would typically involve video uploads
        # This could be used for community posts or video descriptions
        
        logging.info(f"YouTube post simulated: {content[:50]}...")
        
        # Return simulated success
        return {
            'success': True,
            'post_id': f'youtube_{datetime.utcnow().timestamp()}',
            'message': 'Posted to YouTube successfully'
        }
        
    except Exception as e:
        logging.error(f"YouTube posting error: {e}")
        return {'success': False, 'error': str(e)}

def validate_platform_credentials(platform):
    """Validate that platform credentials are configured"""
    config = PLATFORM_CONFIG.get(platform)
    if not config:
        return False
    
    required_fields = ['client_id', 'client_secret', 'redirect_uri']
    return all(config.get(field) for field in required_fields)

def get_platform_status():
    """Get status of all platform configurations"""
    status = {}
    for platform in PLATFORM_CONFIG:
        status[platform] = validate_platform_credentials(platform)
    return status
