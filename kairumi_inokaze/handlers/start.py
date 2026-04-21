"""Handler for /start, force-join verification."""

import logging
from telegram import Update
from telegram.ext import ContextTypes

from kairumi_inokaze import database as db
from kairumi_inokaze.utils.keyboards import force_join_keyboard, main_menu_keyboard, verify_button
from kairumi_inokaze.utils.messages import welcome_message, esc
from kairumi_inokaze.middlewares import check_force_join, check_anti_spam

logger = logging.getLogger(__name__)


async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command — creates user, checks force-join, shows welcome."""
    if update.message is None:
        return

    user = update.effective_user
    user_id = user.id
    username = user.username or user.first_name or str(user_id)

    if await check_anti_spam(user_id):
        return

    if update.effective_chat and update.effective_chat.type in ("group", "supergroup"):
        db.add_group(update.effective_chat.id)

    db_user = db.get_or_create_user(user_id, username)

    if db_user.get("banned"):
        await update.message.reply_text("🚫 You are banned from using this bot.")
        return

    joined = await check_force_join(update, context)
    if not joined:
        await update.message.reply_text(
            "⚠️ You must join our group to use Kairumi Inokaze!\n\nClick <b>JOIN GROUP</b>, then click <b>VERIFY</b>.",
            parse_mode="HTML",
            reply_markup=force_join_keyboard(),
        )
        return

    msg = welcome_message(username, db_user)
    await update.message.reply_text(msg, parse_mode="HTML", reply_markup=main_menu_keyboard())
    logger.info(f"User {user_id} (@{username}) started the bot")


async def verify_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle VERIFY button — re-checks channel membership."""
    query = update.callback_query
    await query.answer()

    user = update.effective_user
    user_id = user.id
    username = user.username or user.first_name or str(user_id)

    joined = await check_force_join(update, context)
    if not joined:
        await query.edit_message_text(
            "⚠️ You haven't joined yet! Please join the group first, then click VERIFY.",
            parse_mode="HTML",
            reply_markup=verify_button(),
        )
        return

    db_user = db.get_or_create_user(user_id, username)
    msg = welcome_message(username, db_user)
    await query.edit_message_text(msg, parse_mode="HTML")
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="✅ Verified! Welcome to Kairumi Inokaze!",
        reply_markup=main_menu_keyboard(),
    )
    logger.info(f"User {user_id} verified join")
