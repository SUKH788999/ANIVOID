"""Handler for /claim daily reward."""

import logging
import time
from telegram import Update
from telegram.ext import ContextTypes

from kairumi_inokaze import database as db
from kairumi_inokaze.config import DAILY_CLAIM_AMOUNT, DAILY_CLAIM_COOLDOWN
from kairumi_inokaze.middlewares import check_anti_spam
from kairumi_inokaze.utils.messages import claim_cooldown_msg, claim_success_msg

logger = logging.getLogger(__name__)


async def claim_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /claim — gives daily 800 coins if eligible."""
    if update.message is None:
        return

    user = update.effective_user
    user_id = user.id
    username = user.username or user.first_name or str(user_id)

    if await check_anti_spam(user_id):
        return

    if update.effective_chat.type in ("group", "supergroup"):
        db.add_group(update.effective_chat.id)

    db_user = db.get_or_create_user(user_id, username)

    if db_user.get("banned"):
        await update.message.reply_text("🚫 You are banned.")
        return

    now = time.time()
    last_claim = db_user.get("last_claim")

    if last_claim is not None:
        elapsed = now - last_claim
        if elapsed < DAILY_CLAIM_COOLDOWN:
            remaining = DAILY_CLAIM_COOLDOWN - elapsed
            await update.message.reply_text(claim_cooldown_msg(remaining), parse_mode="HTML")
            return

    db_user["balance"] = db_user.get("balance", 0) + DAILY_CLAIM_AMOUNT
    db_user["last_claim"] = now
    db.save_user(db_user)

    await update.message.reply_text(
        claim_success_msg(DAILY_CLAIM_AMOUNT, db_user["balance"]),
        parse_mode="HTML",
    )
    logger.info(f"User {user_id} claimed daily reward: +{DAILY_CLAIM_AMOUNT}")
