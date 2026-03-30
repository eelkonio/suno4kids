"""
Admin routes for AI Song Workshop multi-school management.
Provides school CRUD, API key management, global settings, credit checks, and data download.
"""
import io
import os
import zipfile
import logging
import requests

from flask import (
    Blueprint, render_template, request, redirect, url_for,
    jsonify, abort, g, current_app, send_file
)
from config import config

logger = logging.getLogger(__name__)

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


def _get_registry():
    return current_app.config['SCHOOL_REGISTRY']


def _get_config_manager():
    return current_app.config['SCHOOL_CONFIG_MANAGER']


def _get_admin_username():
    return current_app.config.get('ADMIN_USERNAME', 'admin')


@admin_bp.before_request
def require_admin():
    """Restrict all admin routes to the admin user."""
    if getattr(g, 'https_username', None) != _get_admin_username():
        abort(403)


# ============================================================
# Dashboard
# ============================================================

@admin_bp.route('/')
def dashboard():
    """Admin dashboard listing all schools."""
    registry = _get_registry()
    config_manager = _get_config_manager()

    schools = registry.list_schools()
    school_data = []
    for school in schools:
        username = school['username']
        cfg = config_manager.get_config(username)
        key_status = config_manager.get_api_key_status(username)
        school_data.append({
            'username': username,
            'created_at': school.get('created_at', ''),
            'class_name': cfg.class_name,
            'max_projects': cfg.max_projects_per_profile,
            'key_status': key_status,
        })

    return render_template('admin/dashboard.html',
                           schools=school_data,
                           admin_username=_get_admin_username(),
                           config=config)


# ============================================================
# School CRUD
# ============================================================

@admin_bp.route('/schools/add')
def add_school_form():
    """Display add-school form."""
    return render_template('admin/school_form.html',
                           is_edit=False,
                           school=None,
                           key_status=None,
                           key_hints={},
                           config=config)


@admin_bp.route('/schools/add', methods=['POST'])
def add_school():
    """Create a new school."""
    registry = _get_registry()
    config_manager = _get_config_manager()

    username = request.form.get('username', '').strip()
    password = request.form.get('password', '').strip()

    if not username or not password:
        return render_template('admin/school_form.html',
                               is_edit=False,
                               school=None,
                               key_status=None,
                               key_hints={},
                               error='Username and password are required.',
                               config=config)

    try:
        registry.add_school(username, password)
    except ValueError as e:
        return render_template('admin/school_form.html',
                               is_edit=False,
                               school=None,
                               key_status=None,
                               key_hints={},
                               error=str(e),
                               config=config)

    # Create default config
    config_manager.create_default_config(username)

    # Create tenant directories
    _create_tenant_dirs(username)

    return redirect(url_for('admin.dashboard'))


@admin_bp.route('/schools/<username>/edit')
def edit_school_form(username):
    """Display edit-school form."""
    config_manager = _get_config_manager()
    cfg = config_manager.get_config(username)
    key_status = config_manager.get_api_key_status(username)
    key_hints = {
        'anthropic': config_manager.get_api_key_hint(username, 'anthropic'),
        'suno': config_manager.get_api_key_hint(username, 'suno'),
        'google': config_manager.get_api_key_hint(username, 'google'),
    }

    school = {
        'username': username,
        'class_name': cfg.class_name,
        'logo_path': cfg.logo_path,
        'max_projects': cfg.max_projects_per_profile,
    }

    return render_template('admin/school_form.html',
                           is_edit=True,
                           school=school,
                           key_status=key_status,
                           key_hints=key_hints,
                           config=config)


@admin_bp.route('/schools/<username>/edit', methods=['POST'])
def edit_school(username):
    """Save school config changes."""
    config_manager = _get_config_manager()
    cfg = config_manager.get_config(username)

    cfg.class_name = request.form.get('class_name', cfg.class_name).strip()
    cfg.logo_path = request.form.get('logo_path', cfg.logo_path).strip()

    try:
        cfg.max_projects_per_profile = int(request.form.get('max_projects', cfg.max_projects_per_profile))
    except (ValueError, TypeError):
        pass

    config_manager.save_config(username, cfg)
    return redirect(url_for('admin.edit_school_form', username=username))


@admin_bp.route('/schools/<username>/password', methods=['POST'])
def update_password(username):
    """Update a school's password."""
    registry = _get_registry()
    new_password = request.form.get('password', '').strip()

    if not new_password:
        return redirect(url_for('admin.edit_school_form', username=username))

    try:
        registry.update_password(username, new_password)
    except ValueError:
        pass

    return redirect(url_for('admin.edit_school_form', username=username))


@admin_bp.route('/schools/<username>/delete', methods=['POST'])
def delete_school(username):
    """Delete a school (prevent admin self-delete)."""
    registry = _get_registry()

    try:
        registry.delete_school(username)
    except ValueError:
        # Cannot delete admin or non-existent school
        pass

    return redirect(url_for('admin.dashboard'))


# ============================================================
# API Key Management
# ============================================================

