from app import db
from flask_login import UserMixin
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
import json

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    
    # Relationships
    social_accounts = db.relationship('SocialAccount', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    posts = db.relationship('Post', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    bulk_uploads = db.relationship('BulkUpload', backref='user', lazy='dynamic', cascade='all, delete-orphan')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def has_connected_account(self, platform):
        return self.social_accounts.filter_by(platform=platform, is_active=True).first() is not None

    def get_connected_platforms(self):
        return [acc.platform for acc in self.social_accounts.filter_by(is_active=True)]

class SocialAccount(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    platform = db.Column(db.String(50), nullable=False)  # 'tiktok', 'instagram', 'youtube'
    platform_user_id = db.Column(db.String(100), nullable=False)
    platform_username = db.Column(db.String(100))
    access_token = db.Column(db.Text)
    refresh_token = db.Column(db.Text)
    token_expires_at = db.Column(db.DateTime)
    is_active = db.Column(db.Boolean, default=True)
    connected_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_used = db.Column(db.DateTime)
    
    __table_args__ = (db.UniqueConstraint('user_id', 'platform', 'platform_user_id'),)

class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    platforms = db.Column(db.Text)  # JSON string of platforms
    hashtags = db.Column(db.Text)
    media_urls = db.Column(db.Text)  # JSON string of media URLs
    scheduled_for = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(20), default='scheduled')  # scheduled, posting, posted, failed
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    posted_at = db.Column(db.DateTime)
    error_message = db.Column(db.Text)
    job_id = db.Column(db.String(100))  # APScheduler job ID
    
    # Platform-specific post IDs
    platform_post_ids = db.Column(db.Text)  # JSON string

    def get_platforms(self):
        if self.platforms:
            return json.loads(self.platforms)
        return []

    def set_platforms(self, platforms_list):
        self.platforms = json.dumps(platforms_list)

    def get_platform_post_ids(self):
        if self.platform_post_ids:
            return json.loads(self.platform_post_ids)
        return {}

    def set_platform_post_ids(self, post_ids_dict):
        self.platform_post_ids = json.dumps(post_ids_dict)

    def get_media_urls(self):
        if self.media_urls:
            return json.loads(self.media_urls)
        return []

    def set_media_urls(self, urls_list):
        self.media_urls = json.dumps(urls_list)

class BulkUpload(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    total_posts = db.Column(db.Integer, default=0)
    processed_posts = db.Column(db.Integer, default=0)
    failed_posts = db.Column(db.Integer, default=0)
    status = db.Column(db.String(20), default='processing')  # processing, completed, failed
    upload_type = db.Column(db.String(20), default='daily')  # daily, custom, immediate
    start_date = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime)
    error_message = db.Column(db.Text)

class PostQueue(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)
    platform = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending, processing, completed, failed
    attempts = db.Column(db.Integer, default=0)
    max_attempts = db.Column(db.Integer, default=3)
    next_attempt = db.Column(db.DateTime)
    error_message = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime)
    
    post = db.relationship('Post', backref='queue_items')

class AppSettings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False)
    value = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    @staticmethod
    def get_setting(key, default=None):
        setting = AppSettings.query.filter_by(key=key).first()
        return setting.value if setting else default

    @staticmethod
    def set_setting(key, value):
        setting = AppSettings.query.filter_by(key=key).first()
        if setting:
            setting.value = value
            setting.updated_at = datetime.utcnow()
        else:
            setting = AppSettings(key=key, value=value)
            db.session.add(setting)
        db.session.commit()
