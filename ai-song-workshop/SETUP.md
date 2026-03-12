# AI Song Workshop - Setup Guide

## Quick Start (Local Development)

1. **Install Python dependencies**:
```bash
cd ai-song-workshop
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

2. **Configure environment variables**:
```bash
cp .env.example .env
# Edit .env and add your API keys
```

3. **Add a logo** (optional):
```bash
# Place your school logo at static/logo.png
# Or update LOGO_PATH in .env
```

4. **Run the application**:
```bash
python app.py
```

5. **Open in browser**:
```
http://localhost:5000
```

## Configuration

Edit `.env` file:

```env
# Required API Keys
ANTHROPIC_API_KEY=your_anthropic_key_here
SUNO_API_KEY=your_suno_key_here

# Optional
GOOGLE_API_KEY=your_google_key_here

# Branding
LOGO_PATH=static/logo.png
CLASS_NAME=Groep 5 en 6

# Session
SESSION_TIMEOUT_HOURS=8
SESSION_STORAGE_PATH=/tmp/workshop_sessions
```

## Deployment to EC2

See `deployment-config.md` for detailed EC2 deployment instructions.

### Quick EC2 Deployment:

1. **Transfer files to EC2**:
```bash
scp -i suno4kids.pem -r ai-song-workshop ubuntu@ec2-18-196-253-58.eu-central-1.compute.amazonaws.com:~/
```

2. **SSH into EC2**:
```bash
ssh -i suno4kids.pem ubuntu@ec2-18-196-253-58.eu-central-1.compute.amazonaws.com
```

3. **Install dependencies**:
```bash
cd ai-song-workshop
sudo apt update
sudo apt install python3-pip python3-venv nginx -y
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

4. **Configure environment**:
```bash
nano .env
# Add your API keys
```

5. **Run application**:
```bash
python app.py
```

## Features

- ✅ Dutch language interface
- ✅ Profile creation/selection
- ✅ Multiple song projects per profile
- ✅ AI lyric generation (Claude)
- ✅ Song generation (Suno.ai)
- ✅ Optional image generation
- ✅ Content filtering for child safety
- ✅ Configurable school branding

## Troubleshooting

### API Keys Not Working
- Check that keys are correctly set in `.env`
- Ensure no extra spaces or quotes
- Restart the application after changing `.env`

### Port Already in Use
- Change PORT in `.env` to a different number (e.g., 5001)

### Session Data Not Persisting
- Check SESSION_STORAGE_PATH is writable
- Default is `/tmp/workshop_sessions`

## Support

For issues or questions, check the logs in `logs/workshop.log`
