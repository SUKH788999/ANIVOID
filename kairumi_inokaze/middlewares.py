"""Anti-spam, force-join, cooldown checks middleware."""

import logging
import time
from datetime import datetime, timezone
from typing import Optional

from telegram import Update
from telegram.ext import ContextTypes

from kairumi_inokaze import database as db
from kairumi_inokaze.config import ADMIN_IDS, FORCE_JOIN_ID

logger = logging.getLogger(__name__)

SPAM_WINDOW = 3.0
SPAM_MAX_MSGS = 5
SPAM_MUTE_DURATION = 30.0


async def check_anti_spam(user_id: int) -> bool:
    """Return True if user is spamming (should be ignored). Tracks in DB."""
    if user_id in ADMIN_IDS:
        return False

    data = db.get_spam_data(user_id)
    now = time.time()

    muted_until = data.get("muted_until")
    if muted_until and now < muted_until:
        return True

    timestamps = data.get("timestamps", [])
    timestamps = [t for t in timestamps if now - t < SPAM_WINDOW]
    timestamps.append(now)

    if len(timestamps) > SPAM_MAX_MSGS:
        data["muted_until"] = now + SPAM_MUTE_DURATION
        data["timestamps"] = timestamps
        db.save_spam_data(user_id, data)
        logger.warning(f"User {user_id} muted for spam")
        return True

    data["timestamps"] = timestamps
    data["muted_until"] = None
    db.save_spam_data(user_id, data)
    return False


async def check_force_join(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Return True if user has joined the required channel."""
    user_id = update.effective_user.id
    try:
        member = await context.bot.get_chat_member(FORCE_JOIN_ID, user_id)
        return member.status not in ("left", "kicked", "banned")
    except Exception:
        return True


async def check_dead_status(user_id: int) -> bool:
    """Return True if user is currently dead."""
    user = db.get_user(user_id)
    if user is None:
        return False
    if not user.get("dead_status", False):
        return False
    dead_until = user.get("dead_until")
    if dead_until is None:
        return True
    try:
        dt = datetime.fromisoformat(dead_until)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        if datetime.now(timezone.utc) >= dt:
            user["dead_status"] = False
            user["dead_until"] = None
            db.save_user(user)
            return False
        return True
    except Exception:
        return False


async def check_protected(user_id: int) -> bool:
    """Return True if user is currently protected."""
    user = db.get_user(user_id)
    if user is None:
        return False
    expiry = user.get("protect_expiry")
    if not expiry:
        return False
    try:
        dt = datetime.fromisoformat(expiry)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return datetime.now(timezone.utc) < dt
    except Exception:
        return False


def is_admin(user_id: int) -> bool:
    """Check if user is an admin."""
    admins = db.get_all_users()
    admin_list = db._db_get("admins:list") or ADMIN_IDS
    return user_id in admin_list


def require_admin(func):
    """Decorator to restrict command to admins only."""
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        if not is_admin(user_id):
            await update.message.reply_text("🚫 Admin only command.")
            return
        return await func(update, context)
    wrapper.__name__ = func.__name__
    return wrapper
