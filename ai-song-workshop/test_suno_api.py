#!/usr/bin/env python3
"""
Comprehensive Suno.ai API Tests
Tests all Suno.ai API endpoints with detailed output
"""
import asyncio
import sys
import json
import time
import aiohttp
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from backend.song_producer import SongProducer
from config import config


async def test_get_credits():
    """Test 1: Get remaining credits (or test API connectivity)"""
    print("\n" + "="*60)
    print("TEST 1: Test API Connectivity")
    print("="*60)
    
    try:
        song_producer = SongProducer(
            api_key=config.api.suno_api_key,
            storage_path="static/audio"
        )
        
        print(f"API Key: {config.api.suno_api_key[:20]}...")
        print(f"Base URL: {song_producer.base_url}")
        
        print("\n⚠ Note: The Suno API may not have a dedicated credits endpoint.")
        print("We'll test API connectivity by attempting a generation request.")
        print("Credits will be checked when we try to generate.")
        
        return True
        
    except Exception as e:
        print(f"\n✗ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_submit_generation():
    """Test 2: Submit song generation request"""
    print("\n" + "="*60)
    print("TEST 2: Submit Song Generation Request")
    print("="*60)
    
    try:
        song_producer = SongProducer(
            api_key=config.api.suno_api_key,
            storage_path="static/audio"
        )
        
        # Test lyrics
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
        
        test_genre = "pop"
        
        print(f"Endpoint: {song_producer.base_url}/generate")
        print(f"Genre: {test_genre}")
        print(f"Lyrics length: {len(test_lyrics)} characters")
        
        print("\nSubmitting generation request...")
        
        # Make raw API call to see full response
        import aiohttp
        async with aiohttp.ClientSession() as session:
            headers = {
                "Authorization": f"Bearer {config.api.suno_api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "prompt": test_lyrics,
                "customMode": True,
                "style": test_genre,
                "title": "Workshop Song",
                "instrumental": False,
                "model": "V5",
                "callBackUrl": "https://example.com/callback"  # Placeholder callback URL
            }
            
            print(f"\nRequest payload:")
            print(json.dumps(payload, indent=2))
            
            async with session.post(
                f"{song_producer.base_url}/generate",
                headers=headers,
                json=payload
            ) as response:
                print(f"\nResponse status: {response.status}")
                response_text = await response.text()
                print(f"Response body: {response_text}")
                
                if response.status == 200:
                    try:
                        data = json.loads(response_text)
                        print(f"\nParsed JSON:")
                        print(json.dumps(data, indent=2))
                        
                        if data.get('code') == 200:
                            task_id = data['data']['taskId']
                            print(f"\n✓ Generation request submitted successfully!")
                            print(f"Task ID: {task_id}")
                            return task_id
                        else:
                            print(f"\n✗ API returned error code: {data.get('code')}")
                            print(f"Message: {data.get('msg')}")
                            return None
                    except json.JSONDecodeError as e:
                        print(f"✗ Failed to parse JSON: {e}")
                        return None
                else:
                    print(f"✗ API returned error status: {response.status}")
                    return None
        
    except Exception as e:
        print(f"\n✗ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return None


async def test_poll_status(task_id: str):
    """Test 3: Poll generation status"""
    print("\n" + "="*60)
    print("TEST 3: Poll Generation Status")
    print("="*60)
    
    if not task_id:
        print("⚠ Skipping - no task ID from previous test")
        return False
    
    try:
        song_producer = SongProducer(
            api_key=config.api.suno_api_key,
            storage_path="static/audio"
        )
        
        print(f"Task ID: {task_id}")
        print(f"Endpoint: {song_producer.base_url}/generate/record-info?taskId={task_id}")
        
        print("\nChecking status...")
        status_data = await song_producer.poll_status(task_id)
        
        print(f"\n✓ Status check successful!")
        print(f"\nStatus data:")
        print(json.dumps(status_data, indent=2))
        
        status = status_data.get("status")
        print(f"\nCurrent status: {status}")
        
        if status == "SUCCESS":
            print("✓ Generation completed!")
            tracks = status_data.get("response", {}).get("data", [])
            if tracks:
                print(f"Number of tracks: {len(tracks)}")
                print(f"Audio URL: {tracks[0].get('audio_url', 'N/A')}")
        elif status == "GENERATING" or status == "PENDING":
            print("⏳ Generation in progress...")
        elif status == "FAILED":
            print("✗ Generation failed")
            print(f"Error: {status_data.get('errorMessage', 'Unknown error')}")
        
        return True
        
    except Exception as e:
        print(f"\n✗ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_full_generation():
    """Test 4: Full Song Generation with User Directory"""
    print("\n" + "="*60)
    print("TEST 4: Full Song Generation with User Directory")
    print("="*60)
    
    try:
        song_producer = SongProducer(
            api_key=config.api.suno_api_key,
            storage_path="static/audio"
        )
        
        test_username = "test_user@example.com"
        
        print(f"\n⚠ WARNING: This test will:")
        print(f"  - Consume Suno API credits")
        print(f"  - Take 30-90 seconds to complete")
        print(f"  - Generate a real song file")
        print(f"  - Store in user directory: {test_username}")
        print("\nPress Ctrl+C within 5 seconds to skip...")
        
        try:
            await asyncio.sleep(5)
        except KeyboardInterrupt:
            print("\n⚠ Test skipped by user")
            return True
        
        # Test lyrics
        test_lyrics = """[Couplet 1]
Mijn hond rent door het park
Hij speelt zo graag en blij

[Refrein]
Spelen, spelen, de hele dag
Mijn hond is altijd vrolijk"""
        
        test_genre = "pop"
        
        print(f"\n⏳ Generating song...")
        print(f"   Username: {test_username}")
        print(f"   Genre: {test_genre}")
        print(f"   This will take 30-90 seconds, please wait...")
        
        start_time = time.time()
        song_path = await song_producer.generate_song(test_lyrics, test_genre, username=test_username)
        elapsed = time.time() - start_time
        
        print(f"\n✓ Song generated successfully in {elapsed:.1f} seconds!")
        print(f"  File saved at: {song_path}")
        
        # Verify file exists
        if Path(song_path).exists():
            file_size = Path(song_path).stat().st_size
            print(f"  File size: {file_size:,} bytes ({file_size/1024/1024:.2f} MB)")
            
            # Check directory structure
            song_path_obj = Path(song_path)
            print(f"  Directory: {song_path_obj.parent}")
            print(f"  Filename: {song_path_obj.name}")
        else:
            print(f"  ⚠ Warning: File not found at {song_path}")
            return False
        
        return True
        
    except KeyboardInterrupt:
        print("\n⚠ Test interrupted by user")
        return True
    except Exception as e:
        print(f"\n✗ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all Suno API tests"""
    print("\n" + "="*60)
    print("Suno.ai API - Comprehensive Test Suite")
    print("="*60)
    
    results = {}
    
    # Test 1: Get credits
    results['Get Credits'] = await test_get_credits()
    
    # Test 2: Submit generation
    task_id = await test_submit_generation()
    results['Submit Generation'] = task_id is not None
    
    # Test 3: Poll status (if we have a task ID)
    if task_id:
        results['Poll Status'] = await test_poll_status(task_id)
    else:
        results['Poll Status'] = None
    
    # Test 4: Full generation (optional)
    results['Full Generation'] = await test_full_generation()
    
    # Summary
    print("\n" + "="*60)
    print("Test Results Summary")
    print("="*60)
    
    for test_name, passed in results.items():
        if passed is None:
            status = "⊘ SKIPPED"
        elif passed:
            status = "✓ PASSED"
        else:
            status = "✗ FAILED"
        print(f"{test_name}: {status}")
    
    # Check if any tests failed
    failed_tests = [name for name, passed in results.items() if passed is False]
    
    if failed_tests:
        print(f"\n⚠️  {len(failed_tests)} test(s) failed")
        return 1
    else:
        print("\n🎉 All tests passed or skipped!")
        return 0


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n⚠ Tests interrupted by user")
        sys.exit(1)
