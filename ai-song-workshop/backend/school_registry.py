"""
School Registry for multi-tenant AI Song Workshop.
Manages school credentials and global settings, stored in a JSON file.
Replaces the AUTH_USERS environment variable for credential management.
"""
import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

from werkzeug.security import generate_password_hash, check_password_hash

logger = logging.getLogger(__name__)


class SchoolRegistry:
    """
    Manages school credentials stored in data/schools.json.
    
    Registry JSON structure:
    {
        "admin_username": "eelko",
        "global_settings": {
            "default_max_projects_per_profile": 10
        },
        "schools": {
            "suno4kids": {
                "password_hash": "...",
                "created_at": "2025-01-15T10:30:00"
            }
        }
    }
    """

    def __init__(self, registry_path: str = "data/schools.json"):
        self.registry_path = Path(registry_path)
        # Create data directory if missing
        self.registry_path.parent.mkdir(parents=True, exist_ok=True)
        self._data: Optional[dict] = None

    def load(self) -> dict:
        """Load registry from disk. Returns dict with admin_username, schools, global_settings."""
        if not self.registry_path.exists():
            return self._empty_registry()

        try:
            with open(self.registry_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            # Validate structure
            if not isinstance(data, dict) or 'schools' not in data:
                raise ValueError("Invalid registry structure")
            self._data = data
            return data
        except (json.JSONDecodeError, ValueError, OSError) as e:
            logger.error(f"Failed to load school registry from {self.registry_path}: {e}")
            return self._fallback_from_env()

    def save(self, data: Optional[dict] = None) -> None:
        """Persist registry to disk."""
        if data is not None:
            self._data = data
        if self._data is None:
            raise ValueError("No data to save")
        with open(self.registry_path, 'w', encoding='utf-8') as f:
            json.dump(self._data, f, ensure_ascii=False, indent=2)

    def initialize_from_env(self) -> None:
        """Bootstrap registry from AUTH_USERS and ADMIN_USERNAME env vars on first run."""
        if self.registry_path.exists():
            self.load()
            return

        admin_username = os.getenv('ADMIN_USERNAME', 'admin')
        auth_users_str = os.getenv('AUTH_USERS', '')
        max_projects = int(os.getenv('MAX_PROJECTS_PER_PROFILE', '10'))

        schools = {}
        now = datetime.now().isoformat()

        for pair in auth_users_str.split(','):
            pair = pair.strip()
            if ':' in pair:
                username, password = pair.split(':', 1)
                username = username.strip()
                password = password.strip()
                if username:
                    schools[username] = {
                        'password_hash': generate_password_hash(password),
                        'created_at': now,
                    }

        self._data = {
            'admin_username': admin_username,
            'global_settings': {
                'default_max_projects_per_profile': max_projects,
            },
            'schools': schools,
        }
        self.save()

    def validate_credentials(self, username: str, password: str) -> bool:
        """Check username/password against stored hashed passwords."""
        data = self._ensure_loaded()
        school = data['schools'].get(username)
        if not school:
            return False
        return check_password_hash(school['password_hash'], password)

    def add_school(self, username: str, password: str) -> None:
        """Add a new school with hashed password. Raises ValueError if username exists."""
        data = self._ensure_loaded()
        if username in data['schools']:
            raise ValueError(f"School '{username}' already exists")
        data['schools'][username] = {
            'password_hash': generate_password_hash(password),
            'created_at': datetime.now().isoformat(),
        }
        self.save()

    def update_password(self, username: str, new_password: str) -> None:
        """Update a school's hashed password."""
        data = self._ensure_loaded()
        if username not in data['schools']:
            raise ValueError(f"School '{username}' not found")
        data['schools'][username]['password_hash'] = generate_password_hash(new_password)
        self.save()

    def delete_school(self, username: str) -> None:
        """Remove a school. Raises ValueError if username is admin."""
        data = self._ensure_loaded()
        if username == data.get('admin_username'):
            raise ValueError("Cannot delete the admin school")
        if username not in data['schools']:
            raise ValueError(f"School '{username}' not found")
        del data['schools'][username]
        self.save()

    def list_schools(self) -> list:
        """Return list of {username, created_at} for all schools."""
        data = self._ensure_loaded()
        return [
            {'username': username, 'created_at': info.get('created_at', '')}
            for username, info in data['schools'].items()
        ]

    def get_admin_username(self) -> str:
        """Return the admin username."""
        data = self._ensure_loaded()
        return data.get('admin_username', 'admin')

    def get_global_settings(self) -> dict:
        """Return global settings (default_max_projects_per_profile)."""
        data = self._ensure_loaded()
        return data.get('global_settings', {'default_max_projects_per_profile': 10})

    def update_global_settings(self, settings: dict) -> None:
        """Update global settings."""
        data = self._ensure_loaded()
        data['global_settings'] = settings
        self.save()

    # --- Internal helpers ---

    def _ensure_loaded(self) -> dict:
        """Ensure registry data is loaded, loading from disk if needed."""
        if self._data is None:
            self._data = self.load()
        return self._data

    def _empty_registry(self) -> dict:
        """Return an empty registry structure."""
        return {
            'admin_username': os.getenv('ADMIN_USERNAME', 'admin'),
            'global_settings': {
                'default_max_projects_per_profile': int(os.getenv('MAX_PROJECTS_PER_PROFILE', '10')),
            },
            'schools': {},
        }

    def _fallback_from_env(self) -> dict:
        """Fall back to AUTH_USERS env var when registry file is corrupted/unreadable."""
        logger.warning("Falling back to AUTH_USERS environment variable for credentials")
        admin_username = os.getenv('ADMIN_USERNAME', 'admin')
        auth_users_str = os.getenv('AUTH_USERS', '')
        max_projects = int(os.getenv('MAX_PROJECTS_PER_PROFILE', '10'))

        schools = {}
        now = datetime.now().isoformat()

        for pair in auth_users_str.split(','):
            pair = pair.strip()
            if ':' in pair:
                username, password = pair.split(':', 1)
                username = username.strip()
                password = password.strip()
                if username:
                    schools[username] = {
                        'password_hash': generate_password_hash(password),
                        'created_at': now,
                    }

        self._data = {
            'admin_username': admin_username,
            'global_settings': {
                'default_max_projects_per_profile': max_projects,
            },
            'schools': schools,
        }
        return self._data
