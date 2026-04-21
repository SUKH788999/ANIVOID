"""Handler for /bal command."""

import logging
from telegram import Update
from telegram.ext import ContextTypes

from kairumi_inokaze import database as db
from kairumi_inokaze.middlewares import check_anti_spam
from kairumi_inokaze.utils.messages import balance_card

logger = logging.getLogger(__name__)


async def balance_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show user's full profile card."""
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

    card = balance_card(db_user)
    await update.message.reply_text(f"<pre>{card}</pre>", parse_mode="HTML")
    logger.info(f"User {user_id} checked balance: {db_user.get('balance', 0)}")
