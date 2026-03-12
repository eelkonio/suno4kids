"""
Error handling utilities for AI Song Workshop Website.
Provides Dutch error messages and retry logic.
"""
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


# Dutch error messages for child-friendly display
ERROR_MESSAGES_NL = {
    "api_unavailable": "De AI is even niet beschikbaar. Probeer het over een paar seconden opnieuw.",
    "content_rejected": "Laten we iets anders proberen. Klik op 'Opnieuw genereren'.",
    "network_error": "De internetverbinding is even weg. Controleer de verbinding en probeer opnieuw.",
    "timeout": "Dit duurt langer dan verwacht. Probeer het opnieuw.",
    "config_error": "Er is een probleem met de instellingen. Vraag de begeleider om hulp.",
    "profile_not_found": "Profiel niet gevonden.",
    "project_not_found": "Project niet gevonden.",
    "empty_name": "Naam mag niet leeg zijn.",
    "generation_failed": "Het genereren is mislukt. Probeer het opnieuw.",
    "invalid_input": "Ongeldige invoer. Controleer je gegevens.",
}


@dataclass
class RetryConfig:
    """Configuration for retry logic with exponential backoff."""
    max_attempts: int = 3
    initial_delay: float = 1.0  # seconds
    backoff_multiplier: float = 2.0
    max_delay: float = 10.0


class ErrorLogger:
    """
    Centralized error logging with timestamp and context.
    """
    
    def __init__(self, log_file: str = "logs/workshop.log"):
        """
        Initialize ErrorLogger.
        
        Args:
            log_file: Path to log file
        """
        self.logger = logging.getLogger('workshop')
        self.logger.setLevel(logging.INFO)
        
        # Create logs directory if it doesn't exist
        import os
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        
        # File handler
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.INFO)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.WARNING)
        
        # Formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)

    
    def log_error(self, error_type: str, message: str, context: Optional[dict] = None):
        """
        Log an error with timestamp and context.
        
        Args:
            error_type: Type of error (api_error, network_error, etc.)
            message: Error message
            context: Additional context dictionary
        """
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'error_type': error_type,
            'message': message,
            'context': context or {}
        }
        self.logger.error(f"{error_type}: {message} | Context: {context}")
    
    def log_info(self, message: str, context: Optional[dict] = None):
        """
        Log an info message.
        
        Args:
            message: Info message
            context: Additional context dictionary
        """
        self.logger.info(f"{message} | Context: {context}")
    
    def log_warning(self, message: str, context: Optional[dict] = None):
        """
        Log a warning message.
        
        Args:
            message: Warning message
            context: Additional context dictionary
        """
        self.logger.warning(f"{message} | Context: {context}")


class ContentSafetyLogger:
    """
    Separate logger for content safety events.
    """
    
    def __init__(self, log_file: str = "logs/content_safety.log"):
        """
        Initialize ContentSafetyLogger.
        
        Args:
            log_file: Path to content safety log file
        """
        self.logger = logging.getLogger('content_safety')
        self.logger.setLevel(logging.INFO)
        
        # Create logs directory if it doesn't exist
        import os
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        
        # File handler
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.INFO)
        
        # Formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(formatter)
        
        self.logger.addHandler(file_handler)
    
    def log_rejection(self, content_type: str, reason: str, sample: str):
        """
        Log content rejection event.
        
        Args:
            content_type: Type of content (lyrics, image)
            reason: Rejection reason
            sample: Sample of rejected content
        """
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'content_type': content_type,
            'reason': reason,
            'sample': sample[:100]  # Limit sample length
        }
        self.logger.warning(f"Content rejected: {log_entry}")


def get_dutch_error_message(error_key: str) -> str:
    """
    Get Dutch error message by key.
    
    Args:
        error_key: Error message key
        
    Returns:
        Dutch error message
    """
    return ERROR_MESSAGES_NL.get(error_key, "Er is een fout opgetreden. Probeer het opnieuw.")
