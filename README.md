# Localr

A travel-idea app: pick a city and a mood, swipe through ten AI-generated suggestions, save the ones you like, and turn them into a day-by-day itinerary.

> **Honesty note.** Suggestions come from a large language model (Llama 3.3 via Groq), not from Reddit, reviews or any scraped source. They can be wrong or out of date, and the app says so in the UI. Earlier versions of this project claimed to read Reddit and showed "real quotes" and a "Local Score"; that was not true, and it has been removed. Reddit's official API is approval-gated and its public access is being wound down in 2026, so it is not a viable source for a new hobby project. This is a fun project idea.

## Features

- City + mood search (mood is restricted to a fixed list)
- Swipe cards: right to save, left to skip, with undo
- Place detail panel with photos (Unsplash) and AI-generated practical tips
- Saved places on a map (OpenStreetMap / Leaflet)
- Itinerary builder
- Accounts with hashed passwords

## Tech stack

Python, Flask, Flask-Login, Flask-SQLAlchemy (SQLite), Groq API (LLM), Unsplash API, Nominatim (geocoding), vanilla JavaScript.

## Run it locally

```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # then fill in the values
# generate a SECRET_KEY:  python -c "import secrets; print(secrets.token_hex(32))"
# for plain-http local dev add SESSION_COOKIE_SECURE=0 to .env
flask --app backend/main run
```

The app refuses to start without a `SECRET_KEY`.

## Tests

```bash
python -m unittest tests.test_security -v
```

## Security

See [SECURITY.md](SECURITY.md) for what was found, what was fixed, and what is still open.
