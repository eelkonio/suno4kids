# AI Song Workshop Website

Een educatief platform voor kinderen van 9-12 jaar om liedjes te maken met AI-ondersteuning.

## Overzicht

Dit systeem integreert met:
- Claude API (Anthropic) voor het genereren van songteksten
- Suno.ai API voor muziekproductie
- Google Image API (optioneel) voor artwork

## Installatie

1. Maak een virtuele omgeving aan:
```bash
python3 -m venv venv
source venv/bin/activate  # Op Windows: venv\Scripts\activate
```

2. Installeer dependencies:
```bash
pip install -r requirements.txt
```

3. Configureer omgevingsvariabelen:
Maak een `.env` bestand aan met:
```
ANTHROPIC_API_KEY=your_key_here
SUNO_API_KEY=your_key_here
GOOGLE_API_KEY=your_key_here
LOGO_PATH=static/logo.png
CLASS_NAME=Groep 5 en 6
```

4. Start de applicatie:
```bash
python app.py
```

## Projectstructuur

```
ai-song-workshop/
├── backend/           # Backend componenten
├── frontend/          # Frontend templates en routes
├── static/            # Statische bestanden (CSS, JS, afbeeldingen)
├── templates/         # Jinja2 templates
├── tests/             # Unit en property tests
├── config.py          # Configuratie
├── app.py             # Hoofdapplicatie
└── requirements.txt   # Python dependencies
```

## Deployment

Zie `deployment-config.md` voor AWS EC2 deployment instructies.
