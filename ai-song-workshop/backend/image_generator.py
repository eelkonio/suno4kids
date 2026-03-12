"""
Image generation for AI Song Workshop Website.
Optional feature using Google's Gemini image generation API.
"""
import asyncio
import hashlib
import logging
import re
from pathlib import Path
from typing import Optional
from backend.content_filter import ContentFilter

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


class ImageGenerator:
    """
    Generates song artwork using Google Gemini API.
    
    Attributes:
        api_key: Google API key (optional)
        content_filter: ContentFilter for validation
        enabled: Whether image generation is available
        storage_path: Path for storing images
    """
    
    def __init__(self, api_key: Optional[str], content_filter: ContentFilter, 
                 storage_path: str = "static/images"):
        """
        Initialize ImageGenerator.
        
        Args:
            api_key: Google API key (None to disable feature)
            content_filter: ContentFilter instance
            storage_path: Directory path for image storage
        """
        self.api_key = api_key
        self.content_filter = content_filter
        self.enabled = api_key is not None
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.max_retries = 3
        
        # Initialize Google GenAI client if enabled
        if self.enabled:
            try:
                from google import genai
                import os
                os.environ['GOOGLE_API_KEY'] = api_key
                self.client = genai.Client(api_key=api_key)
                self.model = "gemini-2.5-flash-image"
            except ImportError:
                print("Warning: google-genai package not installed. Image generation disabled.")
                self.enabled = False
            except Exception as e:
                print(f"Warning: Failed to initialize Google GenAI: {e}")
                self.enabled = False
    
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
        Get or create user-specific directory for images.
        
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
    
    def _build_prompt(self, description: str, lyrics: str, retry_count: int = 0) -> str:
        """
        Construct image generation prompt emphasizing child-friendly imagery.
        
        Args:
            description: Song description
            lyrics: Song lyrics
            retry_count: Number of previous attempts
            
        Returns:
            Formatted prompt string
        """
        safety_emphasis = ""
        if retry_count > 0:
            safety_emphasis = "EXTRA IMPORTANT: Previous image was inappropriate. "
        
        prompt = f"""{safety_emphasis}Create a colorful, child-friendly illustration for a song.
Song theme: {description}

Style: Cartoon or illustration style, bright colors, abstract and playful.
NO realistic human faces, NO violence, NO inappropriate content.
Suitable for children aged 9-12.
Make it fun, creative, and engaging."""
        
        return prompt

    
    async def generate_image(
        self, 
        description: str, 
        lyrics: str,
        username: Optional[str] = None,
        max_retries: Optional[int] = None
    ) -> Optional[str]:
        """
        Generate image and return file path.
        Returns None if feature is disabled.
        
        Args:
            description: Song description
            lyrics: Song lyrics
            username: Username for directory organization (optional)
            max_retries: Override default max retries
            
        Returns:
            Relative path to generated image, or None if disabled
            
        Raises:
            ValueError: If unable to generate appropriate image after retries
            Exception: If API call fails
        """
        if not self.enabled:
            return None
        
        if max_retries is None:
            max_retries = self.max_retries
        
        # Get user-specific directory if username provided
        target_dir = self._get_user_directory(username) if username else self.storage_path
        
        for attempt in range(max_retries):
            try:
                # Build prompt with retry context
                prompt = self._build_prompt(description, lyrics, attempt)
                
                logger.info(f"Calling Google Gemini API for image generation (attempt {attempt + 1}/{max_retries})")
                
                # Call Google Gemini API
                image_path = await self._call_image_api(prompt, attempt, target_dir)
                
                logger.info(f"Image generated successfully: {image_path}")
                
                # Validate with content filter
                is_valid, rejection_reason = self.content_filter.validate_image(str(image_path))
                
                if is_valid:
                    logger.info("Image validated successfully")
                    return str(image_path)
                
                # Content rejected, will retry
                logger.warning(f"Image rejected (attempt {attempt + 1}): {rejection_reason}")
                print(f"Image rejected (attempt {attempt + 1}): {rejection_reason}")
                if image_path.exists():
                    image_path.unlink()  # Delete rejected image
                
            except Exception as e:
                logger.error(f"Image API error (attempt {attempt + 1}/{max_retries}): {str(e)}", exc_info=True)
                logger.error(f"Full error details: {repr(e)}")
                print(f"Image API error (attempt {attempt + 1}): {e}")
                if attempt == max_retries - 1:
                    logger.error(f"All retry attempts exhausted for image generation")
                    raise Exception(f"Image generatie fout: {str(e)}")
                await asyncio.sleep(1 * (attempt + 1))
        
        logger.error("Failed to generate appropriate image after all retry attempts")
        raise ValueError("Kon geen geschikte afbeelding genereren na meerdere pogingen")
    
    async def _call_image_api(self, prompt: str, attempt: int, target_dir: Path) -> Path:
        """
        Call Google Gemini API to generate image.
        
        Args:
            prompt: Image generation prompt
            attempt: Attempt number for unique filename
            target_dir: Directory to save the image in
            
        Returns:
            Path to saved image file
        """
        if not self.enabled:
            raise Exception("Image generation is not enabled")
        
        try:
            logger.info(f"Calling Gemini API with model: {self.model}")
            
            # Generate image using Google Gemini
            response = self.client.models.generate_content(
                model=self.model,
                contents=[prompt]
            )
            
            logger.info(f"Gemini API response received")
            
            # Extract and save image
            from PIL import Image
            import io
            import base64
            
            # Check if response has candidates attribute (new API structure)
            if hasattr(response, 'candidates') and response.candidates:
                logger.info(f"Processing response with {len(response.candidates)} candidates")
                for candidate in response.candidates:
                    if hasattr(candidate, 'content') and candidate.content:
                        for part in candidate.content.parts:
                            if hasattr(part, 'inline_data') and part.inline_data is not None:
                                # Extract image data
                                image_data = part.inline_data.data
                                mime_type = part.inline_data.mime_type
                                logger.info(f"Found image data with mime type: {mime_type}")
                                
                                # Decode base64 if needed
                                if isinstance(image_data, str):
                                    image_data = base64.b64decode(image_data)
                                
                                # Create PIL Image and save
                                image = Image.open(io.BytesIO(image_data))
                                image_path = target_dir / f"song_image_{attempt}_{hash(prompt) % 10000}.png"
                                image.save(str(image_path))
                                logger.info(f"Image saved to: {image_path}")
                                return image_path
            # Fallback to direct parts access (old API structure)
            elif hasattr(response, 'parts'):
                logger.info(f"Processing response with direct parts access")
                for part in response.parts:
                    if hasattr(part, 'inline_data') and part.inline_data is not None:
                        # Extract image data
                        image_data = part.inline_data.data
                        mime_type = part.inline_data.mime_type
                        logger.info(f"Found image data with mime type: {mime_type}")
                        
                        # Decode base64 if needed
                        if isinstance(image_data, str):
                            image_data = base64.b64decode(image_data)
                        
                        # Create PIL Image and save
                        image = Image.open(io.BytesIO(image_data))
                        image_path = target_dir / f"song_image_{attempt}_{hash(prompt) % 10000}.png"
                        image.save(str(image_path))
                        logger.info(f"Image saved to: {image_path}")
                        return image_path
            
            logger.error("No image data found in response")
            logger.error(f"Response attributes: {dir(response)}")
            raise Exception("No image data in response")
            
        except Exception as e:
            logger.error(f"Gemini API call failed: {str(e)}", exc_info=True)
            logger.error(f"Full error details: {repr(e)}")
            raise Exception(f"Google Gemini API error: {str(e)}")

    async def edit_image(self, image_data: bytes, prompt: str, username: Optional[str] = None) -> bytes:
        """
        Edit existing image using Gemini API for photo transformation.
        
        Args:
            image_data: Original image bytes (PNG or JPEG)
            prompt: Transformation prompt describing the desired style
            username: Username for logging (optional)
            
        Returns:
            Transformed image as bytes
            
        Raises:
            Exception: If image generation is disabled or API call fails
        """
        if not self.enabled:
            raise Exception("Image generation is not enabled")

        try:
            from google.genai import types
            import base64

            logger.info(f"Calling Gemini API for image editing (user: {username or 'unknown'})")

            response = self.client.models.generate_content(
                model=self.model,
                contents=[
                    types.Part.from_bytes(data=image_data, mime_type="image/png"),
                    prompt
                ]
            )

            logger.info("Gemini image edit response received")

            # Extract image data from response (same pattern as _call_image_api)
            if hasattr(response, 'candidates') and response.candidates:
                for candidate in response.candidates:
                    if hasattr(candidate, 'content') and candidate.content:
                        for part in candidate.content.parts:
                            if hasattr(part, 'inline_data') and part.inline_data is not None:
                                result_data = part.inline_data.data
                                mime_type = part.inline_data.mime_type
                                logger.info(f"Found edited image data with mime type: {mime_type}")

                                if isinstance(result_data, str):
                                    result_data = base64.b64decode(result_data)

                                logger.info(f"Image edit completed successfully (user: {username or 'unknown'}, size: {len(result_data)} bytes)")
                                return result_data

            # Fallback to direct parts access
            if hasattr(response, 'parts'):
                for part in response.parts:
                    if hasattr(part, 'inline_data') and part.inline_data is not None:
                        result_data = part.inline_data.data
                        mime_type = part.inline_data.mime_type
                        logger.info(f"Found edited image data with mime type: {mime_type}")

                        if isinstance(result_data, str):
                            result_data = base64.b64decode(result_data)

                        logger.info(f"Image edit completed successfully (user: {username or 'unknown'}, size: {len(result_data)} bytes)")
                        return result_data

            logger.error("No image data found in edit response")
            raise Exception("No image data in Gemini edit response")

        except Exception as e:
            logger.error(f"Gemini image edit failed: {str(e)}", exc_info=True)
            raise Exception(f"Photo transformation failed: {str(e)}")