@admin_bp.route('/schools/<username>/api-keys', methods=['POST'])
def set_api_keys(username):
    """Set API keys for a school."""
    config_manager = _get_config_manager()

    messages = []
    for service in ('anthropic', 'suno', 'google'):
        key_value = request.form.get(f'{service}_api_key', '').strip()
        if key_value:
            config_manager.set_api_key(username, service, key_value)
            hint = key_value[-4:] if len(key_value) >= 4 else key_value
            messages.append(f'{service.capitalize()} key set: ****{hint}')

    return redirect(url_for('admin.edit_school_form', username=username))


@admin_bp.route('/schools/<username>/clear-api-key', methods=['POST'])
def clear_api_key(username):
    """Clear a specific API key."""
    config_manager = _get_config_manager()
    service = request.form.get('service', '').strip()

    if service in ('anthropic', 'suno', 'google'):
        config_manager.clear_api_key(username, service)

    return redirect(url_for('admin.edit_school_form', username=username))


# ============================================================
# Global Settings
# ============================================================

@admin_bp.route('/settings')
def settings_form():
    """Display global settings form."""
    registry = _get_registry()
    global_settings = registry.get_global_settings()
    return render_template('admin/settings.html',
                           settings=global_settings,
                           config=config)


@admin_bp.route('/settings', methods=['POST'])
def save_settings():
    """Save global settings."""
    registry = _get_registry()

    try:
        default_max = int(request.form.get('default_max_projects_per_profile', 10))
    except (ValueError, TypeError):
        default_max = 10

    registry.update_global_settings({
        'default_max_projects_per_profile': default_max,
    })

    return redirect(url_for('admin.settings_form'))


# ============================================================
# Suno Credit Check (AJAX)
# ============================================================

@admin_bp.route('/api/suno-credits/<username>')
def suno_credits(username):
    """AJAX endpoint: fetch Suno API credits for a school."""
    config_manager = _get_config_manager()
    cfg = config_manager.get_config(username)

    if not cfg.suno_api_key:
        return jsonify({'error': 'No Suno API key configured'})

    try:
        resp = requests.get(
            'https://api.sunoapi.org/api/v1/generate/credit',
            headers={'Authorization': f'Bearer {cfg.suno_api_key}'},
            timeout=10,
        )
        if resp.status_code == 200:
            data = resp.json()
            # The API may return credits in different formats
            credits = data.get('credits', data.get('data', {}).get('credits', None))
            if credits is not None:
                return jsonify({'credits': credits})
            # Try to return the whole data if credits field not found
            return jsonify({'credits': data})
        else:
            return jsonify({'error': 'Unable to check'})
    except Exception as e:
        logger.error(f"Suno credit check failed for {username}: {e}")
        return jsonify({'error': 'Unable to check'})


# ============================================================
# Per-School Data Download
# ============================================================

@admin_bp.route('/schools/<username>/download')
def download_school_data(username):
    """Generate and send a zip file with all school data."""
    base_static = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static')

    dirs_to_zip = {
        'audio': os.path.join(base_static, 'audio', username),
        'images': os.path.join(base_static, 'images', username),
        'photos': os.path.join(base_static, 'photos', username),
    }

    mem_zip = io.BytesIO()
    file_count = 0

    with zipfile.ZipFile(mem_zip, 'w', zipfile.ZIP_DEFLATED) as zf:
        for subdir_name, dir_path in dirs_to_zip.items():
            if not os.path.isdir(dir_path):
                continue
            for root, _dirs, files in os.walk(dir_path):
                for fname in files:
                    full_path = os.path.join(root, fname)
                    arcname = os.path.join(subdir_name, os.path.relpath(full_path, dir_path))
                    zf.write(full_path, arcname)
                    file_count += 1

    if file_count == 0:
        return render_template('admin/dashboard.html',
                               schools=_build_school_data(),
                               admin_username=_get_admin_username(),
                               error=f'No data available for {username}.',
                               config=config)

    mem_zip.seek(0)
    return send_file(
        mem_zip,
        mimetype='application/zip',
        as_attachment=True,
        download_name=f'{username}_data.zip',
    )


# ============================================================
# Helpers
# ============================================================

def _create_tenant_dirs(username):
    """Create tenant-scoped storage directories for a new school."""
    base_storage = config.session.storage_path
    dirs = [
        os.path.join(base_storage, username, 'profiles'),
        os.path.join(base_storage, username, 'projects'),
        os.path.join('static', 'audio', username),
        os.path.join('static', 'images', username),
        os.path.join('static', 'photos', username),
    ]
    for d in dirs:
        os.makedirs(d, exist_ok=True)


def _build_school_data():
    """Build school data list for dashboard rendering."""
    registry = _get_registry()
    config_manager = _get_config_manager()
    schools = registry.list_schools()
    school_data = []
    for school in schools:
        username = school['username']
        cfg = config_manager.get_config(username)
        key_status = config_manager.get_api_key_status(username)
        school_data.append({
            'username': username,
            'created_at': school.get('created_at', ''),
            'class_name': cfg.class_name,
            'max_projects': cfg.max_projects_per_profile,
            'key_status': key_status,
        })
    return school_data
