"""
Main application entry point for AI Song Workshop Website.
Multi-tenant: each HTTPS Basic Auth username is a school/tenant.
"""
import os
from pathlib import Path
from flask import Flask, request, Response, g
from flask_cors import CORS
from config import config
from backend.content_filter import ContentFilter
from backend.error_handling import ErrorLogger
from backend.callback_manager import CallbackManager
from backend.school_registry import SchoolRegistry
from backend.school_config import SchoolConfigManager
from backend.session_manager import SessionManager
from backend.profile_manager import ProfileManager
from backend.project_manager import ProjectManager
from backend.lyric_generator import LyricGenerator
from backend.song_producer import SongProducer
from backend.image_generator import ImageGenerator
from backend.photo_transformer import PhotoTransformer
from frontend.routes import bp
from frontend.admin_routes import admin_bp

# Create Flask application
app = Flask(__name__)
CORS(app)

# Configure Flask
app.config['SECRET_KEY'] = 'dev-secret-key-change-in-production'
app.config['SESSION_TYPE'] = 'filesystem'
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max upload
app.config['TEMPLATES_AUTO_RELOAD'] = True  # Force template reload

# --- Multi-tenant registry and config ---
school_registry = SchoolRegistry(registry_path="data/schools.json")
school_registry.initialize_from_env()

school_config_manager = SchoolConfigManager(base_path="data/schools")

# --- Global singletons (not tenant-scoped) ---
content_filter = ContentFilter()
callback_manager = CallbackManager(storage_path="data/callbacks")
error_logger = ErrorLogger()

# Callback URL from config (used by SongProducer per-request)
callback_url = config.callback_url if hasattr(config, 'callback_url') else None

# Base storage path for tenant-scoped session data
base_storage_path = config.session.storage_path

# Store global singletons and registry on app.config for route access
app.config['CALLBACK_MANAGER'] = callback_manager
app.config['SCHOOL_REGISTRY'] = school_registry
app.config['SCHOOL_CONFIG_MANAGER'] = school_config_manager
app.config['ADMIN_USERNAME'] = school_registry.get_admin_username()


def authenticate():
    """Send 401 response that enables basic auth."""
    return Response(
        'Authenticatie vereist.\n'
        'Authentication required.', 401,
        {'WWW-Authenticate': 'Basic realm="AI Song Workshop"'}
    )


@app.before_request
def require_authentication():
    """Require authentication for all requests except callback endpoint."""
    # Allow Suno callback endpoint without authentication
    if request.path == '/api/suno/callback':
        return None

    # Allow static files without extra processing
    if request.path.startswith('/static/'):
        return None

    auth = request.authorization
    if not auth or not school_registry.validate_credentials(auth.username, auth.password):
        return authenticate()

    # Set tenant context on flask.g
    g.https_username = auth.username
    g.school_config = school_config_manager.get_config(auth.username)

    # Set up per-request tenant-scoped components
    setup_tenant_context()


def setup_tenant_context():
    """Create per-request tenant-scoped components and store on flask.g."""
    username = g.https_username
    school_cfg = g.school_config

    # Tenant-scoped session manager
    tenant_storage = f"{base_storage_path}/{username}"
    session_manager = SessionManager(
        storage_path=tenant_storage,
        timeout_hours=config.session.timeout_hours
    )
    g.session_manager = session_manager

    # Profile and project managers (scoped to tenant session)
    g.profile_manager = ProfileManager(session_manager)
    g.project_manager = ProjectManager(session_manager)

    # Lyric generator: uses school's Anthropic key (or None if no key)
    if school_cfg.anthropic_api_key:
        g.lyric_generator = LyricGenerator(
            api_key=school_cfg.anthropic_api_key,
            content_filter=content_filter
        )
    else:
        g.lyric_generator = None

    # Song producer: uses school's Suno key and tenant-scoped audio path
    if school_cfg.suno_api_key:
        g.song_producer = SongProducer(
            api_key=school_cfg.suno_api_key,
            storage_path=f"static/audio/{username}",
            callback_url=callback_url,
            callback_manager=callback_manager
        )
    else:
        g.song_producer = None

    # Image generator: uses school's Google key and tenant-scoped image path
    if school_cfg.google_api_key:
        g.image_generator = ImageGenerator(
            api_key=school_cfg.google_api_key,
            content_filter=content_filter,
            storage_path=f"static/images/{username}"
        )
    else:
        g.image_generator = None

    # Photo transformer: uses school's Google key and tenant-scoped photo path
    if school_cfg.google_api_key and g.image_generator:
        g.photo_transformer = PhotoTransformer(
            image_generator=g.image_generator,
            content_filter=content_filter,
            session_manager=session_manager
        )
        # Override the default storage path to be tenant-scoped
        g.photo_transformer.storage_path = Path(f"static/photos/{username}")
        g.photo_transformer.storage_path.mkdir(parents=True, exist_ok=True)
    else:
        g.photo_transformer = None


# --- Routes registered (components now come from flask.g, set up in setup_tenant_context) ---
print("Initializing AI Song Workshop Website (multi-tenant)...")

# Register blueprints
app.register_blueprint(bp)
app.register_blueprint(admin_bp)


# Make school config available to templates
@app.context_processor
def inject_config():
    school_cfg = getattr(g, 'school_config', None)
    return {
        'config': config,
        'school_config': school_cfg,
        'admin_username': school_registry.get_admin_username(),
        'https_username': getattr(g, 'https_username', None),
    }


if __name__ == '__main__':
    print(f"Starting AI Song Workshop Website (multi-tenant)...")
    print(f"Session storage: {base_storage_path}")
    print(f"Callback URL: {callback_url or 'Not configured (polling only)'}")
    print(f"Schools registered: {len(school_registry.list_schools())}")
    print(f"\nServer running at http://{config.host}:{config.port}")

    app.run(
        host=config.host,
        port=config.port,
        debug=config.flask_debug
    )
