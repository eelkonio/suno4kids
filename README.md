# AI Song Workshop 🎵📸

An interactive web application for children to create AI-generated songs and transform
their photos into fun artistic styles. Built with Flask, Claude AI, Suno AI, and Google Gemini.

## What It Does

### 🎵 Liedjesmaker (Song Maker)
Kids describe a song idea, pick a genre, and the app generates:
- Lyrics using Claude AI (Anthropic)
- A full song using Suno AI
- Album artwork using Gemini AI (Google)

### 📸 Foto Fun (Photo Transformation)
Kids take a webcam selfie and transform it into 17 artistic styles:

| Style | Description |
|-------|-------------|
| 🎨 Old Painting | Rembrandt-style 1700s portrait |
| 🚀 Futuristic City | Flying cars and neon skyscrapers |
| 🎤 Pop Star | Concert stage with thousands of fans |
| 🦸 Superhero | Epic action movie scene |
| ⚔️ Demon Hunters | Korean anime/manhwa style |
| 👑 Disney Princess | Ball gown, tiara, magical castle |
| 🤴 Disney Prince | Royal outfit, heroic pose |
| 🍌 Minion Mayhem | Surrounded by Minions |
| ⛏️ Minecraft | Blocky pixelated world |
| 🧱 LEGO | Classic LEGO Minifigure |
| 🚀 Astronaut | Space suit on Mars |
| 🏴‍☠️ Pirate | Treasure and high-seas adventure |
| 🧙 Wizard | Hogwarts-style magic school |
| 🦕 Dinosaur Park | Friendly prehistoric adventure |
| 🧜 Mermaid | Underwater coral reef scene |
| 🎮 Video Game Hero | Retro or modern game style |
| ❄️ Ice Kingdom | Frozen-inspired ice palace |

## Tech Stack

- Python / Flask
- Anthropic Claude API (lyrics)
- Suno API (music generation)
- Google Gemini API (images and photo transformation)
- Nginx + Let's Encrypt (HTTPS, required for webcam)
- Vanilla JavaScript (no frontend framework)

## Quick Start

### Local Development

```bash
cd ai-song-workshop
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your API keys
python app.py
```

Open `http://localhost:5000` (photo feature needs HTTPS to access webcam).

### Production Deployment

See [SETUP_GUIDE.md](SETUP_GUIDE.md) for full EC2 + HTTPS deployment instructions.

## Configuration

Copy `.env.example` to `.env` and configure:

| Variable | Required | Description |
|----------|----------|-------------|
| `ANTHROPIC_API_KEY` | Yes | Claude API key for lyric generation |
| `SUNO_API_KEY` | Yes | Suno API key for song generation |
| `GOOGLE_API_KEY` | Yes | Gemini API key for images and photo transforms |
| `AUTH_USERS` | Yes | HTTP Basic Auth users (`user:pass,user2:pass2`) |
| `ADMIN_USERNAME` | No | Username with admin access (default: `admin`) |
| `CALLBACK_URL` | No | Suno callback URL for async song generation |
| `CLASS_NAME` | No | Display name in the header |
| `HOST` | No | Bind address (default: `localhost`) |
| `PORT` | No | Bind port (default: `5000`) |

## Project Structure

```
ai-song-workshop/
├── app.py                  # Flask application entry point
├── config.py               # Configuration loader
├── backend/
│   ├── lyric_generator.py  # Claude AI lyrics
│   ├── song_producer.py    # Suno AI songs
│   ├── image_generator.py  # Gemini AI images
│   ├── photo_transformer.py # Photo transformation (17 styles)
│   ├── profile_manager.py  # User profiles
│   ├── project_manager.py  # Song projects
│   ├── session_manager.py  # Session storage
│   ├── callback_manager.py # Suno async callbacks
│   ├── content_filter.py   # Content safety
│   └── error_handling.py   # Error messages (Dutch)
├── frontend/
│   └── routes.py           # All Flask routes
├── templates/              # Jinja2 HTML templates
├── static/
│   ├── css/
│   ├── js/
│   └── home/
├── .env.example            # Environment template
├── requirements.txt
└── workshop.service        # systemd service file
```

## License

MIT
