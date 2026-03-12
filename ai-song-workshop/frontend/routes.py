"""
Frontend routes for AI Song Workshop Website.
"""
import os
from flask import Blueprint, render_template, request, redirect, url_for, jsonify, make_response
import asyncio
import logging
from backend.profile_manager import ProfileManager
from backend.project_manager import ProjectManager
from backend.lyric_generator import LyricGenerator
from backend.song_producer import SongProducer
from backend.image_generator import ImageGenerator
from backend.content_filter import ContentFilter
from backend.error_handling import get_dutch_error_message
from backend.callback_manager import CallbackManager
from config import config

logger = logging.getLogger(__name__)

ADMIN_USERNAME = os.getenv('ADMIN_USERNAME', 'admin')

# Create blueprint
bp = Blueprint('main', __name__)

# Initialize components (will be set by app.py)
profile_manager = None
project_manager = None
lyric_generator = None
song_producer = None
image_generator = None
callback_manager = None
photo_transformer = None


def init_routes(pm, pjm, lg, sp, ig, cm=None, pt=None):
    """Initialize route handlers with component instances."""
    global profile_manager, project_manager, lyric_generator, song_producer, image_generator, callback_manager, photo_transformer
    profile_manager = pm
    project_manager = pjm
    lyric_generator = lg
    song_producer = sp
    image_generator = ig
    callback_manager = cm
    photo_transformer = pt


@bp.route('/')
def index():
    """Homepage with welcome message and explanation."""
    return render_template('home.html', config=config)


@bp.route('/profile')
def profile_page():
    """Profile creation/selection page. Skips if cookie has valid profile."""
    cookie_id = request.cookies.get('profile_id')
    if cookie_id:
        profile = profile_manager.session_manager.load_profile(cookie_id)
        if profile:
            return redirect(url_for('main.list_projects', profile_id=profile.id))
    return render_template('profile.html', config=config)


@bp.route('/profile', methods=['POST'])
def create_or_select_profile():
    """Create or select user profile."""
    name = request.form.get('name', '').strip()
    
    try:
        profile = profile_manager.create_or_get_profile(name)
        resp = make_response(redirect(url_for('main.list_projects', profile_id=profile.id)))
        resp.set_cookie('profile_id', profile.id, max_age=60*60*24*30, samesite='Lax')
        return resp
    except ValueError as e:
        return render_template('profile.html', error=str(e), config=config)



@bp.route('/profile/<profile_id>/projects')
def list_projects(profile_id):
    """List all projects for a profile."""
    profile = profile_manager.session_manager.load_profile(profile_id)
    if not profile:
        return render_template('profile.html', 
                             error=get_dutch_error_message('profile_not_found'),
                             config=config)
    
    projects = project_manager.list_projects(profile_id)
    return render_template('projects.html', profile=profile, projects=projects, config=config)


@bp.route('/profile/<profile_id>/projects/new')
def create_project(profile_id):
    """Create new project and redirect to editing."""
    try:
        project = project_manager.create_project(profile_id)
        return redirect(url_for('main.edit_project', project_id=project.id))
    except ValueError as e:
        # Project limit reached or profile not found
        profile = profile_manager.session_manager.load_profile(profile_id)
        projects = project_manager.list_projects(profile_id)
        return render_template('projects.html', 
                             profile=profile, 
                             projects=projects, 
                             error=str(e),
                             config=config)


@bp.route('/project/<project_id>')
def edit_project(project_id):
    """Project editing page."""
    project = project_manager.get_project(project_id)
    if not project:
        return "Project niet gevonden", 404
    
    return render_template('project.html', project=project, config=config)



# API Routes

