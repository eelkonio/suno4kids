"""
Frontend routes for AI Song Workshop Website.
Multi-tenant: uses flask.g for tenant-scoped components set up by app.py before_request.
"""
import os
import re
from flask import Blueprint, render_template, request, redirect, url_for, jsonify, make_response, g, current_app
import asyncio
import logging
from backend.error_handling import get_dutch_error_message
from config import config

logger = logging.getLogger(__name__)

# Create blueprint
bp = Blueprint('main', __name__)


def _get_callback_manager():
    """Get the global callback manager from app config."""
    return current_app.config.get('CALLBACK_MANAGER')


def _get_admin_username():
    """Get the admin username from app config."""
    return current_app.config.get('ADMIN_USERNAME', 'admin')


def _is_admin():
    """Check if the current user is the admin."""
    return getattr(g, 'https_username', None) == _get_admin_username()


def _collect_songs_for_school(profile_manager, project_manager, school_label=None):
    """Collect all songs from a single tenant-scoped profile/project manager."""
    songs = []
    all_profiles = profile_manager.session_manager.list_profiles()
    for profile in all_profiles:
        for project_id in profile.project_ids:
            project = project_manager.get_project(project_id)
            if project and project.song_generated and project.song_file_path:
                is_disabled = project.song_file_path.endswith('.disabled')
                title = project.description[:50] if project.description else "Untitled"
                if len(project.description or "") > 50:
                    title += "..."
                song = {
                    'project_id': project.id,
                    'title': title,
                    'username': profile.name,
                    'song_path': project.song_file_path,
                    'image_path': project.image_file_path,
                    'created_at': project.created_at,
                    'is_disabled': is_disabled,
                }
                if school_label:
                    song['school'] = school_label
                songs.append(song)
    return songs


def _collect_photos_for_school(photos_dir):
    """Collect all photos from a specific photos directory, grouped by user."""
    users = []
    if not os.path.isdir(photos_dir):
        return users

    for user_dir_name in sorted(os.listdir(photos_dir)):
        user_path = os.path.join(photos_dir, user_dir_name)
        if not os.path.isdir(user_path):
            continue

        display_name = re.sub(r'_[a-f0-9]{4}$', '', user_dir_name)

        files = os.listdir(user_path)
        pairs = {}
        for f in sorted(files):
            if not f.endswith('.png'):
                continue
            parts = f.rsplit('.', 1)[0]
            if parts.startswith('original_'):
                key = parts[len('original_'):]
                pairs.setdefault(key, {})['original'] = f'photos/{user_dir_name}/{f}'
            elif parts.startswith('transformed_'):
                key = parts[len('transformed_'):]
                pairs.setdefault(key, {})['transformed'] = f'photos/{user_dir_name}/{f}'

        photo_list = []
        for key in sorted(pairs.keys(), reverse=True):
            p = pairs[key]
            style = key.rsplit('_', 1)[0] if '_' in key else key
            photo_list.append({
                'style': style,
                'original': p.get('original'),
                'transformed': p.get('transformed'),
            })

        if photo_list:
            users.append({'name': display_name, 'photos': photo_list})

    return users


# ============================================================
# Page Routes
# ============================================================

@bp.route('/')
def index():
    """Homepage with welcome message and explanation."""
    return render_template('home.html', config=config)


@bp.route('/profile')
def profile_page():
    """Profile creation/selection page. Skips if cookie has valid profile."""
    cookie_id = request.cookies.get('profile_id')
    if cookie_id:
        profile = g.profile_manager.session_manager.load_profile(cookie_id)
        if profile:
            return redirect(url_for('main.list_projects', profile_id=profile.id))
    return render_template('profile.html', config=config)


