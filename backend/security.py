"""Security helpers for Localr.

Kept separate from main.py so they can be unit-tested without a database.
Everything here uses only the standard library.
"""
import hmac
import json
import re
import secrets
import time
from collections import defaultdict, deque

# ---------------------------------------------------------------- validation

ALLOWED_MOODS = {"Outdoor", "Food & Drink", "Culture", "Nightlife", "Budget"}

USERNAME_RE = re.compile(r"^[A-Za-z0-9_.-]{3,32}$")
# Letters (incl. accents), spaces, apostrophes, hyphens, dots, commas. No < > { } etc.
CITY_RE = re.compile(r"^[^\W\d_][\w\s'.,-]{0,79}$", re.UNICODE)

MIN_PASSWORD_LEN = 10
MAX_PASSWORD_LEN = 128  # also stops huge inputs being fed to the hash function


def valid_username(value):
    return bool(value) and bool(USERNAME_RE.fullmatch(value))


def password_problem(value):
    """Return a human-readable problem with the password, or None if OK."""
    if not value or len(value) < MIN_PASSWORD_LEN:
        return f"Password must be at least {MIN_PASSWORD_LEN} characters."
    if len(value) > MAX_PASSWORD_LEN:
        return f"Password must be at most {MAX_PASSWORD_LEN} characters."
    if value.lower() in {"password123", "1234567890", "qwertyuiop"}:
        return "That password is too common."
    return None


def clean_city(value):
    """Return a stripped city name, or None if it looks wrong."""
    if not value:
        return None
    value = value.strip()
    if len(value) > 80 or not CITY_RE.fullmatch(value):
        return None
    return value


def clean_mood(value):
    return value if value in ALLOWED_MOODS else None


def clip(value, limit):
    """Make sure client-supplied text can't be arbitrarily large."""
    return (value or "").strip()[:limit]


# ------------------------------------------------------------- rate limiting

class RateLimiter:
    """Tiny in-memory sliding-window limiter.

    LIMITATION: state lives in one process's memory. It resets on restart and
    is not shared between workers. For production use Flask-Limiter + Redis.
    """

    def __init__(self):
        self._hits = defaultdict(deque)

    def allow(self, key, limit, window_seconds, now=None):
        now = time.monotonic() if now is None else now
        q = self._hits[key]
        while q and q[0] <= now - window_seconds:
            q.popleft()
        if len(q) >= limit:
            return False
        q.append(now)
        return True

    def reset(self):
        self._hits.clear()


# ------------------------------------------------------------------- CSRF

def get_or_create_csrf_token(session):
    token = session.get("_csrf")
    if not token:
        token = secrets.token_urlsafe(32)
        session["_csrf"] = token
    return token


def csrf_ok(session, submitted):
    expected = session.get("_csrf")
    if not expected or not submitted:
        return False
    return hmac.compare_digest(expected, submitted)


# ------------------------------------------- LLM output is untrusted input

def parse_json_loose(raw):
    """Parse JSON from an LLM reply, tolerating ```json fences. None on failure."""
    if not isinstance(raw, str):
        return None
    text = raw.strip()
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text)
    try:
        return json.loads(text)
    except (json.JSONDecodeError, ValueError):
        return None


def _str(value, limit):
    return value.strip()[:limit] if isinstance(value, str) else ""


def sanitize_recommendations(data, max_items=10):
    """Keep only well-formed items; coerce every field to a bounded string."""
    out = []
    if not isinstance(data, list):
        return out
    for item in data[:max_items]:
        if not isinstance(item, dict):
            continue
        name = _str(item.get("name"), 120)
        summary = _str(item.get("summary"), 300)
        if not name or not summary:
            continue
        out.append({"name": name, "summary": summary, "tip": _str(item.get("tip"), 200)})
    return out


def sanitize_details(data, fallback_name):
    if not isinstance(data, dict):
        data = {}
    tips = data.get("tips")
    tips = [_str(t, 160) for t in tips if isinstance(t, str)][:3] if isinstance(tips, list) else []
    return {
        "name": _str(data.get("name"), 120) or fallback_name,
        "description": _str(data.get("description"), 500) or "No details available.",
        "price": _str(data.get("price"), 40) or "Unknown",
        "location": _str(data.get("location"), 160) or "Unknown",
        "hours": _str(data.get("hours"), 120) or "Check locally",
        "tips": [t for t in tips if t],
    }


def sanitize_itinerary(data, max_days=14):
    out = []
    if not isinstance(data, list):
        return out
    for i, day in enumerate(data[:max_days], start=1):
        if not isinstance(day, dict):
            continue
        places = day.get("places")
        places = [_str(p, 120) for p in places if isinstance(p, str)][:12] if isinstance(places, list) else []
        out.append({
            "day": i,
            "title": _str(day.get("title"), 80) or f"Day {i}",
            "places": [p for p in places if p],
            "tip": _str(day.get("tip"), 200),
        })
    return out


def safe_https_url(url):
    """Only allow plain https URLs (blocks javascript: and data: links)."""
    if isinstance(url, str) and url.startswith("https://") and len(url) < 500:
        return url
    return ""
