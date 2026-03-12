"""
Data models for AI Song Workshop Website.
"""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Optional
import uuid


class MusicGenre(Enum):
    """Predefined music genres appropriate for children aged 9-12."""
    POP = "pop"
    ROCK = "rock"
    ELECTRONIC = "electronic"
    HIPHOP = "hip-hop"
    FOLK = "folk"
    JAZZ = "jazz"
    CLASSICAL = "classical"
    
    @classmethod
    def get_dutch_names(cls):
        """Return Dutch display names for genres."""
        return {
            cls.POP: "Pop",
            cls.ROCK: "Rock",
            cls.ELECTRONIC: "Elektronisch",
            cls.HIPHOP: "Hip-Hop",
            cls.FOLK: "Folk",
            cls.JAZZ: "Jazz",
            cls.CLASSICAL: "Klassiek"
        }


@dataclass
class UserProfile:
    """
    User profile containing a child's name and associated song projects.
    
    Attributes:
        id: Unique identifier (UUID)
        name: Child's name
        created_at: Profile creation timestamp
        project_ids: List of associated SongProject IDs
    """
    id: str
    name: str
    created_at: datetime
    project_ids: List[str] = field(default_factory=list)
    
    @staticmethod
    def create(name: str) -> 'UserProfile':
        """Create a new UserProfile with generated ID."""
        return UserProfile(
            id=str(uuid.uuid4()),
            name=name,
            created_at=datetime.now(),
            project_ids=[]
        )



@dataclass
class SongProject:
    """
    Container for a song project with description, lyrics, audio, and artwork.
    
    Attributes:
        id: Unique identifier (UUID)
        profile_id: Reference to UserProfile
        created_at: Project creation timestamp
        updated_at: Last update timestamp
        description: User-provided song description
        genre: Selected music genre
        lyrics: Generated/edited lyrics
        song_file_path: Path to generated audio file
        image_file_path: Path to generated artwork
        lyrics_generated: Flag indicating lyrics have been generated
        song_generated: Flag indicating song has been generated
        image_generated: Flag indicating image has been generated
    """
    id: str
    profile_id: str
    created_at: datetime
    updated_at: datetime
    description: str = ""
    genre: Optional[str] = None
    lyrics: Optional[str] = None
    song_file_path: Optional[str] = None
    image_file_path: Optional[str] = None
    lyrics_generated: bool = False
    song_generated: bool = False
    image_generated: bool = False
    
    @staticmethod
    def create(profile_id: str) -> 'SongProject':
        """Create a new empty SongProject with generated ID."""
        now = datetime.now()
        return SongProject(
            id=str(uuid.uuid4()),
            profile_id=profile_id,
            created_at=now,
            updated_at=now
        )
    
    def update(self, **kwargs):
        """Update project fields and refresh updated_at timestamp."""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        self.updated_at = datetime.now()
