"""
Callback manager for handling Suno API callbacks.
Stores callback data and provides status checking.
"""
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class CallbackManager:
    """
    Manages Suno API callbacks and task status.
    
    Stores callback data in memory and optionally persists to disk.
    """
    
    def __init__(self, storage_path: str = "data/callbacks"):
        """
        Initialize CallbackManager.
        
        Args:
            storage_path: Directory for storing callback data
        """
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.callbacks = {}  # In-memory storage: {task_id: callback_data}
        
        logger.info(f"CallbackManager initialized with storage: {storage_path}")
    
    def store_callback(self, task_id: str, callback_data: Dict) -> None:
        """
        Store callback data for a task.
        
        Args:
            task_id: Suno task ID
            callback_data: Full callback payload from Suno
        """
        # Add timestamp
        callback_data['received_at'] = datetime.now().isoformat()
        
        # Store in memory
        self.callbacks[task_id] = callback_data
        
        # Persist to disk
        file_path = self.storage_path / f"{task_id}.json"
        with open(file_path, 'w') as f:
            json.dump(callback_data, f, indent=2)
        
        logger.info(f"Stored callback for task {task_id}")
        logger.info(f"Callback data: {json.dumps(callback_data, indent=2)}")
    
    def get_callback(self, task_id: str) -> Optional[Dict]:
        """
        Retrieve callback data for a task.
        
        Args:
            task_id: Suno task ID
            
        Returns:
            Callback data if available, None otherwise
        """
        # Check memory first
        if task_id in self.callbacks:
            return self.callbacks[task_id]
        
        # Check disk
        file_path = self.storage_path / f"{task_id}.json"
        if file_path.exists():
            with open(file_path, 'r') as f:
                data = json.load(f)
                self.callbacks[task_id] = data  # Cache in memory
                return data
        
        return None
    
    def is_complete(self, task_id: str) -> bool:
        """
        Check if a task has completed (callback received).
        
        Args:
            task_id: Suno task ID
            
        Returns:
            True if callback received, False otherwise
        """
        return task_id in self.callbacks or (self.storage_path / f"{task_id}.json").exists()
    
    def get_audio_url(self, task_id: str) -> Optional[str]:
        """
        Extract audio URL from callback data.
        
        Args:
            task_id: Suno task ID
            
        Returns:
            Audio URL if available, None otherwise
        """
        callback_data = self.get_callback(task_id)
        if not callback_data:
            return None
        
        # Try different possible structures
        # Structure 1: data[0].audio_url
        if 'data' in callback_data and isinstance(callback_data['data'], list):
            if len(callback_data['data']) > 0:
                return callback_data['data'][0].get('audio_url')
        
        # Structure 2: audio_url directly
        if 'audio_url' in callback_data:
            return callback_data['audio_url']
        
        # Structure 3: response.data[0].audio_url
        if 'response' in callback_data and 'data' in callback_data['response']:
            tracks = callback_data['response']['data']
            if isinstance(tracks, list) and len(tracks) > 0:
                return tracks[0].get('audio_url')
        
        logger.warning(f"Could not extract audio URL from callback for task {task_id}")
        logger.warning(f"Callback keys: {list(callback_data.keys())}")
        return None
    
    def clear_callback(self, task_id: str) -> None:
        """
        Remove callback data for a task.
        
        Args:
            task_id: Suno task ID
        """
        # Remove from memory
        if task_id in self.callbacks:
            del self.callbacks[task_id]
        
        # Remove from disk
        file_path = self.storage_path / f"{task_id}.json"
        if file_path.exists():
            file_path.unlink()
        
        logger.info(f"Cleared callback for task {task_id}")