@bp.route('/api/project/<project_id>', methods=['PUT'])
def update_project(project_id):
    """Update project fields."""
    try:
        data = request.get_json()
        project = project_manager.update_project(project_id, data)
        
        if not project:
            return jsonify({'success': False, 'error': 'Project niet gevonden'}), 404
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/api/project/<project_id>/generate-lyrics', methods=['POST'])
def generate_lyrics_route(project_id):
    """Generate lyrics for project."""
    try:
        project = project_manager.get_project(project_id)
        if not project:
            return jsonify({'success': False, 'error': 'Project niet gevonden'}), 404
        
        if not project.description or not project.genre:
            return jsonify({'success': False, 'error': 'Vul eerst beschrijving en genre in'}), 400
        
        # Generate lyrics asynchronously
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        lyrics = loop.run_until_complete(
            lyric_generator.generate_lyrics(project.description, project.genre)
        )
        loop.close()
        
        # Update project
        project_manager.update_project(project_id, {
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
        project = project_manager.get_project(project_id)
        if not project:
            return jsonify({'success': False, 'error': 'Project niet gevonden'}), 404
        
        if not project.lyrics or not project.genre:
            return jsonify({'success': False, 'error': 'Eerst tekst genereren'}), 400
        
        # Get profile for username
        profile = profile_manager.session_manager.load_profile(project.profile_id)
        username = profile.name if profile else None
        
        # Generate song asynchronously
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        song_path = loop.run_until_complete(
            song_producer.generate_song(project.lyrics, project.genre, username=username)
        )
        loop.close()
        
        # Remove 'static/' prefix if present for url_for compatibility
        display_path = song_path
        if song_path.startswith('static/'):
            display_path = song_path[7:]  # Remove 'static/' prefix
        
        # Update project
        project_manager.update_project(project_id, {
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
        if not image_generator or not image_generator.enabled:
            return jsonify({'success': False, 'error': 'Afbeelding generatie niet beschikbaar'}), 400
        
        project = project_manager.get_project(project_id)
        if not project:
            return jsonify({'success': False, 'error': 'Project niet gevonden'}), 404
        
        if not project.description or not project.lyrics:
            return jsonify({'success': False, 'error': 'Eerst beschrijving en tekst nodig'}), 400
        
        # Get profile for username
        profile = profile_manager.session_manager.load_profile(project.profile_id)
        username = profile.name if profile else None
        
        # Generate image asynchronously
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        image_path = loop.run_until_complete(
            image_generator.generate_image(project.description, project.lyrics, username=username)
        )
        loop.close()
        
        if image_path:
            # Remove 'static/' prefix if present for url_for compatibility
            # url_for('static', filename='...') expects path relative to static/
            display_path = image_path
            if image_path.startswith('static/'):
                display_path = image_path[7:]  # Remove 'static/' prefix
            
            # Update project
            project_manager.update_project(project_id, {
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


@bp.route('/api/suno/callback', methods=['POST'])
def suno_callback():
    """
    Receive callback from Suno API when song generation completes.
    """
    try:
        callback_data = request.get_json()
        
        logger.info("Received Suno callback")
        logger.info(f"Callback data: {callback_data}")
        
        # Extract task ID from callback
        task_id = callback_data.get('taskId') or callback_data.get('task_id')
        
        if not task_id:
            logger.error("No task ID in callback data")
            logger.error(f"Callback keys: {list(callback_data.keys())}")
            return jsonify({'success': False, 'error': 'No task ID provided'}), 400
        
        # Store callback data
        if callback_manager:
            callback_manager.store_callback(task_id, callback_data)
            logger.info(f"Callback stored for task {task_id}")
        else:
            logger.warning("CallbackManager not initialized, callback not stored")
        
        return jsonify({'success': True, 'task_id': task_id}), 200
        
    except Exception as e:
        logger.error(f"Error processing Suno callback: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/api/suno/status/<task_id>', methods=['GET'])
def check_suno_status(task_id):
    """
    Check if a Suno task has completed via callback.
    """
    try:
        if not callback_manager:
            return jsonify({'success': False, 'error': 'Callback manager not initialized'}), 500
        
        is_complete = callback_manager.is_complete(task_id)
        
        if is_complete:
            audio_url = callback_manager.get_audio_url(task_id)
            callback_data = callback_manager.get_callback(task_id)
            
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


@bp.route('/allsongs')
def all_songs():
    """
    Display all generated songs from all users, ordered by date (newest first).
    """
    try:
        # Get all profiles
        all_profiles = profile_manager.session_manager.list_profiles()
        
        # Collect all projects with songs
        songs = []
        for profile in all_profiles:
            for project_id in profile.project_ids:
                project = project_manager.get_project(project_id)
                if project and project.song_generated and project.song_file_path:
                    # Determine if song is disabled
                    is_disabled = project.song_file_path.endswith('.disabled')
                    
                    # Get title (first 50 chars of description or "Untitled")
                    title = project.description[:50] if project.description else "Untitled"
                    if len(project.description or "") > 50:
                        title += "..."
                    
                    songs.append({
                        'project_id': project.id,
                        'title': title,
                        'username': profile.name,
                        'song_path': project.song_file_path,
                        'image_path': project.image_file_path,
                        'created_at': project.created_at,
                        'is_disabled': is_disabled
                    })
        
        # Sort by creation date, newest first
        songs.sort(key=lambda s: s['created_at'], reverse=True)
        
        # Check if current user is admin
        is_admin = request.authorization and request.authorization.username == ADMIN_USERNAME
        
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
        # Check if user is admin
        if not request.authorization or request.authorization.username != ADMIN_USERNAME:
            return jsonify({'success': False, 'error': 'Unauthorized'}), 403
        
        # Load project
        project = project_manager.get_project(project_id)
        if not project:
            return jsonify({'success': False, 'error': 'Project not found'}), 404
        
        # Check if song exists
        if not project.song_file_path:
            return jsonify({'success': False, 'error': 'No song to disable'}), 400
        
        # Check if already disabled
        if project.song_file_path.endswith('.disabled'):
            return jsonify({'success': False, 'error': 'Song already disabled'}), 400
        
        # Append .disabled to filename
        new_path = project.song_file_path + '.disabled'
        
        # Update project
        project_manager.update_project(project_id, {
            'song_file_path': new_path
        })
        
        logger.info(f"Song disabled by {request.authorization.username}: {project_id}")
        
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
        # Check if user is admin
        if not request.authorization or request.authorization.username != ADMIN_USERNAME:
            return jsonify({'success': False, 'error': 'Unauthorized'}), 403
        
        # Load project
        project = project_manager.get_project(project_id)
        if not project:
            return jsonify({'success': False, 'error': 'Project not found'}), 404
        
        # Check if song exists
        if not project.song_file_path:
            return jsonify({'success': False, 'error': 'No song to enable'}), 400
        
        # Check if song is disabled
        if not project.song_file_path.endswith('.disabled'):
            return jsonify({'success': False, 'error': 'Song is not disabled'}), 400
        
        # Remove .disabled from filename
        new_path = project.song_file_path[:-9]  # Remove '.disabled' (9 characters)
        
        # Update project
        project_manager.update_project(project_id, {
            'song_file_path': new_path
        })
        
        logger.info(f"Song enabled by {request.authorization.username}: {project_id}")
        
        return jsonify({'success': True})
        
    except Exception as e:
        logger.error(f"Error enabling song: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500



# ============================================================
# Photo Transformation Routes (Isolated Photo Feature)
# ============================================================

@bp.route('/photo-transform')
def photo_transform_page():
    """Photo transformation page with webcam capture and style selection."""
    if not photo_transformer:
        return "Foto transformatie niet beschikbaar", 503

    profile_id = request.args.get('profile_id') or request.cookies.get('profile_id')
    if not profile_id:
        return render_template('photo_profile.html', config=config)

    profile = profile_manager.session_manager.load_profile(profile_id)
    if not profile:
        return render_template('photo_profile.html', error='Profiel niet gevonden', config=config)

    styles = photo_transformer.get_all_styles()
    return render_template('photo_transform.html', styles=styles, profile=profile, config=config)


@bp.route('/photo-transform', methods=['POST'])
def photo_transform_create_profile():
    """Create or load profile, then redirect to photo transform with profile_id."""
    name = request.form.get('name', '').strip()
    if not name:
        return render_template('photo_profile.html', error='Vul je naam in!', config=config)
    try:
        profile = profile_manager.create_or_get_profile(name)
        resp = make_response(redirect(url_for('main.photo_transform_page', profile_id=profile.id)))
        resp.set_cookie('profile_id', profile.id, max_age=60*60*24*30, samesite='Lax')
        return resp
    except ValueError as e:
        return render_template('photo_profile.html', error=str(e), config=config)


@bp.route('/api/photo/styles', methods=['GET'])
def get_photo_styles():
    """Return all available photo transformation styles as JSON."""
    if not photo_transformer:
        return jsonify({'success': False, 'error': 'Photo transformer not available'}), 503
    styles = photo_transformer.get_all_styles()
    return jsonify({'success': True, 'styles': styles})


@bp.route('/api/photo/transform', methods=['POST'])
def transform_photo_route():
    """
    Transform a photo using the specified style.
    Expects JSON: {image: base64_string, style: style_id, username: string}
    """
    if not photo_transformer:
        return jsonify({'success': False, 'error': 'Photo transformer not available'}), 503

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
            photo_transformer.transform_photo(image_b64, style_id, username)
        )
        loop.close()

        return jsonify(result)

    except Exception as e:
        logger.error(f"Photo transform route error: {e}", exc_info=True)
        return jsonify({'success': False, 'error': 'Er ging iets mis bij de transformatie'}), 500


@bp.route('/allphotos')
def all_photos():
    """Display all transformed photos grouped by user. Admin only."""
    if not request.authorization or request.authorization.username != ADMIN_USERNAME:
        return "Niet toegestaan", 403

    import os
    import re
    photos_dir = os.path.join('static', 'photos')
    users = []

    if os.path.isdir(photos_dir):
        for user_dir_name in sorted(os.listdir(photos_dir)):
            user_path = os.path.join(photos_dir, user_dir_name)
            if not os.path.isdir(user_path):
                continue

            # Extract display name from dir name (e.g. "EelkodeVos_df47" -> "EelkodeVos")
            display_name = re.sub(r'_[a-f0-9]{4}$', '', user_dir_name)

            # Find paired original/transformed by timestamp
            files = os.listdir(user_path)
            pairs = {}
            for f in sorted(files):
                if not f.endswith('.png'):
                    continue
                # e.g. original_dinosaur_1773327049.png or transformed_dinosaur_1773327049.png
                parts = f.rsplit('.', 1)[0]  # strip .png
                if parts.startswith('original_'):
                    key = parts[len('original_'):]  # "dinosaur_1773327049"
                    pairs.setdefault(key, {})['original'] = f'photos/{user_dir_name}/{f}'
                elif parts.startswith('transformed_'):
                    key = parts[len('transformed_'):]
                    pairs.setdefault(key, {})['transformed'] = f'photos/{user_dir_name}/{f}'

            photo_list = []
            for key in sorted(pairs.keys(), reverse=True):
                p = pairs[key]
                # Extract style from key (e.g. "dinosaur_1773327049" -> "dinosaur")
                style = key.rsplit('_', 1)[0] if '_' in key else key
                photo_list.append({
                    'style': style,
                    'original': p.get('original'),
                    'transformed': p.get('transformed'),
                })

            if photo_list:
                users.append({'name': display_name, 'photos': photo_list})

    return render_template('allphotos.html', users=users, config=config)
