"""Cooldown tracker helpers."""

import time
from typing import Optional
from kairumi_inokaze import database as db


COOLDOWN_SECONDS = {
    "claim": 86400,
    "rob": 3600,
    "kill": 21600,
}


def check_cooldown(user_id: int, cmd: str) -> Optional[float]:
    """Return seconds remaining on cooldown, or None if not on cooldown."""
    last = db.get_cooldown(user_id, cmd)
    if last is None:
        return None
    duration = COOLDOWN_SECONDS.get(cmd, 0)
    elapsed = time.time() - last
    remaining = duration - elapsed
    return remaining if remaining > 0 else None


def apply_cooldown(user_id: int, cmd: str) -> None:
    """Set cooldown for user/command to now."""
    db.set_cooldown(user_id, cmd)


def format_cooldown(seconds: float) -> str:
    """Format seconds into HH:MM:SS string."""
    s = int(seconds)
    h = s // 3600
    m = (s % 3600) // 60
    sec = s % 60
    return f"{h}h {m}m {sec}s"
