"""
Real Social Media API Integrations
This module handles actual posting to TikTok, Instagram, and YouTube
"""

import os
import requests
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
import json
import base64
from urllib.parse import urlencode

logger = logging.getLogger(__name__)

class SocialMediaError(Exception):
    """Custom exception for social media API errors"""
    pass

class TikTokAPI:
    """TikTok for Developers API integration"""
    
    def __init__(self):
        self.client_key = os.environ.get('TIKTOK_CLIENT_KEY')
        self.client_secret = os.environ.get('TIKTOK_CLIENT_SECRET')
        self.redirect_uri = os.environ.get('TIKTOK_REDIRECT_URI', 'https://your-app.replit.app/auth/tiktok/callback')
        self.base_url = 'https://open-api.tiktok.com'
    
    def get_authorization_url(self, state: str = None) -> str:
        """Generate TikTok OAuth authorization URL"""
        params = {
            'client_key': self.client_key,
            'scope': 'user.info.basic,video.list,video.upload',
            'response_type': 'code',
            'redirect_uri': self.redirect_uri,
            'state': state or 'tiktok_auth'
        }
        return f"{self.base_url}/platform/oauth/authorize/?{urlencode(params)}"
    
    def exchange_code_for_token(self, code: str) -> Dict[str, Any]:
        """Exchange authorization code for access token"""
        url = f"{self.base_url}/v2/oauth/token/"
        data = {
            'client_key': self.client_key,
            'client_secret': self.client_secret,
            'code': code,
            'grant_type': 'authorization_code',
            'redirect_uri': self.redirect_uri
        }
        
        response = requests.post(url, data=data)
        if response.status_code == 200:
            return response.json()
        else:
            raise SocialMediaError(f"TikTok token exchange failed: {response.text}")
    
    def refresh_access_token(self, refresh_token: str) -> Dict[str, Any]:
        """Refresh access token using refresh token"""
        url = f"{self.base_url}/v2/oauth/token/"
        data = {
            'client_key': self.client_key,
            'client_secret': self.client_secret,
            'grant_type': 'refresh_token',
            'refresh_token': refresh_token
        }
        
        response = requests.post(url, data=data)
        if response.status_code == 200:
            return response.json()
        else:
            raise SocialMediaError(f"TikTok token refresh failed: {response.text}")
    
    def get_user_info(self, access_token: str) -> Dict[str, Any]:
        """Get user profile information"""
        url = f"{self.base_url}/v2/user/info/"
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        response = requests.post(url, headers=headers, json={'fields': ['open_id', 'union_id', 'avatar_url', 'display_name']})
        if response.status_code == 200:
            return response.json()
        else:
            raise SocialMediaError(f"TikTok user info failed: {response.text}")
    
    def upload_video(self, access_token: str, video_path: str, title: str, description: str = "") -> Dict[str, Any]:
        """Upload video to TikTok"""
        # Step 1: Initialize upload
        init_url = f"{self.base_url}/v2/post/publish/video/init/"
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        init_data = {
            'post_info': {
                'title': title,
                'description': description,
                'privacy_level': 'SELF_ONLY',  # Change to PUBLIC_TO_EVERYONE for public posts
                'disable_duet': False,
                'disable_comment': False,
                'disable_stitch': False,
                'video_cover_timestamp_ms': 1000
            },
            'source_info': {
                'source': 'FILE_UPLOAD',
                'video_size': os.path.getsize(video_path)
            }
        }
        
        response = requests.post(init_url, headers=headers, json=init_data)
        if response.status_code != 200:
            raise SocialMediaError(f"TikTok upload init failed: {response.text}")
        
        result = response.json()
        upload_url = result['data']['upload_url']
        publish_id = result['data']['publish_id']
        
        # Step 2: Upload video file
        with open(video_path, 'rb') as video_file:
            upload_response = requests.put(upload_url, data=video_file)
            if upload_response.status_code != 200:
                raise SocialMediaError(f"TikTok video upload failed: {upload_response.text}")
        
        # Step 3: Publish video
        publish_url = f"{self.base_url}/v2/post/publish/status/fetch/"
        publish_data = {'publish_id': publish_id}
        
        # Poll for completion
        for _ in range(30):  # Poll for up to 5 minutes
            response = requests.post(publish_url, headers=headers, json=publish_data)
            if response.status_code == 200:
                status = response.json()
                if status['data']['status'] == 'PROCESSING_DOWNLOAD':
                    time.sleep(10)
                    continue
                elif status['data']['status'] == 'PUBLISH_COMPLETE':
                    return {
                        'success': True,
                        'post_id': status['data']['publicaly_available_post_id'][0],
                        'share_url': status['data']['share_url']
                    }
                else:
                    break
        
        raise SocialMediaError("TikTok video publishing timed out or failed")


