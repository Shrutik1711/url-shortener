import random
import re
import string
from datetime import datetime, timezone
from urllib.parse import urlparse

ALIAS_RE = re.compile(r"[A-Za-z0-9_-]{3,32}")
RESERVED_ALIASES = {"links", "ping"}  


def utcnow():
    """Current UTC time as a naive datetime (that is how we store it)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def iso(dt):
    """Naive-UTC datetime -> '2026-10-26T09:00:00Z' (or None)."""
    return dt.isoformat() + "Z" if dt else None


def is_valid_url(url):
    if not isinstance(url, str) or not url or len(url) > 2048:
        return False
    if any(ch.isspace() for ch in url):
        return False
    try:
        parsed = urlparse(url)
        parsed.port 
    except ValueError:
        return False
    return parsed.scheme in ("http", "https") and bool(parsed.hostname)


def is_valid_alias(alias):
    return (
        isinstance(alias, str)
        and ALIAS_RE.fullmatch(alias) is not None
        and alias.lower() not in RESERVED_ALIASES
    )


def generate_short_code(length=6):
    characters = string.ascii_letters + string.digits
    return "".join(random.choice(characters) for _ in range(length))


def parse_expiry(value):
    """ISO 8601 string -> naive UTC datetime. Raises ValueError if invalid."""
    if not isinstance(value, str):
        raise ValueError("expires_at must be a string")
    dt = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    if dt.tzinfo is not None: 
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt