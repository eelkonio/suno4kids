# Async Handling and Concurrent User Support

## Overview

The AI Song Workshop application uses asynchronous operations for all API calls (Claude, Suno, Gemini) to handle long-running tasks without blocking the Flask application.

## Current Implementation

### Async Pattern in Flask Routes

Each route that needs to call async functions follows this pattern:

```python
@bp.route('/api/project/<project_id>/generate-song', methods=['POST'])
def generate_song_route(project_id):
    # ... validation code ...
    
    # Create new event loop for this request
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    # Run async operation
    result = loop.run_until_complete(
        song_producer.generate_song(lyrics, genre, username=username)
    )
    
    # Clean up
    loop.close()
    
    return jsonify({'success': True, 'result': result})
```

### Why This Works for Multiple Users

1. **Separate Event Loops**: Each request creates its own event loop, so concurrent requests don't interfere with each other
2. **Flask Threading**: Flask's built-in development server handles each request in a separate thread
3. **Async Operations**: Long-running API calls (30-90 seconds for song generation) use async/await internally, allowing efficient I/O handling

### User-Specific Directories

All generated content is stored in user-specific directories to prevent conflicts:

- **Images**: `static/images/{sanitized_username}_{hash}/`
- **Audio**: `static/audio/{sanitized_username}_{hash}/`

The hash is a 4-character MD5 hash of the full username, ensuring unique directories even if sanitized names collide.

## Production Considerations

For production deployment with many concurrent users, consider:

### 1. Use a Production WSGI Server

Replace Flask's development server with a production-grade server:

```bash
# Install gunicorn
pip install gunicorn

# Run with multiple workers
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

### 2. Background Task Queue (Optional)

For very high traffic, consider using Celery or RQ for background tasks:

```python
# Example with Celery
from celery import Celery

celery = Celery('tasks', broker='redis://localhost:6379')

@celery.task
def generate_song_task(lyrics, genre, username):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    result = loop.run_until_complete(
        song_producer.generate_song(lyrics, genre, username)
    )
    loop.close()
    return result
```

### 3. Async Flask (Alternative)

Use Quart (async Flask) for native async support:

```python
from quart import Quart

app = Quart(__name__)

@app.route('/api/generate-song', methods=['POST'])
async def generate_song():
    # Direct async/await without event loop management
    result = await song_producer.generate_song(lyrics, genre, username)
    return jsonify({'success': True, 'result': result})
```

## Current Limitations

1. **Request Timeout**: Long-running operations (30-90 seconds) may hit default timeouts
   - Solution: Increase timeout in production server config
   - Alternative: Use webhooks or polling for status updates

2. **Memory Usage**: Each request holds memory until completion
   - Solution: Use background tasks for very long operations

3. **No Progress Updates**: Users don't see progress during generation
   - Solution: Implement WebSocket or Server-Sent Events for real-time updates

## Testing Concurrent Users

To test concurrent user support:

```bash
# Install Apache Bench
brew install apache2  # macOS

# Test with 10 concurrent requests
ab -n 10 -c 10 http://localhost:5000/api/project/test/generate-lyrics
```

## Summary

The current implementation:
- ✅ Supports multiple concurrent users
- ✅ Uses proper async handling for API calls
- ✅ Stores files in user-specific directories
- ✅ Won't block the Flask application
- ⚠️ May need production server for high traffic
- ⚠️ Consider background tasks for very long operations
