from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app import db

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    first_name = db.Column(db.String(100))
    last_name = db.Column(db.String(100))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Auto-scheduling preferences
    auto_schedule_enabled = db.Column(db.Boolean, default=False)
    daily_post_times = db.Column(db.JSON, default=list)  # ['09:00', '18:00']
    timezone = db.Column(db.String(50), default='UTC')
    
    # Relationships
    posts = db.relationship('Post', backref='author', lazy=True, cascade='all, delete-orphan')
    accounts = db.relationship('SocialAccount', backref='user', lazy=True, cascade='all, delete-orphan')
    bulk_uploads = db.relationship('BulkUpload', backref='user', lazy=True, cascade='all, delete-orphan')
    
    def set_password(self, password):
        """Hash and set the password"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Check if provided password matches hash"""
        return check_password_hash(self.password_hash, password)
    
    def get_full_name(self):
        """Get user's full name"""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        elif self.first_name:
            return self.first_name
        else:
            return self.username
    
    def __repr__(self):
        return f'<User {self.username}>'

class SocialAccount(db.Model):
    __tablename__ = 'social_accounts'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    platform = db.Column(db.String(50), nullable=False)  # 'tiktok', 'instagram', 'youtube'
    platform_user_id = db.Column(db.String(100))  # User ID on the platform
    platform_username = db.Column(db.String(100))  # Username on the platform
    access_token = db.Column(db.Text)  # OAuth access token (encrypted in production)
    refresh_token = db.Column(db.Text)  # OAuth refresh token
    token_expires_at = db.Column(db.DateTime)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Ensure one account per platform per user
    __table_args__ = (db.UniqueConstraint('user_id', 'platform', name='unique_user_platform'),)
    
    def __repr__(self):
        return f'<SocialAccount {self.platform} for user {self.user_id}>'

class Post(db.Model):
    __tablename__ = 'posts'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    media_url = db.Column(db.String(500))  # URL to uploaded media
    media_type = db.Column(db.String(50))  # 'image', 'video', etc.
    
    # Scheduling
    scheduled_time = db.Column(db.DateTime, nullable=False)
    timezone = db.Column(db.String(50), default='UTC')
    
    # Status tracking
    status = db.Column(db.String(50), default='scheduled')  # 'scheduled', 'posting', 'posted', 'failed'
    
    # Platform targeting
    target_platforms = db.Column(db.JSON)  # ['tiktok', 'instagram', 'youtube']
    
    # Results tracking
    posting_results = db.Column(db.JSON)  # Store results from each platform
    
    # Bulk upload reference
    bulk_upload_id = db.Column(db.Integer, db.ForeignKey('bulk_uploads.id'), nullable=True)
    
    # Hashtags and mentions
    hashtags = db.Column(db.JSON, default=list)
    mentions = db.Column(db.JSON, default=list)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    posted_at = db.Column(db.DateTime)
    
    def is_due_for_posting(self):
        """Check if post is ready to be published"""
        return (self.status == 'scheduled' and 
                self.scheduled_time <= datetime.utcnow())
    
    def get_platform_result(self, platform):
        """Get posting result for specific platform"""
        if self.posting_results and platform in self.posting_results:
            return self.posting_results[platform]
        return None
    
    def update_platform_result(self, platform, result):
        """Update posting result for specific platform"""
        if not self.posting_results:
            self.posting_results = {}
        self.posting_results[platform] = result
        db.session.commit()
    
    def __repr__(self):
        return f'<Post {self.id} by user {self.user_id}>'


class BulkUpload(db.Model):
    __tablename__ = 'bulk_uploads'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    total_posts = db.Column(db.Integer, default=0)
    processed_posts = db.Column(db.Integer, default=0)
    status = db.Column(db.String(20), default='processing')  # processing, completed, failed
    start_date = db.Column(db.DateTime, nullable=False)
    schedule_type = db.Column(db.String(20), default='daily')  # daily, custom, immediate
    target_platforms = db.Column(db.JSON, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    posts = db.relationship('Post', backref='bulk_upload', lazy=True)
    
    def __repr__(self):
        return f'<BulkUpload {self.name} by user {self.user_id}>'


class SchedulingQueue(db.Model):
    __tablename__ = 'scheduling_queue'
    
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('posts.id'), nullable=False)
    platform = db.Column(db.String(20), nullable=False)
    scheduled_time = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending, processing, completed, failed
    retry_count = db.Column(db.Integer, default=0)
    last_attempt = db.Column(db.DateTime, nullable=True)
    error_message = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship
    post = db.relationship('Post', backref='queue_items')
    
    def __repr__(self):
        return f'<SchedulingQueue {self.id} for post {self.post_id}>'