class InstagramAPI:
    """Instagram Basic Display and Graph API integration"""
    
    def __init__(self):
        self.app_id = os.environ.get('INSTAGRAM_APP_ID')
        self.app_secret = os.environ.get('INSTAGRAM_APP_SECRET')
        self.redirect_uri = os.environ.get('INSTAGRAM_REDIRECT_URI', 'https://your-app.replit.app/auth/instagram/callback')
        self.base_url = 'https://graph.instagram.com'
        self.auth_url = 'https://api.instagram.com/oauth'
    
    def get_authorization_url(self, state: str = None) -> str:
        """Generate Instagram OAuth authorization URL"""
        params = {
            'client_id': self.app_id,
            'redirect_uri': self.redirect_uri,
            'scope': 'user_profile,user_media',
            'response_type': 'code',
            'state': state or 'instagram_auth'
        }
        return f"{self.auth_url}/authorize?{urlencode(params)}"
    
    def exchange_code_for_token(self, code: str) -> Dict[str, Any]:
        """Exchange authorization code for access token"""
        url = f"{self.auth_url}/access_token"
        data = {
            'client_id': self.app_id,
            'client_secret': self.app_secret,
            'grant_type': 'authorization_code',
            'redirect_uri': self.redirect_uri,
            'code': code
        }
        
        response = requests.post(url, data=data)
        if response.status_code == 200:
            return response.json()
        else:
            raise SocialMediaError(f"Instagram token exchange failed: {response.text}")
    
    def get_long_lived_token(self, access_token: str) -> Dict[str, Any]:
        """Exchange short-lived token for long-lived token"""
        url = f"{self.base_url}/access_token"
        params = {
            'grant_type': 'ig_exchange_token',
            'client_secret': self.app_secret,
            'access_token': access_token
        }
        
        response = requests.get(url, params=params)
        if response.status_code == 200:
            return response.json()
        else:
            raise SocialMediaError(f"Instagram long-lived token failed: {response.text}")
    
    def get_user_info(self, access_token: str) -> Dict[str, Any]:
        """Get user profile information"""
        url = f"{self.base_url}/me"
        params = {
            'fields': 'id,username,account_type,media_count',
            'access_token': access_token
        }
        
        response = requests.get(url, params=params)
        if response.status_code == 200:
            return response.json()
        else:
            raise SocialMediaError(f"Instagram user info failed: {response.text}")
    
    def create_media_container(self, access_token: str, image_url: str, caption: str) -> str:
        """Create media container for posting"""
        url = f"{self.base_url}/me/media"
        data = {
            'image_url': image_url,
            'caption': caption,
            'access_token': access_token
        }
        
        response = requests.post(url, data=data)
        if response.status_code == 200:
            return response.json()['id']
        else:
            raise SocialMediaError(f"Instagram media container creation failed: {response.text}")
    
    def publish_media(self, access_token: str, creation_id: str) -> Dict[str, Any]:
        """Publish the media container"""
        url = f"{self.base_url}/me/media_publish"
        data = {
            'creation_id': creation_id,
            'access_token': access_token
        }
        
        response = requests.post(url, data=data)
        if response.status_code == 200:
            return response.json()
        else:
            raise SocialMediaError(f"Instagram media publish failed: {response.text}")


