# AI Song Workshop — Setup Guide

A complete guide to deploy the AI Song Workshop on a fresh EC2 instance with HTTPS.

---

## Prerequisites

- An AWS EC2 instance (Amazon Linux 2023 recommended, t3.micro or larger)
- A domain name pointing to your EC2 instance's public IP (A record)
- AWS Security Group allowing inbound ports: 22 (SSH), 80 (HTTP), 443 (HTTPS)
- API keys for:
  - [Anthropic](https://console.anthropic.com/) — for lyric generation (Claude)
  - [Suno API](https://suno.com/) — for song generation
  - [Google AI Studio](https://aistudio.google.com/apikey) — for image generation and photo transformations (Gemini)

---

## Step 1: Initial Server Setup

SSH into your EC2 instance:

```bash
ssh -i your-key.pem ec2-user@YOUR_EC2_HOST
```

Install system dependencies:

```bash
sudo yum update -y
sudo yum install -y python3 python3-pip nginx certbot python3-certbot-nginx
```

---

## Step 2: Deploy Application Files

From your local machine, use the deploy script or rsync manually:

```bash
rsync -avz --progress \
    --exclude 'venv/' \
    --exclude '__pycache__/' \
    --exclude '.env' \
    --exclude 'data/' \
    --exclude 'logs/*.log' \
    -e "ssh -i your-key.pem" \
    ai-song-workshop/ ec2-user@YOUR_EC2_HOST:~/ai-song-workshop/
```

---

## Step 3: Configure the Application

On the server:

```bash
cd ~/ai-song-workshop

# Create virtual environment
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Create required directories
mkdir -p logs data/callbacks static/audio static/images static/photos

# Create .env from example
cp .env.example .env
nano .env
```

Fill in your `.env` with real values:

```
ANTHROPIC_API_KEY=sk-ant-...
SUNO_API_KEY=your_suno_key
GOOGLE_API_KEY=AIza...
AUTH_USERS=student:yourpassword,admin:youradminpassword
ADMIN_USERNAME=admin
CALLBACK_URL=https://YOUR_DOMAIN/api/suno/callback
CLASS_NAME=Your Class Name
HOST=localhost
PORT=5000
FLASK_ENV=production
FLASK_DEBUG=False
```

---

## Step 4: Set Up systemd Service

```bash
sudo cp ~/ai-song-workshop/workshop.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable workshop
sudo systemctl start workshop
```

Verify it's running:

```bash
sudo systemctl status workshop
curl http://localhost:5000  # Should return HTML
```

---

## Step 5: Configure Nginx (HTTP only, temporarily)

Create a temporary HTTP-only config for Certbot verification:

```bash
sudo tee /etc/nginx/conf.d/workshop.conf << 'EOF'
server {
    listen 80;
    server_name YOUR_DOMAIN;

    location / {
        proxy_pass http://localhost:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_connect_timeout 300;
        proxy_send_timeout 300;
        proxy_read_timeout 300;
    }
    client_max_body_size 10M;
}
EOF
```

Replace `YOUR_DOMAIN` with your actual domain, then:

```bash
sudo nginx -t
sudo systemctl start nginx
sudo systemctl enable nginx
```

---

## Step 6: Obtain SSL Certificate with Certbot

```bash
sudo certbot --nginx -d YOUR_DOMAIN
```

Certbot will:
1. Verify domain ownership via HTTP challenge
2. Obtain a Let's Encrypt certificate
3. Automatically update the nginx config to add HTTPS

Verify auto-renewal:

```bash
sudo certbot renew --dry-run
```

Enable the renewal timer:

```bash
sudo systemctl enable certbot-renew.timer
sudo systemctl start certbot-renew.timer
```

---

## Step 7: Verify Everything Works

```bash
# HTTPS should work
curl -I https://YOUR_DOMAIN

# HTTP should redirect to HTTPS
curl -I http://YOUR_DOMAIN

# Check the service
sudo systemctl status workshop

# Check logs if something is wrong
sudo journalctl -u workshop -f
```

Open `https://YOUR_DOMAIN` in a browser. You should see the login prompt.

---

## Features

### Liedjesmaker (Song Maker)
Kids describe a song idea, pick a genre, and the app generates lyrics (Claude AI)
and a full song (Suno AI) with album art (Gemini AI).

### Foto Fun (Photo Transformation)
Kids take a webcam photo and transform it into 17 artistic styles (Gemini AI):
superhero, Disney princess/prince, Minecraft, LEGO, astronaut, pirate, wizard,
dinosaur park, mermaid, video game hero, ice kingdom, and more.

Requires HTTPS (webcam API needs secure context).

### Admin Features
The admin user (configured via `ADMIN_USERNAME`) can see:
- All songs from all users (`/allsongs`)
- All photo transformations from all users (`/allphotos`)

---

## Troubleshooting

### "Camera not working"
The webcam API requires HTTPS. Make sure SSL is properly configured.

### "Transformatie mislukt"
Check that `GOOGLE_API_KEY` is set and the Gemini API is accessible.
Check logs: `sudo journalctl -u workshop -f`

### Service won't start
```bash
sudo journalctl -u workshop --no-pager -n 50
```
Common issues: missing `.env`, missing Python packages, wrong permissions.

### Certbot fails
Make sure your domain's DNS A record points to the EC2 public IP,
and port 80 is open in the AWS Security Group.
