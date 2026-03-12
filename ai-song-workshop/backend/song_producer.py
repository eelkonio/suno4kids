"""
Song production using Suno.ai API for AI Song Workshop Website.
"""
import asyncio
import aiohttp
import hashlib
import json
import logging
import re
import time
from pathlib import Path
from typing import Optional, Dict

# Configure logging
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/workshop.log'),
        logging.StreamHandler()
    ]
)


class SongProducer:
    """
    Generates complete songs using Suno.ai API.
    
    Attributes:
        api_key: Suno.ai API key
        base_url: Suno.ai API base URL
        storage_path: Path for storing audio files
    """
    
    def __init__(self, api_key: str, storage_path: str = "static/audio", callback_url: str = None, callback_manager=None):
        """
        Initialize SongProducer.
        
        Args:
            api_key: Suno.ai API key
            storage_path: Directory path for audio storage
            callback_url: URL for Suno to send callbacks (optional)
            callback_manager: CallbackManager instance for handling callbacks (optional)
        """
        self.api_key = api_key
        self.base_url = "https://api.sunoapi.org/api/v1"
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.callback_url = callback_url
        self.callback_manager = callback_manager
        
        logger.info(f"SongProducer initialized with callback URL: {callback_url}")
    
    async def generate_song(self, lyrics: str, genre: str, username: Optional[str] = None) -> str:
        """
        Generate song and return file path.
        
        Args:
            lyrics: Song lyrics
            genre: Music genre
            username: Username for directory organization (optional)
            
        Returns:
            Relative path to generated audio file
            
        Raises:
            Exception: If generation fails
        """
        # Get user-specific directory if username provided
        target_dir = self._get_user_directory(username) if username else self.storage_path
        
        # Submit generation request
        task_id = await self._submit_generation(lyrics, genre)
        
        # Poll for completion
        audio_url = await self._poll_until_complete(task_id)
        
        # Download and save audio
        file_path = await self._download_audio(audio_url, task_id, target_dir)
        
        return file_path

    
    def _sanitize_username(self, username: str) -> str:
        """
        Sanitize username for use in directory names.
        Removes all characters except alphanumeric, hyphens, and underscores.
        
        Args:
            username: Original username
            
        Returns:
            Sanitized username with only safe characters
        """
        # Remove all characters except alphanumeric, hyphens, and underscores
        sanitized = re.sub(r'[^a-zA-Z0-9_-]', '', username)
        # Ensure it's not empty
        return sanitized if sanitized else 'user'
    
    def _get_username_hash(self, username: str) -> str:
        """
        Generate a 4-character hash code from the full username.
        
        Args:
            username: Full original username (not sanitized)
            
        Returns:
            4-character hash code
        """
        # Create hash from full username
        hash_obj = hashlib.md5(username.encode('utf-8'))
        # Take first 4 characters of hex digest
        return hash_obj.hexdigest()[:4]
    
    def _get_user_directory(self, username: str) -> Path:
        """
        Get or create user-specific directory for audio files.
        
        Args:
            username: Username to create directory for
            
        Returns:
            Path to user-specific directory
        """
        # Sanitize username and add hash code
        sanitized = self._sanitize_username(username)
        hash_code = self._get_username_hash(username)
        dir_name = f"{sanitized}_{hash_code}"
        
        # Create full path
        user_dir = self.storage_path / dir_name
        user_dir.mkdir(parents=True, exist_ok=True)
        
        return user_dir
    
    async def _submit_generation(self, lyrics: str, genre: str) -> str:
        """
        Submit song generation request to Suno.ai API.
        
        Args:
            lyrics: Song lyrics
            genre: Music genre
            
        Returns:
            Task ID for tracking generation
        """
        logger.info(f"Submitting song generation request to Suno API (genre: {genre})")
        
        async with aiohttp.ClientSession() as session:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "prompt": lyrics,
                "customMode": True,
                "style": genre,
                "title": "Workshop Song",
                "instrumental": False,
                "model": "V5",
                "callBackUrl": self.callback_url or "https://example.com/callback"
            }
            
            try:
                async with session.post(
                    f"{self.base_url}/generate",
                    headers=headers,
                    json=payload
                ) as response:
                    response_text = await response.text()
                    
                    if response.status != 200:
                        logger.error(f"Suno API returned status {response.status}")
                        logger.error(f"Response body: {response_text}")
                        raise Exception(f"Suno.ai API fout: {response.status} - {response_text}")
                    
                    data = json.loads(response_text)
                    logger.info(f"Suno API response: {json.dumps(data, indent=2)}")
                    
                    if data.get('code') != 200:
                        logger.error(f"Suno API returned error code: {data.get('code')}")
                        logger.error(f"Error message: {data.get('msg')}")
                        raise Exception(f"Suno.ai generatie fout: {data.get('msg')}")
                    
                    task_id = data['data']['taskId']
                    logger.info(f"Song generation submitted successfully, task ID: {task_id}")
                    return task_id
                    
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse Suno API response as JSON: {e}")
                logger.error(f"Response text: {response_text}")
                raise Exception(f"Suno.ai API response parse error: {str(e)}")
            except Exception as e:
                logger.error(f"Suno API submission failed: {str(e)}", exc_info=True)
                raise
    
    async def poll_status(self, task_id: str) -> Dict:
        """
        Check generation status.
        
        Args:
            task_id: Task ID to check
            
        Returns:
            Status dictionary with 'status' and optional audio data
        """
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Authorization": f"Bearer {self.api_key}"
                }
                
                async with session.get(
                    f"{self.base_url}/generate/record-info?taskId={task_id}",
                    headers=headers
                ) as response:
                    response_text = await response.text()
                    
                    if response.status != 200:
                        logger.error(f"Suno status check returned status {response.status}")
                        logger.error(f"Response body: {response_text}")
                        raise Exception(f"Status check fout: {response.status} - {response_text}")
                    
                    result = json.loads(response_text)
                    return result.get('data', {})
                    
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Suno status response as JSON: {e}")
            logger.error(f"Response text: {response_text}")
            raise Exception(f"Suno.ai status response parse error: {str(e)}")
        except Exception as e:
            logger.error(f"Suno status check failed: {str(e)}", exc_info=True)
            raise

    
    async def _poll_until_complete(self, task_id: str, timeout: int = 600) -> str:
        """
        Poll status until generation completes.
        Uses callback if available, otherwise polls API.
        
        Args:
            task_id: Task ID to poll
            timeout: Maximum wait time in seconds
            
        Returns:
            URL to generated audio file
        """
        start_time = time.time()
        logger.info(f"Starting to poll for task completion: {task_id}")
        
        # If callback manager is available, check for callback first
        if self.callback_manager:
            logger.info("Callback manager available, will check for callbacks")
        
        while True:
            # Check if callback received
            if self.callback_manager and self.callback_manager.is_complete(task_id):
                logger.info(f"Callback received for task {task_id}")
                audio_url = self.callback_manager.get_audio_url(task_id)
                if audio_url:
                    logger.info(f"Audio URL from callback: {audio_url}")
                    return audio_url
                else:
                    logger.warning("Callback received but no audio URL found, falling back to polling")
            
            # Poll API for status
            status_data = await self.poll_status(task_id)
            status = status_data.get("status")
            
            logger.info(f"Task {task_id} status: {status}")
            
            if status == "SUCCESS":
                logger.info(f"Task {task_id} completed successfully")
                logger.info(f"Full SUCCESS response: {json.dumps(status_data, indent=2)}")
                
                # Try different possible response structures
                audio_url = None
                
                # Structure 1: response.sunoData[0].audioUrl (NEW - actual Suno API structure)
                if status_data.get("response") and status_data["response"].get("sunoData"):
                    tracks = status_data["response"]["sunoData"]
                    if isinstance(tracks, list) and len(tracks) > 0:
                        # Try multiple audio URL fields
                        audio_url = (tracks[0].get("audioUrl") or 
                                   tracks[0].get("sourceAudioUrl") or
                                   tracks[0].get("audio_url"))
                        if audio_url:
                            logger.info(f"Found audio URL in response.sunoData[0]: {audio_url}")
                
                # Structure 2: response.data[0].audio_url
                if not audio_url and status_data.get("response") and status_data["response"].get("data"):
                    tracks = status_data["response"]["data"]
                    if isinstance(tracks, list) and len(tracks) > 0:
                        audio_url = tracks[0].get("audio_url")
                        if audio_url:
                            logger.info(f"Found audio URL in response.data[0]: {audio_url}")
                
                # Structure 3: data[0].audio_url
                if not audio_url and status_data.get("data"):
                    if isinstance(status_data["data"], list) and len(status_data["data"]) > 0:
                        audio_url = status_data["data"][0].get("audio_url")
                        if audio_url:
                            logger.info(f"Found audio URL in data[0]: {audio_url}")
                
                # Structure 4: audioUrl directly in response
                if not audio_url:
                    audio_url = status_data.get("audioUrl") or status_data.get("audio_url")
                    if audio_url:
                        logger.info(f"Found audio URL directly in response: {audio_url}")
                
                if audio_url:
                    return audio_url
                else:
                    error_msg = f"Geen audio URL gevonden in response. Response keys: {list(status_data.keys())}"
                    logger.error(error_msg)
                    logger.error(f"Full response structure: {json.dumps(status_data, indent=2)}")
                    raise Exception(error_msg)
                    
            elif status == "FAILED":
                error_msg = status_data.get("errorMessage", "Onbekende fout")
                logger.error(f"Task {task_id} failed: {error_msg}")
                logger.error(f"Full FAILED response: {json.dumps(status_data, indent=2)}")
                raise Exception(f"Song generatie mislukt: {error_msg}")
            
            # Check timeout
            elapsed = time.time() - start_time
            if elapsed > timeout:
                logger.error(f"Task {task_id} timed out after {elapsed:.1f} seconds")
                raise Exception("Song generatie timeout")
            
            # Wait before next poll (30 seconds as per Suno API recommendation)
            # If using callbacks, can poll less frequently
            poll_interval = 60 if self.callback_manager else 30
            await asyncio.sleep(poll_interval)
    
    async def _download_audio(self, audio_url: str, task_id: str, target_dir: Path) -> str:
        """
        Download audio file from URL.
        
        Args:
            audio_url: URL to audio file
            task_id: Task ID for filename
            target_dir: Directory to save the audio file in
            
        Returns:
            Relative path to saved file
        """
        logger.info(f"Downloading audio from: {audio_url}")
        file_path = target_dir / f"{task_id}.mp3"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(audio_url) as response:
                    if response.status != 200:
                        logger.error(f"Audio download failed with status {response.status}")
                        raise Exception(f"Audio download fout: {response.status}")
                    
                    audio_data = await response.read()
                    logger.info(f"Downloaded {len(audio_data)} bytes")
                    
                    with open(file_path, 'wb') as f:
                        f.write(audio_data)
                    
                    logger.info(f"Audio saved to: {file_path}")
            
            return str(file_path)
            
        except Exception as e:
            logger.error(f"Audio download failed: {str(e)}", exc_info=True)
            raise
    
    def save_audio(self, audio_data: bytes, project_id: str) -> str:
        """
        Save audio file and return path.
        
        Args:
            audio_data: Audio file bytes
            project_id: Project ID for filename
            
        Returns:
            Relative path to saved file
        """
        file_path = self.storage_path / f"{project_id}.mp3"
        
        with open(file_path, 'wb') as f:
            f.write(audio_data)
        
        return str(file_path)
    
    async def get_remaining_credits(self) -> int:
        """
        Get remaining API credits.
        
        Returns:
            Number of remaining credits
        """
        async with aiohttp.ClientSession() as session:
            headers = {
                "Authorization": f"Bearer {self.api_key}"
            }
            
            async with session.get(
                f"{self.base_url}/get-credits",
                headers=headers
            ) as response:
                if response.status != 200:
                    return -1
                
                data = await response.json()
                return data.get('data', {}).get('credits', -1)