@bp.route('/profile', methods=['POST'])
def create_or_select_profile():
    """Create or select user profile."""
    name = request.form.get('name', '').strip()

    try:
        profile = g.profile_manager.create_or_get_profile(name)
        resp = make_response(redirect(url_for('main.list_projects', profile_id=profile.id)))
        resp.set_cookie('profile_id', profile.id, max_age=60*60*24*30, samesite='Lax')
        return resp
    except ValueError as e:
        return render_template('profile.html', error=str(e), config=config)


@bp.route('/profile/<profile_id>/projects')
def list_projects(profile_id):
    """List all projects for a profile."""
    profile = g.profile_manager.session_manager.load_profile(profile_id)
    if not profile:
        return render_template('profile.html',
                             error=get_dutch_error_message('profile_not_found'),
                             config=config)

    projects = g.project_manager.list_projects(profile_id)
    max_projects = g.school_config.max_projects_per_profile
    return render_template('projects.html', profile=profile, projects=projects,
                         config=config, max_projects=max_projects)


@bp.route('/profile/<profile_id>/projects/new')
def create_project(profile_id):
    """Create new project and redirect to editing."""
    max_projects = g.school_config.max_projects_per_profile
    try:
        project = g.project_manager.create_project(profile_id, max_projects=max_projects)
        return redirect(url_for('main.edit_project', project_id=project.id))
    except ValueError as e:
        profile = g.profile_manager.session_manager.load_profile(profile_id)
        projects = g.project_manager.list_projects(profile_id)
        return render_template('projects.html',
                             profile=profile,
                             projects=projects,
                             error=str(e),
                             config=config,
                             max_projects=max_projects)


@bp.route('/project/<project_id>')
def edit_project(project_id):
    """Project editing page."""
    project = g.project_manager.get_project(project_id)
    if not project:
        return "Project niet gevonden", 404

    return render_template('project.html', project=project, config=config)


# ============================================================
# API Routes
# ============================================================

@bp.route('/api/project/<project_id>', methods=['PUT'])
def update_project(project_id):
    """Update project fields."""
    try:
        data = request.get_json()
        project = g.project_manager.update_project(project_id, data)

        if not project:
            return jsonify({'success': False, 'error': 'Project niet gevonden'}), 404

        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/api/project/<project_id>/generate-lyrics', methods=['POST'])
def generate_lyrics_route(project_id):
    """Generate lyrics for project."""
    try:
        if not g.lyric_generator:
            return jsonify({'success': False,
                          'error': 'Tekst genereren is niet beschikbaar — neem contact op met de beheerder'}), 503

        project = g.project_manager.get_project(project_id)
        if not project:
            return jsonify({'success': False, 'error': 'Project niet gevonden'}), 404

        if not project.description or not project.genre:
            return jsonify({'success': False, 'error': 'Vul eerst beschrijving en genre in'}), 400

        # Generate lyrics asynchronously
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        lyrics = loop.run_until_complete(
            g.lyric_generator.generate_lyrics(project.description, project.genre)
        )
        loop.close()

        # Update project
        g.project_manager.update_project(project_id, {
            'lyrics': lyrics,
            'lyrics_generated': True
        })

        return jsonify({'success': True, 'lyrics': lyrics})

    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        return jsonify({'success': False, 'error': get_dutch_error_message('api_unavailable')}), 500


@bp.route('/api/project/<project_id>/generate-song', methods=['POST'])
def generate_song_route(project_id):
    """Generate song for project."""
    try:
        if not g.song_producer:
            return jsonify({'success': False,
                          'error': 'Liedje genereren is niet beschikbaar — neem contact op met de beheerder'}), 503

        project = g.project_manager.get_project(project_id)
        if not project:
            return jsonify({'success': False, 'error': 'Project niet gevonden'}), 404

        if not project.lyrics or not project.genre:
            return jsonify({'success': False, 'error': 'Eerst tekst genereren'}), 400

        # Get profile for username
        profile = g.profile_manager.session_manager.load_profile(project.profile_id)
        username = profile.name if profile else None

        # Generate song asynchronously
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        song_path = loop.run_until_complete(
            g.song_producer.generate_song(project.lyrics, project.genre, username=username)
        )
        loop.close()

        # Remove 'static/' prefix if present for url_for compatibility
        display_path = song_path
        if song_path.startswith('static/'):
            display_path = song_path[7:]

        # Update project
        g.project_manager.update_project(project_id, {
            'song_file_path': display_path,
            'song_generated': True
        })

        return jsonify({'success': True, 'song_path': display_path})

    except Exception as e:
        return jsonify({'success': False, 'error': get_dutch_error_message('generation_failed')}), 500


