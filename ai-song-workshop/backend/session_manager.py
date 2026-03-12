"""
Session management for AI Song Workshop Website.
Handles persistence of profiles and projects during workshop sessions.
"""
import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List
from backend.models import UserProfile, SongProject


class SessionManager:
    """
    Manages session data persistence using file-based storage.
    
    Attributes:
        storage_path: Directory path for session storage
        timeout_hours: Session timeout in hours
    """
    
    def __init__(self, storage_path: str, timeout_hours: int = 8):
        """
        Initialize SessionManager.
        
        Args:
            storage_path: Directory path for storing session data
            timeout_hours: Session timeout in hours (default: 8)
        """
        self.storage_path = Path(storage_path)
        self.timeout_hours = timeout_hours
        
        # Create storage directory if it doesn't exist
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.profiles_dir = self.storage_path / "profiles"
        self.projects_dir = self.storage_path / "projects"
        self.profiles_dir.mkdir(exist_ok=True)
        self.projects_dir.mkdir(exist_ok=True)
    
    def save_profile(self, profile: UserProfile) -> None:
        """
        Save a UserProfile to storage.
        
        Args:
            profile: UserProfile to save
        """
        profile_path = self.profiles_dir / f"{profile.id}.json"
        profile_data = {
            'id': profile.id,
            'name': profile.name,
            'created_at': profile.created_at.isoformat(),
            'project_ids': profile.project_ids
        }
        
        with open(profile_path, 'w', encoding='utf-8') as f:
            json.dump(profile_data, f, ensure_ascii=False, indent=2)

    
    def load_profile(self, profile_id: str) -> Optional[UserProfile]:
        """
        Load a UserProfile from storage.
        
        Args:
            profile_id: Profile ID to load
            
        Returns:
            UserProfile if found, None otherwise
        """
        profile_path = self.profiles_dir / f"{profile_id}.json"
        
        if not profile_path.exists():
            return None
        
        try:
            with open(profile_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            return UserProfile(
                id=data['id'],
                name=data['name'],
                created_at=datetime.fromisoformat(data['created_at']),
                project_ids=data['project_ids']
            )
        except (json.JSONDecodeError, KeyError) as e:
            print(f"Error loading profile {profile_id}: {e}")
            return None
    
    def find_profile_by_name(self, name: str) -> Optional[UserProfile]:
        """
        Find a profile by name (case-insensitive).
        
        Args:
            name: Profile name to search for
            
        Returns:
            UserProfile if found, None otherwise
        """
        name_lower = name.lower().strip()
        
        for profile_file in self.profiles_dir.glob("*.json"):
            profile = self.load_profile(profile_file.stem)
            if profile and profile.name.lower().strip() == name_lower:
                return profile
        
        return None

    
    def save_project(self, project: SongProject) -> None:
        """
        Save a SongProject to storage.
        
        Args:
            project: SongProject to save
        """
        project_path = self.projects_dir / f"{project.id}.json"
        project_data = {
            'id': project.id,
            'profile_id': project.profile_id,
            'created_at': project.created_at.isoformat(),
            'updated_at': project.updated_at.isoformat(),
            'description': project.description,
            'genre': project.genre,
            'lyrics': project.lyrics,
            'song_file_path': project.song_file_path,
            'image_file_path': project.image_file_path,
            'lyrics_generated': project.lyrics_generated,
            'song_generated': project.song_generated,
            'image_generated': project.image_generated
        }
        
        with open(project_path, 'w', encoding='utf-8') as f:
            json.dump(project_data, f, ensure_ascii=False, indent=2)
    
    def load_project(self, project_id: str) -> Optional[SongProject]:
        """
        Load a SongProject from storage.
        
        Args:
            project_id: Project ID to load
            
        Returns:
            SongProject if found, None otherwise
        """
        project_path = self.projects_dir / f"{project_id}.json"
        
        if not project_path.exists():
            return None
        
        try:
            with open(project_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            return SongProject(
                id=data['id'],
                profile_id=data['profile_id'],
                created_at=datetime.fromisoformat(data['created_at']),
                updated_at=datetime.fromisoformat(data['updated_at']),
                description=data['description'],
                genre=data['genre'],
                lyrics=data['lyrics'],
                song_file_path=data['song_file_path'],
                image_file_path=data['image_file_path'],
                lyrics_generated=data['lyrics_generated'],
                song_generated=data['song_generated'],
                image_generated=data['image_generated']
            )
        except (json.JSONDecodeError, KeyError) as e:
            print(f"Error loading project {project_id}: {e}")
            return None

    
    def list_profiles(self) -> List[UserProfile]:
        """
        List all profiles in the session.
        
        Returns:
            List of UserProfile objects
        """
        profiles = []
        for profile_file in self.profiles_dir.glob("*.json"):
            profile = self.load_profile(profile_file.stem)
            if profile:
                profiles.append(profile)
        return profiles
    
    def clear_session(self) -> None:
        """
        Clear all session data (admin function).
        Removes all profile and project files.
        """
        for profile_file in self.profiles_dir.glob("*.json"):
            profile_file.unlink()
        
        for project_file in self.projects_dir.glob("*.json"):
            project_file.unlink()
    
    def cleanup_expired_sessions(self) -> None:
        """
        Remove sessions older than timeout_hours.
        """
        cutoff_time = datetime.now() - timedelta(hours=self.timeout_hours)
        
        # Clean up expired profiles
        for profile_file in self.profiles_dir.glob("*.json"):
            profile = self.load_profile(profile_file.stem)
            if profile and profile.created_at < cutoff_time:
                profile_file.unlink()
                # Also remove associated projects
                for project_id in profile.project_ids:
                    project_path = self.projects_dir / f"{project_id}.json"
                    if project_path.exists():
                        project_path.unlink()
