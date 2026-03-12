"""
Photo transformation service for AI Song Workshop Website.
Handles webcam photo transformations using Gemini API.
"""
import base64
import hashlib
import io
import logging
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Dict, List, Tuple
from PIL import Image

logger = logging.getLogger(__name__)


@dataclass
class TransformationStyle:
    """Model for transformation style definition."""
    id: str
    name: str
    description: str
    icon: str
    category: str
    prompt_template: str


class PhotoTransformer:
    """
    Handles webcam photo transformation using Gemini API.
    
    Attributes:
        image_generator: ImageGenerator instance for Gemini API access
        content_filter: ContentFilter for validation
        session_manager: SessionManager for temporary storage
        max_image_size: Maximum image size in bytes (5MB)
        supported_formats: List of supported image formats
    """
    
    # Define all 17 transformation styles
    TRANSFORMATION_STYLES = [
        TransformationStyle(
            id="old-painting",
            name="Old Painting",
            description="Rembrandt-style painting from the 1700s",
            icon="🎨",
            category="artistic",
            prompt_template="old_painting"
        ),
        TransformationStyle(
            id="futuristic-city",
            name="Futuristic City",
            description="Flying cars, rockets, and robots",
            icon="🚀",
            category="fantasy",
            prompt_template="futuristic_city"
        ),
        TransformationStyle(
            id="pop-star",
            name="Pop Star Stage",
            description="Performance with thousands of fans",
            icon="🎤",
            category="character",
            prompt_template="pop_star"
        ),
        TransformationStyle(
            id="superhero",
            name="Superhero Movie",
            description="Explosive action scenes",
            icon="🦸",
            category="character",
            prompt_template="superhero"
        ),
        TransformationStyle(
            id="demon-hunters",
            name="Demon Hunters",
            description="Korean anime fighting scenes",
            icon="⚔️",
            category="character",
            prompt_template="demon_hunters"
        ),
        TransformationStyle(
            id="disney-princess",
            name="Disney Princess",
            description="Ball gown, tiara, magical castle",
            icon="👑",
            category="character",
            prompt_template="disney_princess"
        ),
        TransformationStyle(
            id="disney-prince",
            name="Disney Prince",
            description="Royal outfit, crown, heroic pose",
            icon="🤴",
            category="character",
            prompt_template="disney_prince"
        ),
        TransformationStyle(
            id="minion-mayhem",
            name="Minion Mayhem",
            description="Surrounded by yellow Minions",
            icon="🍌",
            category="character",
            prompt_template="minion_mayhem"
        ),
        TransformationStyle(
            id="minecraft",
            name="Minecraft World",
            description="Blocky pixelated with Creepers",
            icon="⛏️",
            category="fantasy",
            prompt_template="minecraft"
        ),
        TransformationStyle(
            id="lego",
            name="LEGO Minifigure",
            description="Classic yellow LEGO character",
            icon="🧱",
            category="character",
            prompt_template="lego"
        ),
        TransformationStyle(
            id="astronaut",
            name="Astronaut on Mars",
            description="Space suit on red planet",
            icon="🚀",
            category="adventure",
            prompt_template="astronaut"
        ),
        TransformationStyle(
            id="pirate",
            name="Pirate Adventure",
            description="Pirate costume, treasure, ship",
            icon="🏴‍☠️",
            category="adventure",
            prompt_template="pirate"
        ),
        TransformationStyle(
            id="wizard",
            name="Wizard School",
            description="Hogwarts robes, wand, magic",
            icon="🧙",
            category="fantasy",
            prompt_template="wizard"
        ),
        TransformationStyle(
            id="dinosaur",
            name="Dinosaur Park",
            description="Surrounded by friendly dinosaurs",
            icon="🦕",
            category="adventure",
            prompt_template="dinosaur"
        ),
        TransformationStyle(
            id="mermaid",
            name="Underwater Mermaid/Merman",
            description="Tail, coral reefs, fish",
            icon="🧜",
            category="fantasy",
            prompt_template="mermaid"
        ),
        TransformationStyle(
            id="video-game",
            name="Video Game Hero",
            description="Retro 8-bit or modern game style",
            icon="🎮",
            category="character",
            prompt_template="video_game"
        ),
        TransformationStyle(
            id="ice-kingdom",
            name="Ice Kingdom",
            description="Frozen-inspired ice palace",
            icon="❄️",
            category="fantasy",
            prompt_template="ice_kingdom"
        ),
    ]
    
    def __init__(self, image_generator, content_filter, session_manager):
        """
        Initialize PhotoTransformer with dependencies.
        
        Args:
            image_generator: ImageGenerator instance for Gemini API access
            content_filter: ContentFilter for validation
            session_manager: SessionManager for temporary storage
        """
        self.image_generator = image_generator
        self.content_filter = content_filter
        self.session_manager = session_manager
        self.max_image_size = 5 * 1024 * 1024  # 5MB
        self.supported_formats = ['PNG', 'JPEG']
        self.storage_path = Path("static/photos")
        self.storage_path.mkdir(parents=True, exist_ok=True)

    def _get_user_directory(self, username: str) -> Path:
        """Get or create user-specific photo directory (matches song image pattern)."""
        sanitized = re.sub(r'[^a-zA-Z0-9_-]', '', username) or 'user'
        hash_code = hashlib.md5(username.encode('utf-8')).hexdigest()[:4]
        user_dir = self.storage_path / f"{sanitized}_{hash_code}"
        user_dir.mkdir(parents=True, exist_ok=True)
        return user_dir

    def _save_photos(self, username: str, style_id: str, original_bytes: bytes, transformed_bytes: bytes) -> Tuple[str, str]:
        """
        Save original and transformed photos to disk under the user's directory.

        Returns:
            Tuple of (original_path, transformed_path) relative to app root.
        """
        user_dir = self._get_user_directory(username)
        timestamp = int(time.time())
        orig_path = user_dir / f"original_{style_id}_{timestamp}.png"
        trans_path = user_dir / f"transformed_{style_id}_{timestamp}.png"

        Image.open(io.BytesIO(original_bytes)).save(str(orig_path))
        Image.open(io.BytesIO(transformed_bytes)).save(str(trans_path))

        logger.info(f"Photos saved: {orig_path}, {trans_path}")
        return str(orig_path), str(trans_path)
    
    @classmethod
    def get_style_by_id(cls, style_id: str) -> Optional[TransformationStyle]:
        """
        Get transformation style by ID.
        
        Args:
            style_id: Style identifier
            
        Returns:
            TransformationStyle if found, None otherwise
        """
        for style in cls.TRANSFORMATION_STYLES:
            if style.id == style_id:
                return style
        return None
    
    @classmethod
    def get_all_styles(cls) -> List[Dict]:
        """
        Get all transformation styles as dictionaries.
        
        Returns:
            List of style dictionaries
        """
        return [
            {
                'id': style.id,
                'name': style.name,
                'description': style.description,
                'icon': style.icon,
                'category': style.category
            }
            for style in cls.TRANSFORMATION_STYLES
        ]

    def _get_style_prompt(self, style_id: str) -> str:
        """
        Get the full Gemini API prompt for a given transformation style.

        Args:
            style_id: One of the 17 transformation style IDs

        Returns:
            Full prompt text for the style

        Raises:
            ValueError: If style_id is not recognized
        """
        prompts = {
            "old-painting": (
                "Edit this photo to transform it into a classical oil painting from the 1700s in the style of Rembrandt.\n"
                "\n"
                "Style Requirements:\n"
                "- Rich, dark background with dramatic lighting (chiaroscuro effect)\n"
                "- Warm, earthy color palette: deep browns, golden yellows, dark reds\n"
                "- Visible brush strokes and oil painting texture\n"
                "- Renaissance-era clothing: elaborate collars, rich fabrics, period-appropriate attire\n"
                "- Formal, dignified pose as in classical portraiture\n"
                "- Subtle aging effects: slight cracks in paint, antique canvas texture\n"
                "\n"
                "Important:\n"
                "- Transform the person into a noble or merchant from the 1700s\n"
                "- Background should be a dark, atmospheric interior with subtle details\n"
                "- Maintain the person's recognizable features while adding classical painting qualities\n"
                "- Child-friendly and historically inspired"
            ),
            "futuristic-city": (
                "Edit this photo to place the person in an advanced futuristic city scene.\n"
                "\n"
                "Style Requirements:\n"
                "- Background: towering skyscrapers with glowing neon lights, flying cars zooming past\n"
                "- Holographic displays and digital billboards floating in the air\n"
                "- Sleek robots and drones in the scene\n"
                "- Person wearing futuristic clothing: metallic fabrics, LED accents, high-tech accessories\n"
                "- Rockets or spacecraft visible in the sky\n"
                "- Vibrant color palette: electric blues, neon purples, bright cyans\n"
                "- Clean, high-tech aesthetic with smooth surfaces and glowing elements\n"
                "\n"
                "Important:\n"
                "- Create a sense of wonder and advanced technology\n"
                "- Background should be a bustling futuristic metropolis\n"
                "- Person should look like a citizen of the future\n"
                "- Exciting and optimistic vision of tomorrow"
            ),
            "pop-star": (
                "Edit this photo to transform the person into a pop star performing on a massive concert stage.\n"
                "\n"
                "Style Requirements:\n"
                "- Person dressed as a pop star: sparkly outfit, microphone in hand, confident pose\n"
                "- Massive stage with dramatic lighting: spotlights, laser beams, colorful stage lights\n"
                "- Background: enormous crowd of thousands of cheering fans with raised hands\n"
                "- Stage effects: pyrotechnics, confetti, smoke machines\n"
                "- Concert screens showing the performance\n"
                "- Vibrant, energetic atmosphere with bright colors\n"
                "- Professional concert production quality\n"
                "\n"
                "Important:\n"
                "- Capture the excitement and energy of a major concert\n"
                "- Person should be the star performer in the spotlight\n"
                "- Crowd should be enthusiastic and massive\n"
                "- Glamorous and exciting performance atmosphere"
            ),
            "superhero": (
                "Edit this photo to transform the person into a superhero in an explosive action scene.\n"
                "\n"
                "Style Requirements:\n"
                "- Person in superhero costume: cape, mask, emblem, heroic pose\n"
                "- Dynamic action scene: mid-flight, landing, or power pose\n"
                "- Background: city scene with dramatic action - explosions, energy blasts, debris\n"
                "- Cinematic lighting and effects: lens flares, motion blur, dramatic shadows\n"
                "- Epic scale: tall buildings, dramatic sky, sense of power\n"
                "- Vibrant superhero colors: bold reds, blues, golds\n"
                "- Movie poster quality composition\n"
                "\n"
                "Important:\n"
                "- Create an epic, heroic atmosphere\n"
                "- Person should look powerful and heroic\n"
                "- Action should be exciting but not violent or scary\n"
                "- Suitable for children - fun superhero adventure style"
            ),
            "demon-hunters": (
                "Edit this photo to transform the person into a demon hunter character in Korean anime/manhwa style.\n"
                "\n"
                "Style Requirements:\n"
                "- Anime art style: large expressive eyes, dynamic hair, stylized features\n"
                "- Person in demon hunter outfit: traditional Korean-inspired warrior clothing with modern elements\n"
                "- Action pose: wielding a glowing weapon (sword, staff, or magical energy)\n"
                "- Background: mystical Korean temple or mountain landscape with magical effects\n"
                "- Dramatic lighting with glowing magical auras and energy effects\n"
                "- Vibrant colors: deep purples, electric blues, golden glows\n"
                "- Dynamic composition with motion lines and energy bursts\n"
                "\n"
                "Important:\n"
                "- Korean manhwa/webtoon aesthetic\n"
                "- Heroic and powerful but not scary or violent\n"
                "- Magical and mystical atmosphere\n"
                "- Cool and exciting for kids who love anime"
            ),
            "disney-princess": (
                "Edit this photo to transform the person into a Disney-style princess.\n"
                "\n"
                "Style Requirements:\n"
                "- Person in elegant ball gown: flowing fabric, sparkles, pastel colors\n"
                "- Beautiful tiara or crown on head\n"
                "- Magical castle in the background: tall towers, flags, fairy-tale architecture\n"
                "- Sparkles and magical glitter effects throughout the scene\n"
                "- Soft, dreamy lighting with warm golden tones\n"
                "- Enchanted garden or ballroom setting\n"
                "- Disney animation-inspired art style: soft features, big eyes, graceful pose\n"
                "- Magical creatures: butterflies, birds, or small woodland animals\n"
                "\n"
                "Important:\n"
                "- Classic Disney princess aesthetic\n"
                "- Magical, dreamy, and elegant atmosphere\n"
                "- Suitable for all children\n"
                "- Enchanting and inspiring"
            ),
            "disney-prince": (
                "Edit this photo to transform the person into a Disney-style prince.\n"
                "\n"
                "Style Requirements:\n"
                "- Person in royal prince outfit: elegant jacket, cape, royal colors (blue, red, gold)\n"
                "- Crown or royal circlet on head\n"
                "- Heroic, confident pose\n"
                "- Background: majestic castle with towers and an enchanted forest\n"
                "- Magical lighting with golden sunbeams\n"
                "- Disney animation-inspired art style: strong features, heroic proportions\n"
                "- Royal setting: throne room, castle courtyard, or forest clearing\n"
                "- Magical elements: sparkles, glowing effects, enchanted atmosphere\n"
                "\n"
                "Important:\n"
                "- Classic Disney prince aesthetic\n"
                "- Noble, heroic, and inspiring\n"
                "- Magical and adventurous atmosphere\n"
                "- Suitable for all children"
            ),
            "minion-mayhem": (
                "Edit this photo to surround the person with dozens of Minions from Despicable Me.\n"
                "\n"
                "Style Requirements:\n"
                "- Person in the center, surrounded by 20-30 yellow Minions\n"
                "- Minions in various poses: waving, laughing, jumping, causing chaos\n"
                "- Minions wearing their signature goggles and denim overalls\n"
                "- Colorful, chaotic, fun atmosphere\n"
                "- Background: Gru's lab or colorful cartoon environment\n"
                "- Bright, vibrant colors: lots of yellow, blue, and bright accents\n"
                "- Cartoon style blending with the person\n"
                "- Playful and silly mood\n"
                "\n"
                "Important:\n"
                "- Capture the fun, chaotic energy of Minions\n"
                "- Lots of Minions doing silly things\n"
                "- Person should be interacting happily with the Minions\n"
                "- Funny and entertaining for kids"
            ),
            "minecraft": (
                "Edit this photo to transform the person and environment into Minecraft's blocky, pixelated style.\n"
                "\n"
                "Style Requirements:\n"
                "- Person transformed into blocky, pixelated Minecraft character style\n"
                "- Minecraft-style clothing and appearance\n"
                "- Background: iconic Minecraft landscape with cube blocks, grass, trees, mountains\n"
                "- Minecraft creatures: Creepers, pigs, chickens, sheep nearby\n"
                "- Diamond ore, crafting tables, or other Minecraft items visible\n"
                "- Pixelated, blocky aesthetic throughout\n"
                "- Bright, saturated colors typical of Minecraft\n"
                "- Day or sunset lighting in Minecraft style\n"
                "\n"
                "Important:\n"
                "- Everything should have the distinctive Minecraft blocky, pixelated look\n"
                "- Include recognizable Minecraft elements\n"
                "- Fun and adventurous Minecraft atmosphere\n"
                "- Person should be recognizable but fully Minecraft-styled"
            ),
            "lego": (
                "Edit this photo to transform the person into a LEGO Minifigure in a LEGO brick-built world.\n"
                "\n"
                "Style Requirements:\n"
                "- Person transformed into LEGO Minifigure: classic yellow head, cylindrical body, claw hands\n"
                "- LEGO-style facial features: simple dots for eyes, curved smile\n"
                "- LEGO outfit appropriate to a theme (city, space, castle, etc.)\n"
                "- Background: entirely built from LEGO bricks - buildings, vehicles, landscape\n"
                "- Bright, primary colors: red, blue, yellow, green\n"
                "- Plastic toy appearance with slight shine\n"
                "- Other LEGO Minifigures in the scene\n"
                "- LEGO studs visible on bricks\n"
                "\n"
                "Important:\n"
                "- Complete LEGO toy aesthetic\n"
                "- Person should look like an actual LEGO Minifigure\n"
                "- Everything in the scene should be made of LEGO bricks\n"
                "- Fun, playful, and colorful"
            ),
            "astronaut": (
                "Edit this photo to transform the person into an astronaut exploring Mars.\n"
                "\n"
                "Style Requirements:\n"
                "- Person in full astronaut space suit: white suit with NASA-style patches, helmet with reflective visor\n"
                "- Background: Mars surface with red rocky terrain, craters, and mountains\n"
                "- Mars rovers or scientific equipment nearby\n"
                "- Earth visible as a small blue dot in the pink Martian sky\n"
                "- Dramatic space lighting: bright sun, long shadows\n"
                "- Futuristic space exploration equipment\n"
                "- Sense of wonder and exploration\n"
                "- Realistic space photography style\n"
                "\n"
                "Important:\n"
                "- Capture the excitement of space exploration\n"
                "- Mars environment should be scientifically inspired\n"
                "- Person should look like a real astronaut\n"
                "- Inspiring and educational"
            ),
            "pirate": (
                "Edit this photo to transform the person into a pirate on a high-seas adventure.\n"
                "\n"
                "Style Requirements:\n"
                "- Person in pirate costume: tricorn hat, eye patch, bandana, vest, boots\n"
                "- Pirate accessories: sword, telescope, compass\n"
                "- Background: wooden ship deck with sails, rigging, and pirate flag\n"
                "- Treasure chest overflowing with gold coins and jewels\n"
                "- Tropical island with palm trees in the distance\n"
                "- Parrots perched on shoulders or nearby\n"
                "- Ocean with waves and blue sky\n"
                "- Adventure movie aesthetic with warm, vibrant colors\n"
                "\n"
                "Important:\n"
                "- Fun, adventurous pirate atmosphere (not scary)\n"
                "- Treasure and exploration theme\n"
                "- Colorful and exciting\n"
                "- Suitable for children - playful pirate adventure"
            ),
            "wizard": (
                "Edit this photo to transform the person into a student at a magical wizard school.\n"
                "\n"
                "Style Requirements:\n"
                "- Person in wizard robes: Hogwarts-style house colors, scarf, wizard hat\n"
                "- Holding a magic wand with glowing tip\n"
                "- Background: magical castle interior - stone walls, floating candles, moving staircases\n"
                "- Magical creatures: owls, cats, or small magical beings\n"
                "- Floating books, potion bottles, and magical artifacts\n"
                "- Magical effects: sparkles, glowing spells, floating objects\n"
                "- Warm, atmospheric lighting with candlelight\n"
                "- Harry Potter-inspired aesthetic\n"
                "\n"
                "Important:\n"
                "- Magical school atmosphere\n"
                "- Sense of wonder and learning magic\n"
                "- Whimsical and enchanting\n"
                "- Suitable for children who love magic stories"
            ),
            "dinosaur": (
                "Edit this photo to place the person in a prehistoric park surrounded by friendly dinosaurs.\n"
                "\n"
                "Style Requirements:\n"
                "- Person in explorer outfit: safari vest, hat, binoculars\n"
                "- Background: lush prehistoric jungle with giant ferns and ancient trees\n"
                "- Multiple friendly dinosaurs: T-Rex, Triceratops, Brachiosaurus, Pterodactyls\n"
                "- Dinosaurs should look realistic but friendly and non-threatening\n"
                "- Vibrant green jungle environment\n"
                "- Sense of adventure and discovery\n"
                "- Jurassic Park-inspired but child-friendly\n"
                "- Dramatic but safe atmosphere\n"
                "\n"
                "Important:\n"
                "- Dinosaurs should be impressive but not scary\n"
                "- Exciting prehistoric adventure\n"
                "- Educational and fun\n"
                "- Person should look excited and safe"
            ),
            "mermaid": (
                "Edit this photo to transform the person into a mermaid or merman in an underwater scene.\n"
                "\n"
                "Style Requirements:\n"
                "- Person with beautiful fish tail: shimmering scales in blues, greens, purples, or pinks\n"
                "- Underwater environment: clear blue water with sun rays filtering down\n"
                "- Colorful coral reefs with various coral formations\n"
                "- Tropical fish swimming around: clownfish, angelfish, butterflyfish\n"
                "- Sea turtles, dolphins, or friendly sea creatures\n"
                "- Bubbles floating upward\n"
                "- Flowing hair as if underwater\n"
                "- Magical, ethereal lighting\n"
                "- Little Mermaid-inspired aesthetic\n"
                "\n"
                "Important:\n"
                "- Beautiful, magical underwater world\n"
                "- Person should look graceful and at home underwater\n"
                "- Vibrant ocean colors\n"
                "- Enchanting and peaceful atmosphere"
            ),
            "video-game": (
                "Edit this photo to transform the person into a video game character with game UI elements.\n"
                "\n"
                "Style Requirements:\n"
                "- Person styled as video game character: either retro 8-bit pixel art OR modern 3D game style\n"
                "- Video game UI elements: health bar, score counter, power-up icons, level indicator\n"
                "- Background: video game level environment (platform game, adventure game, or RPG style)\n"
                "- Game elements: floating coins, power-up boxes, collectible items\n"
                "- Vibrant, saturated video game colors\n"
                "- Action pose or heroic stance\n"
                "- Game effects: sparkles, stars, motion lines\n"
                "- Choose style: retro (8-bit, 16-bit) OR modern (3D rendered)\n"
                "\n"
                "Important:\n"
                "- Clear video game aesthetic\n"
                "- Fun and energetic\n"
                "- Include recognizable game elements\n"
                "- Exciting gaming atmosphere"
            ),
            "ice-kingdom": (
                "Edit this photo to transform the person into royalty in a magical ice kingdom.\n"
                "\n"
                "Style Requirements:\n"
                "- Person in ice-themed royal outfit: sparkling ice-blue dress or suit, snowflake patterns\n"
                "- Ice crown or tiara with crystalline details\n"
                "- Background: magnificent ice palace with crystalline architecture, ice towers, frozen waterfalls\n"
                "- Magical ice and snow effects: swirling snowflakes, ice crystals, frost patterns\n"
                "- Ice powers effect: magical ice emanating from hands, frozen magic\n"
                "- Winter wonderland: snow-covered landscape, ice sculptures, northern lights in sky\n"
                "- Frozen movie-inspired aesthetic\n"
                "- Cool color palette: blues, whites, silvers, purples\n"
                "- Magical, ethereal lighting\n"
                "\n"
                "Important:\n"
                "- Frozen/Elsa-inspired magical ice theme\n"
                "- Beautiful and magical winter atmosphere\n"
                "- Person should look regal and magical\n"
                "- Enchanting ice palace setting"
            ),
        }

        if style_id not in prompts:
            raise ValueError(f"Unknown style_id: {style_id}")

        return prompts[style_id]

    def _validate_image(self, image_data: bytes) -> Tuple[bool, str]:
        """
        Validate image data for format, size, and dimensions.

        Args:
            image_data: Raw image bytes

        Returns:
            Tuple of (is_valid, error_message). error_message is empty if valid.
        """
        # Check file size (max 5MB)
        if len(image_data) > self.max_image_size:
            size_mb = len(image_data) / (1024 * 1024)
            return False, f"Afbeelding te groot: {size_mb:.1f}MB (max 5MB)"

        try:
            image = Image.open(io.BytesIO(image_data))
        except Exception:
            return False, "Ongeldig afbeeldingsformaat. Gebruik PNG of JPEG."

        # Check format
        if image.format not in self.supported_formats:
            return False, f"Niet-ondersteund formaat: {image.format}. Gebruik PNG of JPEG."

        # Check dimensions
        width, height = image.size
        if width < 200 or height < 200:
            return False, f"Afbeelding te klein: {width}x{height} (minimaal 200x200)"
        if width > 4096 or height > 4096:
            return False, f"Afbeelding te groot: {width}x{height} (maximaal 4096x4096)"

        return True, ""

    async def transform_photo(self, image_data_b64: str, style_id: str, username: str) -> Dict:
        """
        Transform a photo using the specified artistic style.

        Args:
            image_data_b64: Base64-encoded image data (PNG or JPEG)
            style_id: One of the 17 transformation style IDs
            username: Username for logging and session tracking

        Returns:
            Dict with keys: success, transformed_image, original_image, style, error
        """
        logger.info(f"Photo transformation requested: style={style_id}, user={username}")

        # Validate style
        style = self.get_style_by_id(style_id)
        if not style:
            logger.warning(f"Invalid style_id: {style_id}")
            return {
                'success': False,
                'transformed_image': None,
                'original_image': None,
                'style': style_id,
                'error': f"Onbekende stijl: {style_id}"
            }

        # Decode base64
        try:
            image_bytes = base64.b64decode(image_data_b64)
        except Exception as e:
            logger.error(f"Base64 decode failed: {e}")
            return {
                'success': False,
                'transformed_image': None,
                'original_image': image_data_b64,
                'style': style_id,
                'error': "Ongeldige afbeeldingsdata."
            }

        # Validate image
        is_valid, error_msg = self._validate_image(image_bytes)
        if not is_valid:
            logger.warning(f"Image validation failed: {error_msg}")
            return {
                'success': False,
                'transformed_image': None,
                'original_image': image_data_b64,
                'style': style_id,
                'error': error_msg
            }

        # Get style prompt
        try:
            prompt = self._get_style_prompt(style_id)
        except ValueError as e:
            logger.error(f"Prompt lookup failed: {e}")
            return {
                'success': False,
                'transformed_image': None,
                'original_image': image_data_b64,
                'style': style_id,
                'error': str(e)
            }

        # Call Gemini API via ImageGenerator
        try:
            result_bytes = await self.image_generator.edit_image(
                image_data=image_bytes,
                prompt=prompt,
                username=username
            )
            result_b64 = base64.b64encode(result_bytes).decode('utf-8')

            # Save both images to disk under user's directory
            try:
                orig_path, trans_path = self._save_photos(username, style_id, image_bytes, result_bytes)
            except Exception as save_err:
                logger.error(f"Failed to save photos to disk: {save_err}", exc_info=True)
                orig_path, trans_path = None, None

            logger.info(f"Photo transformation successful: style={style_id}, user={username}")
            return {
                'success': True,
                'transformed_image': result_b64,
                'original_image': image_data_b64,
                'style': style_id,
                'original_path': orig_path,
                'transformed_path': trans_path,
                'error': None
            }
        except Exception as e:
            logger.error(f"Photo transformation failed: {e}", exc_info=True)
            return {
                'success': False,
                'transformed_image': None,
                'original_image': image_data_b64,
                'style': style_id,
                'error': f"Transformatie mislukt: {str(e)}"
            }


