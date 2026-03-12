"""
Main application entry point for AI Song Workshop Website.
"""
import os
from flask import Flask, request, Response
from flask_cors import CORS
from functools import wraps
from config import config
from backend.session_manager import SessionManager
from backend.profile_manager import ProfileManager
from backend.project_manager import ProjectManager
from backend.lyric_generator import LyricGenerator
from backend.song_producer import SongProducer
from backend.image_generator import ImageGenerator
from backend.content_filter import ContentFilter
from backend.error_handling import ErrorLogger
from backend.callback_manager import CallbackManager
from backend.photo_transformer import PhotoTransformer
from frontend.routes import bp, init_routes

# Create Flask application
app = Flask(__name__)
CORS(app)

# Configure Flask
app.config['SECRET_KEY'] = 'dev-secret-key-change-in-production'
app.config['SESSION_TYPE'] = 'filesystem'
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max upload
app.config['TEMPLATES_AUTO_RELOAD'] = True  # Force template reload

# HTTP Basic Authentication
# Configure users via AUTH_USERS env var: "user1:pass1,user2:pass2"
ADMIN_USERNAME = os.getenv('ADMIN_USERNAME', 'admin')

def _load_auth_users():
    """Parse AUTH_USERS env var into a dict."""
    users = {}
    for pair in os.getenv('AUTH_USERS', 'demo:demo123').split(','):
        if ':' in pair:
            u, p = pair.split(':', 1)
            users[u.strip()] = p.strip()
    return users

def check_auth(username, password):
    """Check if username/password combination is valid."""
    valid_users = _load_auth_users()
    return valid_users.get(username) == password

def authenticate():
    """Send 401 response that enables basic auth."""
    return Response(
        'Authenticatie vereist.\n'
        'Authentication required.', 401,
        {'WWW-Authenticate': 'Basic realm="AI Song Workshop"'}
    )

def requires_auth(f):
    """Decorator to require HTTP Basic Authentication."""
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return authenticate()
        return f(*args, **kwargs)
    return decorated

# Apply authentication to all routes
@app.before_request
def require_authentication():
    """Require authentication for all requests except callback endpoint."""
    # Allow Suno callback endpoint without authentication
    if request.path == '/api/suno/callback':
        return None
    
    auth = request.authorization
    if not auth or not check_auth(auth.username, auth.password):
        return authenticate()

# Initialize backend components
print("Initializing AI Song Workshop Website...")

# Session management
session_manager = SessionManager(
    storage_path=config.session.storage_path,
    timeout_hours=config.session.timeout_hours
)

# Content filter
content_filter = ContentFilter()

# Profile and project managers
profile_manager = ProfileManager(session_manager)
project_manager = ProjectManager(session_manager)

# API integrations
lyric_generator = LyricGenerator(
    api_key=config.api.anthropic_api_key,
    content_filter=content_filter
)

# Callback manager for Suno API
callback_manager = CallbackManager(storage_path="data/callbacks")

# Determine callback URL (use EC2 public DNS if available)
callback_url = config.callback_url if hasattr(config, 'callback_url') else None
if callback_url:
    print(f"Using callback URL: {callback_url}")
else:
    print("No callback URL configured, will use polling only")

song_producer = SongProducer(
    api_key=config.api.suno_api_key,
    storage_path="static/audio",
    callback_url=callback_url,
    callback_manager=callback_manager
)

image_generator = ImageGenerator(
    api_key=config.api.google_api_key,
    content_filter=content_filter,
    storage_path="static/images"
)

# Photo transformer (isolated photo feature)
photo_transformer = PhotoTransformer(
    image_generator=image_generator,
    content_filter=content_filter,
    session_manager=session_manager
)

# Error logging
error_logger = ErrorLogger()

# Initialize routes with components
init_routes(
    profile_manager,
    project_manager,
    lyric_generator,
    song_producer,
    image_generator,
    callback_manager,
    photo_transformer
)

# Register blueprints
app.register_blueprint(bp)

# Make config available to templates
@app.context_processor
def inject_config():
    return {'config': config, 'admin_username': ADMIN_USERNAME}


if __name__ == '__main__':
    print(f"Starting AI Song Workshop Website...")
    print(f"Class: {config.api.header.class_name}")
    print(f"Logo: {config.api.header.logo_path}")
    print(f"Session storage: {config.session.storage_path}")
    print(f"Image generation: {'Enabled' if image_generator.enabled else 'Disabled'}")
    print(f"\nServer running at http://{config.host}:{config.port}")
    
    app.run(
        host=config.host,
        port=config.port,
        debug=config.flask_debug
    )
