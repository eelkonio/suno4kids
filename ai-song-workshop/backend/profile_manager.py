"""
Profile management for AI Song Workshop Website.
Handles user profile creation and selection.
"""
from typing import List, Optional
from backend.models import UserProfile
from backend.session_manager import SessionManager


class ProfileManager:
    """
    Manages user profile creation and retrieval.
    
    Attributes:
        session_manager: SessionManager instance for persistence
    """
    
    def __init__(self, session_manager: SessionManager):
        """
        Initialize ProfileManager.
        
        Args:
            session_manager: SessionManager for profile persistence
        """
        self.session_manager = session_manager
    
    def validate_name(self, name: str) -> bool:
        """
        Validate that name is non-empty.
        
        Args:
            name: Name to validate
            
        Returns:
            True if name is valid, False otherwise
        """
        return bool(name and name.strip())
    
    def create_or_get_profile(self, name: str) -> UserProfile:
        """
        Create new profile or retrieve existing one by name.
        Names are matched case-insensitively.
        
        Args:
            name: Profile name
            
        Returns:
            UserProfile (new or existing)
            
        Raises:
            ValueError: If name is empty or invalid
        """
        if not self.validate_name(name):
            raise ValueError("Naam mag niet leeg zijn")
        
        # Check if profile already exists (case-insensitive)
        existing_profile = self.session_manager.find_profile_by_name(name)
        if existing_profile:
            return existing_profile
        
        # Create new profile
        profile = UserProfile.create(name.strip())
        self.session_manager.save_profile(profile)
        return profile
    
    def list_profiles(self) -> List[UserProfile]:
        """
        Return all profiles in current session.
        
        Returns:
            List of UserProfile objects
        """
        return self.session_manager.list_profiles()
