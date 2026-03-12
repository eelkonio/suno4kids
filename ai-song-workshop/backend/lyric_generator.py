"""
Lyric generation using Claude API for AI Song Workshop Website.
"""
import asyncio
import logging
from anthropic import Anthropic
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


class LyricGenerator:
    """
    Generates age-appropriate song lyrics using Claude API.
    
    Attributes:
        client: Anthropic API client
        content_filter: ContentFilter for validation
        max_retries: Maximum regeneration attempts
    """
    
    def __init__(self, api_key: str, content_filter: ContentFilter):
        """
        Initialize LyricGenerator.
        
        Args:
            api_key: Anthropic API key
            content_filter: ContentFilter instance
        """
        self.client = Anthropic(api_key=api_key)
        self.content_filter = content_filter
        self.max_retries = 3
    
    def _build_prompt(self, description: str, genre: str, retry_count: int = 0) -> str:
        """
        Construct Claude API prompt with safety constraints.
        
        Args:
            description: Song description from user
            genre: Music genre
            retry_count: Number of previous attempts (for enhanced safety)
            
        Returns:
            Formatted prompt string
        """
        safety_emphasis = ""
        if retry_count > 0:
            safety_emphasis = """
EXTRA BELANGRIJK: De vorige tekst was niet geschikt. 
Zorg ervoor dat deze tekst ABSOLUUT geschikt is voor kinderen van 9-12 jaar.
Geen geweld, geen ongepaste taal, geen volwassen thema's.
"""

        
        prompt = f"""Je bent een vriendelijke songwriter die liedjes schrijft voor kinderen van 9-12 jaar.

Schrijf een {genre} liedje in het Nederlands over: {description}

{safety_emphasis}

BELANGRIJKE REGELS:
- De tekst moet geschikt zijn voor kinderen van 9-12 jaar
- Gebruik eenvoudige, positieve taal
- Geen geweld, drugs, alcohol of volwassen thema's
- Geen ongepaste taal
- Maak het leuk, creatief en educatief
- Gebruik een duidelijke structuur met coupletten en refrein

Schrijf de volledige songtekst met duidelijke labels voor [Couplet 1], [Refrein], etc.
"""
        return prompt
    
    async def generate_lyrics(
        self, 
        description: str, 
        genre: str,
        max_retries: Optional[int] = None
    ) -> str:
        """
        Generate lyrics with content filtering and retry logic.
        
        Args:
            description: Song description
            genre: Music genre
            max_retries: Override default max retries
            
        Returns:
            Generated and validated lyrics
            
        Raises:
            ValueError: If unable to generate appropriate content after retries
            Exception: If API call fails
        """
        if max_retries is None:
            max_retries = self.max_retries
        
        for attempt in range(max_retries):
            try:
                # Build prompt with retry context
                prompt = self._build_prompt(description, genre, attempt)
                
                logger.info(f"Calling Claude API (attempt {attempt + 1}/{max_retries})")
                
                # Call Claude API
                message = self.client.messages.create(
                    model="claude-haiku-4-5-20251001",
                    max_tokens=1024,
                    messages=[
                        {"role": "user", "content": prompt}
                    ]
                )
                
                logger.info(f"Claude API call successful, received {len(message.content[0].text)} characters")
                
                # Extract lyrics from response
                lyrics = message.content[0].text
                
                # Validate with content filter
                is_valid, rejection_reason = self.content_filter.validate_lyrics(lyrics)
                
                if is_valid:
                    logger.info("Lyrics validated successfully")
                    return lyrics
                
                # Content rejected, will retry
                logger.warning(f"Lyrics rejected (attempt {attempt + 1}): {rejection_reason}")
                print(f"Lyrics rejected (attempt {attempt + 1}): {rejection_reason}")
                
            except Exception as e:
                logger.error(f"Claude API error (attempt {attempt + 1}/{max_retries}): {str(e)}", exc_info=True)
                logger.error(f"Full error details: {repr(e)}")
                print(f"API error (attempt {attempt + 1}): {e}")
                if attempt == max_retries - 1:
                    logger.error(f"All retry attempts exhausted for Claude API")
                    raise Exception(f"Claude API fout: {str(e)}")
                await asyncio.sleep(1 * (attempt + 1))  # Exponential backoff
        
        logger.error("Failed to generate appropriate lyrics after all retry attempts")
        raise ValueError("Kon geen geschikte tekst genereren na meerdere pogingen")