@dataclass
class PhotoSession:
    """Tracks a photo transformation session (no persistent image storage)."""
    session_id: str
    username: str
    style_id: str
    created_at: str
    success: bool


class PhotoSessionManager:
    """
    Manages photo transformation sessions.
    Photos are kept in-memory (base64) and never persisted to disk.
    Sessions are tracked for logging and rate limiting only.
    """

    def __init__(self, max_per_user: int = 3, expiry_seconds: int = 3600):
        self.max_per_user = max_per_user
        self.expiry_seconds = expiry_seconds
        self._sessions: Dict[str, List[PhotoSession]] = {}

    def _cleanup_expired(self, username: str):
        """Remove expired sessions for a user."""
        import datetime
        now = datetime.datetime.utcnow()
        if username in self._sessions:
            self._sessions[username] = [
                s for s in self._sessions[username]
                if (now - datetime.datetime.fromisoformat(s.created_at)).total_seconds() < self.expiry_seconds
            ]

    def can_transform(self, username: str) -> bool:
        """Check if user hasn't exceeded the session limit."""
        self._cleanup_expired(username)
        return len(self._sessions.get(username, [])) < self.max_per_user

    def record_session(self, username: str, style_id: str, success: bool) -> PhotoSession:
        """Record a transformation session."""
        import datetime
        import uuid
        session = PhotoSession(
            session_id=str(uuid.uuid4())[:8],
            username=username,
            style_id=style_id,
            created_at=datetime.datetime.utcnow().isoformat(),
            success=success
        )
        if username not in self._sessions:
            self._sessions[username] = []
        self._sessions[username].append(session)
        logger.info(f"Photo session recorded: user={username}, style={style_id}, success={success}")
        return session

    def get_user_sessions(self, username: str) -> List[PhotoSession]:
        """Get active sessions for a user."""
        self._cleanup_expired(username)
        return self._sessions.get(username, [])

    def cleanup_all_expired(self):
        """Clean up expired sessions for all users."""
        for username in list(self._sessions.keys()):
            self._cleanup_expired(username)
            if not self._sessions[username]:
                del self._sessions[username]
