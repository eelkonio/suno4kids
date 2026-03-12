# Error Logging System

## Overview

The AI Song Workshop application includes comprehensive error logging for all API calls. When any API call fails, the full error response is logged to help with debugging and monitoring.

## Log File Location

All logs are written to: `logs/workshop.log`

## Logging Configuration

Each backend module (lyric_generator, song_producer, image_generator) has its own logger configured with:

- **Log Level**: INFO (captures INFO, WARNING, ERROR, and CRITICAL messages)
- **Format**: `%(asctime)s - %(name)s - %(levelname)s - %(message)s`
- **Handlers**:
  - FileHandler: Writes to `logs/workshop.log`
  - StreamHandler: Outputs to console/stdout

## What Gets Logged

### Successful Operations

- API call initiation
- Successful responses
- File saves and downloads
- Validation results

### Failed Operations

- HTTP error status codes
- Full response bodies from failed API calls
- Exception stack traces
- Retry attempts
- Timeout errors

## Logged Information by Module

### Lyric Generator (Claude API)

**Logged Events:**
- API call attempts with retry count
- Response character count
- Content filter validation results
- Rejection reasons
- Full error details including exception info

**Example Log Entries:**
```
2026-03-04 21:26:54 - backend.lyric_generator - INFO - Calling Claude API (attempt 1/3)
2026-03-04 21:26:55 - backend.lyric_generator - INFO - Claude API call successful, received 512 characters
2026-03-04 21:26:55 - backend.lyric_generator - INFO - Lyrics validated successfully
```

**Error Example:**
```
2026-03-04 21:27:10 - backend.lyric_generator - ERROR - Claude API error (attempt 1/3): 429 Rate limit exceeded
2026-03-04 21:27:10 - backend.lyric_generator - ERROR - Full error details: <full exception repr>
```

### Song Producer (Suno API)

**Logged Events:**
- Song generation submission with genre
- Full API request/response JSON
- Task ID assignment
- Status polling updates
- Audio download progress
- File save locations

**Example Log Entries:**
```
2026-03-04 21:28:00 - backend.song_producer - INFO - Submitting song generation request to Suno API (genre: pop)
2026-03-04 21:28:01 - backend.song_producer - INFO - Suno API response: {"code": 200, "msg": "success", ...}
2026-03-04 21:28:01 - backend.song_producer - INFO - Song generation submitted successfully, task ID: abc123
2026-03-04 21:28:31 - backend.song_producer - INFO - Task abc123 status: PENDING
2026-03-04 21:29:01 - backend.song_producer - INFO - Task abc123 status: SUCCESS
2026-03-04 21:29:01 - backend.song_producer - INFO - Full SUCCESS response: {...}
2026-03-04 21:29:02 - backend.song_producer - INFO - Downloaded 3145728 bytes
2026-03-04 21:29:02 - backend.song_producer - INFO - Audio saved to: static/audio/user_abc1/task123.mp3
```

**Error Example:**
```
2026-03-04 21:30:00 - backend.song_producer - ERROR - Suno API returned status 400
2026-03-04 21:30:00 - backend.song_producer - ERROR - Response body: {"code": 400, "msg": "Invalid parameters"}
```

### Image Generator (Google Gemini API)

**Logged Events:**
- API call attempts with retry count
- Model being used
- Response structure details
- Image data extraction
- File save locations
- Content filter validation

**Example Log Entries:**
```
2026-03-04 21:31:00 - backend.image_generator - INFO - Calling Google Gemini API for image generation (attempt 1/3)
2026-03-04 21:31:01 - backend.image_generator - INFO - Calling Gemini API with model: gemini-2.5-flash-image
2026-03-04 21:31:05 - backend.image_generator - INFO - Gemini API response received
2026-03-04 21:31:05 - backend.image_generator - INFO - Processing response with 1 candidates
2026-03-04 21:31:05 - backend.image_generator - INFO - Found image data with mime type: image/png
2026-03-04 21:31:05 - backend.image_generator - INFO - Image saved to: static/images/user_abc1/song_image_0_1234.png
2026-03-04 21:31:05 - backend.image_generator - INFO - Image validated successfully
```

**Error Example:**
```
2026-03-04 21:32:00 - backend.image_generator - ERROR - Image API error (attempt 1/3): 429 RESOURCE_EXHAUSTED
2026-03-04 21:32:00 - backend.image_generator - ERROR - Full error details: <full exception repr>
```

## Viewing Logs

### Real-time Monitoring

```bash
# Follow the log file in real-time
tail -f logs/workshop.log

# Filter for errors only
tail -f logs/workshop.log | grep ERROR

# Filter for specific module
tail -f logs/workshop.log | grep "backend.song_producer"
```

### Searching Logs

```bash
# Find all errors
grep ERROR logs/workshop.log

# Find errors from last hour
grep "2026-03-04 21:" logs/workshop.log | grep ERROR

# Find specific task ID
grep "task_id_here" logs/workshop.log

# Count errors by type
grep ERROR logs/workshop.log | cut -d'-' -f3 | sort | uniq -c
```

## Log Rotation

For production, consider implementing log rotation to prevent the log file from growing too large:

```python
# Add to logging configuration
from logging.handlers import RotatingFileHandler

handler = RotatingFileHandler(
    'logs/workshop.log',
    maxBytes=10*1024*1024,  # 10MB
    backupCount=5
)
```

## Error Response Details

When an API call fails, the following information is logged:

1. **HTTP Status Code**: The error status returned by the API
2. **Response Body**: Full text of the error response
3. **Exception Type**: The Python exception that was raised
4. **Stack Trace**: Full traceback for debugging
5. **Attempt Number**: Which retry attempt failed
6. **Context**: Request parameters, task IDs, etc.

## Monitoring Recommendations

### Development

- Monitor console output for immediate feedback
- Check `logs/workshop.log` for detailed error information

### Production

- Set up log aggregation (e.g., ELK stack, Splunk, CloudWatch)
- Configure alerts for ERROR and CRITICAL level messages
- Monitor for patterns:
  - Repeated 429 (rate limit) errors
  - Timeout errors
  - Authentication failures
  - Content filter rejections

### Key Metrics to Track

- API call success/failure rates
- Average response times
- Retry attempt frequencies
- Content filter rejection rates
- User-specific error patterns

## Troubleshooting Common Issues

### Claude API Errors

- **429 Rate Limit**: Reduce request frequency or upgrade API tier
- **401 Unauthorized**: Check API key configuration
- **Content Rejected**: Review content filter rules

### Suno API Errors

- **400 Bad Request**: Check payload format and required fields
- **404 Not Found**: Verify API endpoint URLs
- **Task Timeout**: Increase timeout value or check API status

### Gemini API Errors

- **429 Quota Exceeded**: Check API quota limits
- **No Image Data**: Verify response structure in logs
- **Invalid Model**: Confirm model name is correct

## Privacy Considerations

The logs may contain:
- User-generated content (song descriptions, lyrics)
- API responses
- File paths with usernames

Ensure logs are:
- Stored securely
- Access-controlled
- Rotated/archived appropriately
- Compliant with data retention policies