@bp.route('/api/project/<project_id>/generate-image', methods=['POST'])
def generate_image_route(project_id):
    """Generate image for project."""
    try:
        if not g.image_generator:
            return jsonify({'success': False,
                          'error': 'Afbeelding genereren is niet beschikbaar — neem contact op met de beheerder'}), 503

        if not g.image_generator.enabled:
            return jsonify({'success': False, 'error': 'Afbeelding generatie niet beschikbaar'}), 400

        project = g.project_manager.get_project(project_id)
        if not project:
            return jsonify({'success': False, 'error': 'Project niet gevonden'}), 404

        if not project.description or not project.lyrics:
            return jsonify({'success': False, 'error': 'Eerst beschrijving en tekst nodig'}), 400

        # Get profile for username
        profile = g.profile_manager.session_manager.load_profile(project.profile_id)
        username = profile.name if profile else None

        # Generate image asynchronously
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        image_path = loop.run_until_complete(
            g.image_generator.generate_image(project.description, project.lyrics, username=username)
        )
        loop.close()

        if image_path:
            display_path = image_path
            if image_path.startswith('static/'):
                display_path = image_path[7:]

            # Update project
            g.project_manager.update_project(project_id, {
                'image_file_path': display_path,
                'image_generated': True
            })

            return jsonify({'success': True, 'image_path': display_path})
        else:
            return jsonify({'success': False, 'error': 'Afbeelding generatie mislukt'}), 500

    except NotImplementedError:
        return jsonify({'success': False, 'error': 'Afbeelding generatie nog niet geïmplementeerd'}), 501
    except Exception as e:
        return jsonify({'success': False, 'error': get_dutch_error_message('generation_failed')}), 500


# ============================================================
# Suno Callback Routes (callback_manager is a global singleton)
# ============================================================

