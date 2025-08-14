import os
import logging
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_cors import CORS
from werkzeug.middleware.proxy_fix import ProxyFix
from sqlalchemy.orm import DeclarativeBase
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
import atexit

# Configure logging
logging.basicConfig(level=logging.DEBUG)

class Base(DeclarativeBase):
    pass

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key-change-in-production")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)
CORS(app)

# Database configuration - SQLite for offline capabilities
database_url = os.environ.get("DATABASE_URL", "sqlite:///smm_agent.db")
# Convert postgres:// to postgresql:// for SQLAlchemy compatibility
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    'pool_pre_ping': True,
    "pool_recycle": 300,
}

# Initialize extensions
db = SQLAlchemy(app, model_class=Base)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Please log in to access this page.'

# Initialize scheduler
scheduler = None

def init_scheduler():
    global scheduler
    if scheduler is None:
        jobstores = {
            'default': SQLAlchemyJobStore(url=app.config["SQLALCHEMY_DATABASE_URI"])
        }
        scheduler = BackgroundScheduler(jobstores=jobstores)
        scheduler.start()
        logging.info("Background scheduler initialized")

def shutdown_scheduler():
    global scheduler
    if scheduler:
        scheduler.shutdown()
        logging.info("Background scheduler stopped")

# Register shutdown handler
atexit.register(shutdown_scheduler)

# Import models and create tables
with app.app_context():
    import models
    db.create_all()
    logging.info("Database tables created")
    
    # Initialize scheduler after database is ready
    init_scheduler()

# Import and register blueprints
from auth import auth_bp
from routes import main_bp
from social_auth import social_bp

app.register_blueprint(auth_bp, url_prefix='/auth')
app.register_blueprint(main_bp)
app.register_blueprint(social_bp, url_prefix='/social')

# User loader for Flask-Login
@login_manager.user_loader
def load_user(user_id):
    from models import User
    return User.query.get(int(user_id))

# Webhook endpoint for external integrations (like Telegram bots)
@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        data = request.get_json()
        logging.info(f"Webhook received: {data}")
        return jsonify({"status": "success"}), 200
    except Exception as e:
        logging.error(f"Webhook error: {e}")
        return jsonify({"error": str(e)}), 500

# Health check endpoint
@app.route('/health')
def health_check():
    return jsonify({"status": "healthy", "service": "SMM Automation Agent"}), 200
