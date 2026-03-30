"""
Per-school configuration manager for multi-tenant AI Song Workshop.
Manages per-school config files at data/schools/{username}/config.json.
Each school has its own class name, logo, project limit, and API keys.
"""
import json
import logging
import os
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class SchoolConfig:
    """Per-school configuration."""
    class_name: str = ""
    logo_path: str = ""
    max_projects_per_profile: int = 10
    anthropic_api_key: Optional[str] = None
    suno_api_key: Optional[str] = None
    google_api_key: Optional[str] = None


class SchoolConfigManager:
    """
    Manages per-school config files at data/schools/{username}/config.json.
    API keys are stored in plaintext in the config file (file system security).
    """

    VALID_SERVICES = ('anthropic', 'suno', 'google')

    def __init__(self, base_path: str = "data/schools"):
        self.base_path = Path(base_path)

    def _config_path(self, username: str) -> Path:
        return self.base_path / username / "config.json"

    def get_config(self, username: str) -> SchoolConfig:
        """Load school config from disk. Returns defaults if file missing or invalid."""
        path = self._config_path(username)
        if not path.exists():
            return self._default_config()

        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if not isinstance(data, dict):
                raise ValueError("Config is not a JSON object")
            return SchoolConfig(
                class_name=data.get('class_name', self._default_class_name()),
                logo_path=data.get('logo_path', self._default_logo_path()),
                max_projects_per_profile=int(data.get('max_projects_per_profile', self._default_max_projects())),
                anthropic_api_key=data.get('anthropic_api_key') or None,
                suno_api_key=data.get('suno_api_key') or None,
                google_api_key=data.get('google_api_key') or None,
            )
        except (json.JSONDecodeError, ValueError, OSError) as e:
            logger.error(f"Failed to load config for school '{username}': {e}")
            return self._default_config()

    def save_config(self, username: str, config: SchoolConfig) -> None:
        """Persist school config to disk."""
        path = self._config_path(username)
        path.parent.mkdir(parents=True, exist_ok=True)
        data = asdict(config)
        # Normalize empty-string API keys to None for clean JSON
        for key in ('anthropic_api_key', 'suno_api_key', 'google_api_key'):
            if not data.get(key):
                data[key] = None
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def create_default_config(self, username: str) -> SchoolConfig:
        """Create config with defaults from env vars and save to disk."""
        config = self._default_config()
        self.save_config(username, config)
        return config

    def set_api_key(self, username: str, service: str, key: str) -> None:
        """Set a single API key. service is 'anthropic', 'suno', or 'google'."""
        self._validate_service(service)
        config = self.get_config(username)
        setattr(config, f'{service}_api_key', key if key else None)
        self.save_config(username, config)

    def clear_api_key(self, username: str, service: str) -> None:
        """Clear (remove) an API key for a service."""
        self._validate_service(service)
        config = self.get_config(username)
        setattr(config, f'{service}_api_key', None)
        self.save_config(username, config)

    def get_api_key_status(self, username: str) -> dict:
        """Return {anthropic: 'Set'|'Not set', suno: 'Set'|'Not set', google: 'Set'|'Not set'}."""
        config = self.get_config(username)
        return {
            'anthropic': 'Set' if config.anthropic_api_key else 'Not set',
            'suno': 'Set' if config.suno_api_key else 'Not set',
            'google': 'Set' if config.google_api_key else 'Not set',
        }

    def get_api_key_hint(self, username: str, service: str) -> Optional[str]:
        """Return last 4 chars of key if set, None otherwise."""
        self._validate_service(service)
        config = self.get_config(username)
        key = getattr(config, f'{service}_api_key', None)
        if not key:
            return None
        if len(key) >= 4:
            return key[-4:]
        return key

    # --- Internal helpers ---

    def _validate_service(self, service: str) -> None:
        """Raise ValueError if service name is invalid."""
        if service not in self.VALID_SERVICES:
            raise ValueError(f"Invalid service '{service}'. Must be one of: {', '.join(self.VALID_SERVICES)}")

    @staticmethod
    def _default_class_name() -> str:
        return os.getenv('CLASS_NAME', 'Groep 5 en 6')

    @staticmethod
    def _default_logo_path() -> str:
        return os.getenv('LOGO_PATH', 'static/logo.png')

    @staticmethod
    def _default_max_projects() -> int:
        return int(os.getenv('MAX_PROJECTS_PER_PROFILE', '10'))

    def _default_config(self) -> SchoolConfig:
        """Build a SchoolConfig with env var defaults."""
        return SchoolConfig(
            class_name=self._default_class_name(),
            logo_path=self._default_logo_path(),
            max_projects_per_profile=self._default_max_projects(),
        )