@bp.route('/api/suno/callback', methods=['POST'])
def suno_callback():
    """
    Receive callback from Suno API when song generation completes.
    This route runs WITHOUT authentication — no g.https_username available.
    Uses the global callback_manager from app.config.
    """
    try:
        callback_data = request.get_json()

        logger.info("Received Suno callback")
        logger.info(f"Callback data: {callback_data}")

        task_id = callback_data.get('taskId') or callback_data.get('task_id')

        if not task_id:
            logger.error("No task ID in callback data")
            logger.error(f"Callback keys: {list(callback_data.keys())}")
            return jsonify({'success': False, 'error': 'No task ID provided'}), 400

        cb_manager = _get_callback_manager()
        if cb_manager:
            cb_manager.store_callback(task_id, callback_data)
            logger.info(f"Callback stored for task {task_id}")
        else:
            logger.warning("CallbackManager not initialized, callback not stored")

        return jsonify({'success': True, 'task_id': task_id}), 200

    except Exception as e:
        logger.error(f"Error processing Suno callback: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/api/suno/status/<task_id>', methods=['GET'])
def check_suno_status(task_id):
    """Check if a Suno task has completed via callback."""
    try:
        cb_manager = _get_callback_manager()
        if not cb_manager:
            return jsonify({'success': False, 'error': 'Callback manager not initialized'}), 500

        is_complete = cb_manager.is_complete(task_id)

        if is_complete:
            audio_url = cb_manager.get_audio_url(task_id)
            callback_data = cb_manager.get_callback(task_id)

            return jsonify({
                'success': True,
                'complete': True,
                'audio_url': audio_url,
                'callback_data': callback_data
            })
        else:
            return jsonify({
                'success': True,
                'complete': False
            })

    except Exception as e:
        logger.error(f"Error checking Suno status: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================
# All Songs / All Photos (tenant-scoped)
# ============================================================

@bp.route('/allsongs')
def all_songs():
    """
    Display all generated songs, ordered by date (newest first).
    Non-admin: only songs from the current school (tenant-scoped g.profile_manager).
    Admin: songs from ALL schools, labeled by school.
    """
    try:
        is_admin = _is_admin()

        if is_admin:
            # Admin sees songs from all schools
            school_registry = current_app.config.get('SCHOOL_REGISTRY')
            school_config_manager = current_app.config.get('SCHOOL_CONFIG_MANAGER')

            from backend.session_manager import SessionManager
            from backend.profile_manager import ProfileManager
            from backend.project_manager import ProjectManager

            songs = []
            if school_registry:
                base_storage = config.session.storage_path
                for school in school_registry.list_schools():
                    username = school['username']
                    tenant_storage = f"{base_storage}/{username}"
                    try:
                        sm = SessionManager(
                            storage_path=tenant_storage,
                            timeout_hours=config.session.timeout_hours
                        )
                        pm = ProfileManager(sm)
                        pjm = ProjectManager(sm)
                        songs.extend(_collect_songs_for_school(pm, pjm, school_label=username))
                    except Exception as e:
                        logger.error(f"Error loading songs for school {username}: {e}")
                        continue
        else:
            # Non-admin: only songs from current school
            songs = _collect_songs_for_school(g.profile_manager, g.project_manager)

        # Sort by creation date, newest first
        songs.sort(key=lambda s: s['created_at'], reverse=True)

        return render_template('allsongs.html', songs=songs, is_admin=is_admin, config=config)

    except Exception as e:
        logger.error(f"Error loading all songs: {str(e)}", exc_info=True)
        return "Error loading songs", 500


@bp.route('/api/song/<project_id>/disable', methods=['POST'])
def disable_song(project_id):
    """
    Disable a song by appending .disabled to the filename in the database.
    Only accessible by admin user.
    """
    try:
        if not _is_admin():
            return jsonify({'success': False, 'error': 'Unauthorized'}), 403

        project = g.project_manager.get_project(project_id)
        if not project:
            return jsonify({'success': False, 'error': 'Project not found'}), 404

        if not project.song_file_path:
            return jsonify({'success': False, 'error': 'No song to disable'}), 400

        if project.song_file_path.endswith('.disabled'):
            return jsonify({'success': False, 'error': 'Song already disabled'}), 400

        new_path = project.song_file_path + '.disabled'
        g.project_manager.update_project(project_id, {
            'song_file_path': new_path
        })

        logger.info(f"Song disabled by {g.https_username}: {project_id}")
        return jsonify({'success': True})

    except Exception as e:
        logger.error(f"Error disabling song: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/api/song/<project_id>/enable', methods=['POST'])
def enable_song(project_id):
    """
    Enable a disabled song by removing .disabled from the filename in the database.
    Only accessible by admin user.
    """
    try:
        if not _is_admin():
            return jsonify({'success': False, 'error': 'Unauthorized'}), 403

        project = g.project_manager.get_project(project_id)
        if not project:
            return jsonify({'success': False, 'error': 'Project not found'}), 404

        if not project.song_file_path:
            return jsonify({'success': False, 'error': 'No song to enable'}), 400

        if not project.song_file_path.endswith('.disabled'):
            return jsonify({'success': False, 'error': 'Song is not disabled'}), 400

        new_path = project.song_file_path[:-9]  # Remove '.disabled' (9 characters)
        g.project_manager.update_project(project_id, {
            'song_file_path': new_path
        })

        logger.info(f"Song enabled by {g.https_username}: {project_id}")
        return jsonify({'success': True})

    except Exception as e:
        logger.error(f"Error enabling song: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================
# Photo Transformation Routes
# ============================================================

@bp.route('/photo-transform')
def photo_transform_page():
    """Photo transformation page with webcam capture and style selection."""
    if not g.photo_transformer:
        return "Foto transformatie niet beschikbaar — neem contact op met de beheerder", 503

    profile_id = request.args.get('profile_id') or request.cookies.get('profile_id')
    if not profile_id:
        return render_template('photo_profile.html', config=config)

    profile = g.profile_manager.session_manager.load_profile(profile_id)
    if not profile:
        return render_template('photo_profile.html', error='Profiel niet gevonden', config=config)

    styles = g.photo_transformer.get_all_styles()
    return render_template('photo_transform.html', styles=styles, profile=profile, config=config)


@bp.route('/photo-transform', methods=['POST'])
def photo_transform_create_profile():
    """Create or load profile, then redirect to photo transform with profile_id."""
    name = request.form.get('name', '').strip()
    if not name:
        return render_template('photo_profile.html', error='Vul je naam in!', config=config)
    try:
        profile = g.profile_manager.create_or_get_profile(name)
        resp = make_response(redirect(url_for('main.photo_transform_page', profile_id=profile.id)))
        resp.set_cookie('profile_id', profile.id, max_age=60*60*24*30, samesite='Lax')
        return resp
    except ValueError as e:
        return render_template('photo_profile.html', error=str(e), config=config)


@bp.route('/api/photo/styles', methods=['GET'])
def get_photo_styles():
    """Return all available photo transformation styles as JSON."""
    if not g.photo_transformer:
        return jsonify({'success': False, 'error': 'Photo transformer not available'}), 503
    styles = g.photo_transformer.get_all_styles()
    return jsonify({'success': True, 'styles': styles})


@bp.route('/api/photo/transform', methods=['POST'])
def transform_photo_route():
    """
    Transform a photo using the specified style.
    Expects JSON: {image: base64_string, style: style_id, username: string}
    """
    if not g.photo_transformer:
        return jsonify({'success': False, 'error': 'Afbeelding genereren is niet beschikbaar — neem contact op met de beheerder'}), 503

    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'Geen data ontvangen'}), 400

        image_b64 = data.get('image')
        style_id = data.get('style')
        username = data.get('username', 'anonymous')

        if not image_b64:
            return jsonify({'success': False, 'error': 'Geen afbeelding ontvangen'}), 400
        if not style_id:
            return jsonify({'success': False, 'error': 'Geen stijl geselecteerd'}), 400

        # Strip data URL prefix if present (e.g. "data:image/png;base64,...")
        if ',' in image_b64:
            image_b64 = image_b64.split(',', 1)[1]

        # Run async transform
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(
            g.photo_transformer.transform_photo(image_b64, style_id, username)
        )
        loop.close()

        return jsonify(result)

    except Exception as e:
        logger.error(f"Photo transform route error: {e}", exc_info=True)
        return jsonify({'success': False, 'error': 'Er ging iets mis bij de transformatie'}), 500


@bp.route('/allphotos')
def all_photos():
    """
    Display all transformed photos grouped by user.
    Non-admin: only photos from the current school.
    Admin: photos from ALL schools.
    """
    is_admin = _is_admin()

    if is_admin:
        # Admin sees photos from all schools
        school_registry = current_app.config.get('SCHOOL_REGISTRY')
        users = []
        if school_registry:
            for school in school_registry.list_schools():
                username = school['username']
                school_photos_dir = os.path.join('static', 'photos', username)
                school_users = _collect_photos_for_school(school_photos_dir)
                # Tag each user group with the school name
                for u in school_users:
                    u['school'] = username
                users.extend(school_users)
    else:
        # Non-admin: only photos from current school
        school_photos_dir = os.path.join('static', 'photos', g.https_username)
        users = _collect_photos_for_school(school_photos_dir)

    return render_template('allphotos.html', users=users, is_admin=is_admin, config=config)