class YouTubeAPI:
    """YouTube Data API v3 integration"""
    
    def __init__(self):
        self.client_id = os.environ.get('YOUTUBE_CLIENT_ID')
        self.client_secret = os.environ.get('YOUTUBE_CLIENT_SECRET')
        self.redirect_uri = os.environ.get('YOUTUBE_REDIRECT_URI', 'https://your-app.replit.app/auth/youtube/callback')
        self.api_key = os.environ.get('YOUTUBE_API_KEY')
        self.base_url = 'https://www.googleapis.com/youtube/v3'
        self.upload_url = 'https://www.googleapis.com/upload/youtube/v3/videos'
    
    def get_authorization_url(self, state: str = None) -> str:
        """Generate YouTube OAuth authorization URL"""
        params = {
            'client_id': self.client_id,
            'redirect_uri': self.redirect_uri,
            'scope': 'https://www.googleapis.com/auth/youtube.upload https://www.googleapis.com/auth/youtube',
            'response_type': 'code',
            'access_type': 'offline',
            'state': state or 'youtube_auth'
        }
        return f"https://accounts.google.com/o/oauth2/auth?{urlencode(params)}"
    
    def exchange_code_for_token(self, code: str) -> Dict[str, Any]:
        """Exchange authorization code for access token"""
        url = "https://oauth2.googleapis.com/token"
        data = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'code': code,
            'grant_type': 'authorization_code',
            'redirect_uri': self.redirect_uri
        }
        
        response = requests.post(url, data=data)
        if response.status_code == 200:
            return response.json()
        else:
            raise SocialMediaError(f"YouTube token exchange failed: {response.text}")
    
    def refresh_access_token(self, refresh_token: str) -> Dict[str, Any]:
        """Refresh access token using refresh token"""
        url = "https://oauth2.googleapis.com/token"
        data = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'refresh_token': refresh_token,
            'grant_type': 'refresh_token'
        }
        
        response = requests.post(url, data=data)
        if response.status_code == 200:
            return response.json()
        else:
            raise SocialMediaError(f"YouTube token refresh failed: {response.text}")
    
    def get_channel_info(self, access_token: str) -> Dict[str, Any]:
        """Get user's channel information"""
        url = f"{self.base_url}/channels"
        headers = {'Authorization': f'Bearer {access_token}'}
        params = {
            'part': 'snippet,statistics',
            'mine': 'true'
        }
        
        response = requests.get(url, headers=headers, params=params)
        if response.status_code == 200:
            return response.json()
        else:
            raise SocialMediaError(f"YouTube channel info failed: {response.text}")
    
    def upload_video(self, access_token: str, video_path: str, title: str, description: str, tags: List[str] = None) -> Dict[str, Any]:
        """Upload video to YouTube"""
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        # Video metadata
        metadata = {
            'snippet': {
                'title': title,
                'description': description,
                'tags': tags or [],
                'categoryId': '22'  # People & Blogs
            },
            'status': {
                'privacyStatus': 'private'  # Change to 'public' for public videos
            }
        }
        
        # Upload video
        params = {
            'part': 'snippet,status',
            'uploadType': 'multipart'
        }
        
        files = {
            'metadata': (None, json.dumps(metadata), 'application/json'),
            'media': (os.path.basename(video_path), open(video_path, 'rb'), 'video/*')
        }
        
        response = requests.post(self.upload_url, headers={'Authorization': f'Bearer {access_token}'}, 
                               params=params, files=files)
        
        if response.status_code == 200:
            return response.json()
        else:
            raise SocialMediaError(f"YouTube video upload failed: {response.text}")


class SocialMediaManager:
    """Main class to manage all social media integrations"""
    
    def __init__(self):
        self.tiktok = TikTokAPI()
        self.instagram = InstagramAPI()
        self.youtube = YouTubeAPI()
    
    def get_authorization_url(self, platform: str, state: str = None) -> str:
        """Get OAuth authorization URL for specified platform"""
        if platform == 'tiktok':
            return self.tiktok.get_authorization_url(state)
        elif platform == 'instagram':
            return self.instagram.get_authorization_url(state)
        elif platform == 'youtube':
            return self.youtube.get_authorization_url(state)
        else:
            raise ValueError(f"Unsupported platform: {platform}")
    
    def exchange_code_for_token(self, platform: str, code: str) -> Dict[str, Any]:
        """Exchange authorization code for access token"""
        if platform == 'tiktok':
            return self.tiktok.exchange_code_for_token(code)
        elif platform == 'instagram':
            return self.instagram.exchange_code_for_token(code)
        elif platform == 'youtube':
            return self.youtube.exchange_code_for_token(code)
        else:
            raise ValueError(f"Unsupported platform: {platform}")
    
    def get_user_info(self, platform: str, access_token: str) -> Dict[str, Any]:
        """Get user information for specified platform"""
        if platform == 'tiktok':
            return self.tiktok.get_user_info(access_token)
        elif platform == 'instagram':
            return self.instagram.get_user_info(access_token)
        elif platform == 'youtube':
            return self.youtube.get_channel_info(access_token)
        else:
            raise ValueError(f"Unsupported platform: {platform}")
    
    def post_content(self, platform: str, access_token: str, content: str, media_path: str = None, **kwargs) -> Dict[str, Any]:
        """Post content to specified platform"""
        try:
            if platform == 'tiktok' and media_path:
                return self.tiktok.upload_video(access_token, media_path, content, **kwargs)
            elif platform == 'instagram' and media_path:
                # For Instagram, we need to upload the image first and get a URL
                container_id = self.instagram.create_media_container(access_token, media_path, content)
                return self.instagram.publish_media(access_token, container_id)
            elif platform == 'youtube' and media_path:
                return self.youtube.upload_video(access_token, media_path, content, **kwargs)
            else:
                raise SocialMediaError(f"Unsupported content type for {platform}")
        except Exception as e:
            logger.error(f"Failed to post to {platform}: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }


# Global instance
social_media = SocialMediaManager()