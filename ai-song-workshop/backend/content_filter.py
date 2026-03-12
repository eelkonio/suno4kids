"""
Content filtering for AI Song Workshop Website.
Ensures all AI-generated content is age-appropriate for children aged 9-12.
"""
import logging
from datetime import datetime
from typing import Tuple, Optional, List


class ContentFilter:
    """
    Validates AI-generated content for age-appropriateness.
    
    Filters profanity, violence, and adult themes from lyrics and images.
    """
    
    def __init__(self):
        """Initialize ContentFilter with Dutch profanity list and theme patterns."""
        self.profanity_list = self._load_dutch_profanity()
        self.inappropriate_themes = [
            "geweld", "violence", "drugs", "alcohol", "dood", "death",
            "bloed", "blood", "moord", "murder", "seks", "sex"
        ]
        
        # Set up logging
        self.logger = logging.getLogger('content_filter')
    
    def _load_dutch_profanity(self) -> List[str]:
        """
        Load Dutch profanity word list.
        
        Returns:
            List of profanity words (lowercase)
        """
        # Basic Dutch profanity list (expandable)
        return [
            "kut", "lul", "klote", "shit", "fuck", "hoer",
            "kanker", "tering", "tyfus", "godverdomme"
        ]
    
    def _check_profanity(self, text: str) -> bool:
        """
        Check if text contains profanity.
        
        Args:
            text: Text to check
            
        Returns:
            True if profanity found, False otherwise
        """
        text_lower = text.lower()
        for word in self.profanity_list:
            if word in text_lower:
                return True
        return False

    
    def _check_themes(self, text: str) -> bool:
        """
        Check if text contains inappropriate themes.
        
        Args:
            text: Text to check
            
        Returns:
            True if inappropriate themes found, False otherwise
        """
        text_lower = text.lower()
        for theme in self.inappropriate_themes:
            if theme in text_lower:
                return True
        return False
    
    def validate_lyrics(self, lyrics: str) -> Tuple[bool, Optional[str]]:
        """
        Validate lyrics for age-appropriateness.
        
        Args:
            lyrics: Lyrics text to validate
            
        Returns:
            Tuple of (is_valid, rejection_reason)
            - is_valid: True if content is appropriate
            - rejection_reason: String describing why content was rejected, or None
        """
        if not lyrics or not lyrics.strip():
            return False, "Tekst is leeg"
        
        # Check for profanity
        if self._check_profanity(lyrics):
            reason = "Ongepaste taal gedetecteerd"
            self._log_rejection("lyrics", reason, lyrics[:100])
            return False, reason
        
        # Check for inappropriate themes
        if self._check_themes(lyrics):
            reason = "Ongepast thema gedetecteerd"
            self._log_rejection("lyrics", reason, lyrics[:100])
            return False, reason
        
        return True, None
    
    def validate_image(self, image_path: str) -> Tuple[bool, Optional[str]]:
        """
        Validate image for age-appropriateness.
        Currently a placeholder - could integrate with Google Safe Search API.
        
        Args:
            image_path: Path to image file
            
        Returns:
            Tuple of (is_valid, rejection_reason)
        """
        # Placeholder implementation
        # In production, could use Google Safe Search API or similar
        return True, None

    
    def _log_rejection(self, content_type: str, reason: str, sample: str) -> None:
        """
        Log content filtering event.
        
        Args:
            content_type: Type of content (lyrics, image)
            reason: Rejection reason
            sample: Sample of rejected content (sanitized)
        """
        timestamp = datetime.now().isoformat()
        log_entry = {
            'timestamp': timestamp,
            'content_type': content_type,
            'reason': reason,
            'sample': sample
        }
        self.logger.warning(f"Content rejected: {log_entry}")
