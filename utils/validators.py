"""
Input validation utilities.
"""

import re

_URL_RE = re.compile(
    r"^https?://"
    r"(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|"
    r"localhost|"
    r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})"
    r"(?::\d+)?"
    r"(?:/?|[/?]\S+)$",
    re.IGNORECASE,
)

# Matches @username or -100xxxxxxxxxx (supergroup/channel id)
_CHANNEL_USERNAME_RE = re.compile(r"^@[a-zA-Z][a-zA-Z0-9_]{3,}$")
_CHANNEL_ID_RE = re.compile(r"^-100\d{7,13}$")


def is_valid_url(url: str) -> bool:
    """Return True if *url* is a syntactically valid HTTP/HTTPS URL."""
    return bool(_URL_RE.match(url.strip()))


def is_valid_channel_input(text: str) -> bool:
    """
    Return True if *text* looks like a Telegram channel identifier:
      • @username  (public channel)
      • -100xxxxxxx  (channel/supergroup ID)
    """
    text = text.strip()
    return bool(_CHANNEL_USERNAME_RE.match(text) or _CHANNEL_ID_RE.match(text))


def parse_channel_input(text: str) -> tuple[str | None, int | None]:
    """
    Parse user input and return (username, channel_id).

    • @username  → ("@username", None)
    • -100xxxxxx → (None, int)
    """
    text = text.strip()
    if _CHANNEL_USERNAME_RE.match(text):
        return text, None
    if _CHANNEL_ID_RE.match(text):
        return None, int(text)
    return None, None
