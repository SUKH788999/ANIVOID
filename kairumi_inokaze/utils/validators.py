"""Input validation helpers."""

from typing import Optional


def parse_positive_int(value: str) -> Optional[int]:
    """Parse a positive integer from string. Returns None on failure."""
    try:
        n = int(value.strip())
        if n <= 0:
            return None
        return n
    except (ValueError, AttributeError):
        return None


def is_valid_pin(pin: str) -> bool:
    """Check if PIN is exactly 4 digits."""
    return pin.isdigit() and len(pin) == 4


def sanitize_username(username: Optional[str]) -> str:
    """Return a safe display username."""
    if not username:
        return "Unknown"
    return username.lstrip("@")
