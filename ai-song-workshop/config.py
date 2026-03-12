"""
Configuration module for AI Song Workshop Website.
Loads configuration from environment variables with validation.
"""
import os
from dataclasses import dataclass
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


@dataclass
class HeaderConfig:
    """Configuration for header branding."""
    logo_path: str
    class_name: str


@dataclass
class APIConfiguration:
    """Configuration for external API integrations."""
    anthropic_api_key: str
    suno_api_key: str
    google_api_key: Optional[str]
    header: HeaderConfig


@dataclass
class SessionConfig:
    """Configuration for session management."""
    timeout_hours: int
    storage_path: str


@dataclass
class AppConfig:
    """Main application configuration."""
    api: APIConfiguration
    session: SessionConfig
    flask_env: str
    flask_debug: bool
    host: str
    port: int
    callback_url: Optional[str] = None


def load_config() -> AppConfig:
    """
    Load configuration from environment variables.
    Validates required keys and fails fast if missing.
    
    Returns:
        AppConfig: Complete application configuration
        
    Raises:
        ValueError: If required configuration is missing
    """
    # Required API keys
    anthropic_key = os.getenv('ANTHROPIC_API_KEY')
    suno_key = os.getenv('SUNO_API_KEY')
    
    if not anthropic_key:
        raise ValueError("ANTHROPIC_API_KEY is required but not set")
    if not suno_key:
        raise ValueError("SUNO_API_KEY is required but not set")
    
    # Optional Google API key
    google_key = os.getenv('GOOGLE_API_KEY')
    
    # Header configuration
    logo_path = os.getenv('LOGO_PATH', 'static/logo.png')
    class_name = os.getenv('CLASS_NAME', 'Groep 6, 7 en 8')
    
    # Session configuration
    timeout_hours = int(os.getenv('SESSION_TIMEOUT_HOURS', '8'))
    storage_path = os.getenv('SESSION_STORAGE_PATH', '/tmp/workshop_sessions')
    
    # Server configuration
    flask_env = os.getenv('FLASK_ENV', 'development')
    flask_debug = os.getenv('FLASK_DEBUG', 'True').lower() == 'true'
    host = os.getenv('HOST', '0.0.0.0')
    port = int(os.getenv('PORT', '80'))
    
    # Callback URL for Suno API
    callback_url = os.getenv('CALLBACK_URL')
    
    # Build configuration objects
    header_config = HeaderConfig(
        logo_path=logo_path,
        class_name=class_name
    )
    
    api_config = APIConfiguration(
        anthropic_api_key=anthropic_key,
        suno_api_key=suno_key,
        google_api_key=google_key,
        header=header_config
    )
    
    session_config = SessionConfig(
        timeout_hours=timeout_hours,
        storage_path=storage_path
    )
    
    return AppConfig(
        api=api_config,
        session=session_config,
        flask_env=flask_env,
        flask_debug=flask_debug,
        host=host,
        port=port,
        callback_url=callback_url
    )


# Global configuration instance
try:
    config = load_config()
except ValueError as e:
    print(f"Configuration Error: {e}")
    print("Please set required environment variables in .env file")
    raise
