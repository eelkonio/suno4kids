"""
Project management for AI Song Workshop Website.
Handles song project creation and management within user profiles.
"""
from typing import List, Optional
from backend.models import SongProject, UserProfile
from backend.session_manager import SessionManager


class ProjectManager:
    """
    Manages song projects within user profiles.
    
    Attributes:
        session_manager: SessionManager instance for persistence
    """
    
    def __init__(self, session_manager: SessionManager):
        """
        Initialize ProjectManager.
        
        Args:
            session_manager: SessionManager for project persistence
        """
        self.session_manager = session_manager
    
    def create_project(self, profile_id: str, max_projects: int = 10) -> SongProject:
        """
        Create new empty song project.
        
        Args:
            profile_id: ID of the profile to create project for
            max_projects: Maximum number of projects allowed per profile.
                         Caller should pass school_config.max_projects_per_profile.
            
        Returns:
            New SongProject with empty fields
            
        Raises:
            ValueError: If profile not found or project limit reached
        """
        # Verify profile exists
        profile = self.session_manager.load_profile(profile_id)
        if not profile:
            raise ValueError(f"Profiel niet gevonden: {profile_id}")
        
        # Check project limit
        if len(profile.project_ids) >= max_projects:
            raise ValueError(f"Je hebt het maximum van {max_projects} projecten bereikt. Verwijder eerst een oud project.")
        
        # Create new project
        project = SongProject.create(profile_id)
        self.session_manager.save_project(project)
        
        # Add project ID to profile
        profile.project_ids.append(project.id)
        self.session_manager.save_profile(profile)
        
        return project

    
    def get_project(self, project_id: str) -> Optional[SongProject]:
        """
        Retrieve specific project by ID.
        
        Args:
            project_id: Project ID to retrieve
            
        Returns:
            SongProject if found, None otherwise
        """
        return self.session_manager.load_project(project_id)
    
    def list_projects(self, profile_id: str) -> List[SongProject]:
        """
        Get all projects for a profile, ordered by creation time (newest first).
        
        Args:
            profile_id: Profile ID to get projects for
            
        Returns:
            List of SongProject objects
        """
        profile = self.session_manager.load_profile(profile_id)
        if not profile:
            return []
        
        projects = []
        for project_id in profile.project_ids:
            project = self.session_manager.load_project(project_id)
            if project:
                projects.append(project)
        
        # Sort by creation time, newest first
        projects.sort(key=lambda p: p.created_at, reverse=True)
        return projects
    
    def update_project(self, project_id: str, updates: dict) -> Optional[SongProject]:
        """
        Update project fields atomically.
        
        Args:
            project_id: Project ID to update
            updates: Dictionary of field updates
            
        Returns:
            Updated SongProject if found, None otherwise
        """
        project = self.session_manager.load_project(project_id)
        if not project:
            return None
        
        # Update fields
        project.update(**updates)
        
        # Save updated project
        self.session_manager.save_project(project)
        return project
