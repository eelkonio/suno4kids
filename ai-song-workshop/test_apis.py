#!/usr/bin/env python3
"""
API Integration Tests for AI Song Workshop
Tests Claude, Suno.ai, and Google Gemini APIs
"""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from backend.lyric_generator import LyricGenerator
from backend.song_producer import SongProducer
from backend.image_generator import ImageGenerator
from backend.content_filter import ContentFilter
from config import config


def test_claude_api():
    """Test Claude API for lyric generation"""
    print("\n" + "="*60)
    print("Testing Claude API (Lyric Generation)")
    print("="*60)
    
    try:
        content_filter = ContentFilter()
        lyric_gen = LyricGenerator(
            api_key=config.api.anthropic_api_key,
            content_filter=content_filter
        )
        
        print("✓ LyricGenerator initialized successfully")
        print(f"  API Key: {config.api.anthropic_api_key[:20]}...")
        
        # Test lyric generation
        print("\nGenerating test lyrics...")
        description = "Een vrolijk liedje over een hond die graag speelt"
        genre = "pop"
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        lyrics = loop.run_until_complete(
            lyric_gen.generate_lyrics(description, genre)
        )
        loop.close()
        
        print("✓ Lyrics generated successfully!")
        print(f"\nGenerated lyrics (first 200 chars):\n{lyrics[:200]}...")
        
        return True
        
    except Exception as e:
        print(f"✗ Claude API test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_suno_api():
    """Test Suno.ai API for song generation"""
    print("\n" + "="*60)
    print("Testing Suno.ai API (Song Generation)")
    print("="*60)
    
    try:
        song_producer = SongProducer(
            api_key=config.api.suno_api_key,
            storage_path="static/audio"
        )
        
        print("✓ SongProducer initialized successfully")
        print(f"  API Key: {config.api.suno_api_key[:20]}...")
        print(f"  Base URL: {song_producer.base_url}")
        
        # Check credits first
        print("\nChecking Suno.ai credits...")
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        credits = loop.run_until_complete(song_producer.get_remaining_credits())
        loop.close()
        
        print(f"✓ Remaining credits: {credits}")
        
        if credits <= 0:
            print("⚠ Warning: No credits remaining. Skipping song generation test.")
            return True
        
        # Test song generation (this takes 30-60 seconds)
        print("\n⏳ Generating test song (this will take 30-60 seconds)...")
        print("   You can skip this by pressing Ctrl+C")
        
        test_lyrics = """[Couplet 1]
Mijn hond rent door het park
Hij speelt zo graag en blij
Met zijn bal in zijn bek
Komt hij terug naar mij

[Refrein]
Spelen, spelen, de hele dag
Mijn hond is altijd vrolijk
Rennen, springen, wat hij maar mag
Hij is zo lief en vrolijk"""
        
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            song_path = loop.run_until_complete(
                song_producer.generate_song(test_lyrics, "pop")
            )
            loop.close()
            
            print(f"✓ Song generated successfully!")
            print(f"  File saved at: {song_path}")
            return True
            
        except KeyboardInterrupt:
            print("\n⚠ Song generation test skipped by user")
            return True
        
    except Exception as e:
        print(f"✗ Suno.ai API test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_google_gemini_api():
    """Test Google Gemini API for image generation"""
    print("\n" + "="*60)
    print("Testing Google Gemini API (Image Generation)")
    print("="*60)
    
    try:
        if not config.api.google_api_key:
            print("⚠ Google API key not configured. Skipping test.")
            return True
        
        content_filter = ContentFilter()
        image_gen = ImageGenerator(
            api_key=config.api.google_api_key,
            content_filter=content_filter,
            storage_path="static/images"
        )
        
        if not image_gen.enabled:
            print("⚠ Image generation not enabled. Check google-genai package.")
            return False
        
        print("✓ ImageGenerator initialized successfully")
        print(f"  API Key: {config.api.google_api_key[:20]}...")
        print(f"  Model: {image_gen.model}")
        
        # Test image generation
        print("\nGenerating test image...")
        description = "Een vrolijk liedje over een hond"
        lyrics = "Mijn hond speelt graag in het park"
        test_username = "test_user@example.com"
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        image_path = loop.run_until_complete(
            image_gen.generate_image(description, lyrics, username=test_username)
        )
        loop.close()
        
        if image_path:
            print(f"✓ Image generated successfully!")
            print(f"  File saved at: {image_path}")
            print(f"  Username: {test_username}")
            return True
        else:
            print("✗ Image generation returned None")
            return False
        
    except Exception as e:
        print(f"✗ Google Gemini API test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all API tests"""
    print("\n" + "="*60)
    print("AI Song Workshop - API Integration Tests")
    print("="*60)
    
    results = {
        'Claude API': test_claude_api(),
        'Suno.ai API': test_suno_api(),
        'Google Gemini API': test_google_gemini_api()
    }
    
    print("\n" + "="*60)
    print("Test Results Summary")
    print("="*60)
    
    for api_name, passed in results.items():
        status = "✓ PASSED" if passed else "✗ FAILED"
        print(f"{api_name}: {status}")
    
    all_passed = all(results.values())
    
    if all_passed:
        print("\n🎉 All API tests passed!")
        return 0
    else:
        print("\n⚠️  Some API tests failed. Check the output above for details.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
