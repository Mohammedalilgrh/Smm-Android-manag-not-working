from app import app, login_manager
from flask_login import current_user
from auth import auth_bp
from routes import main_bp
from enhanced_routes import api_bp, auth_bp as social_auth_bp
from models import User
from bulk_upload_service import init_scheduler
import atexit

# Register blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(main_bp)
app.register_blueprint(api_bp)
app.register_blueprint(social_auth_bp)

# Initialize background scheduler
init_scheduler()

# Cleanup on exit
atexit.register(lambda: __import__('bulk_upload_service').cleanup_scheduler())

# User loader for Flask-Login
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Context processor to make current_user available in templates
@app.context_processor
def inject_user():
    return dict(current_user=current_user)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
