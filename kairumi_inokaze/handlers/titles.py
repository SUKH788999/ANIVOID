"""Handler for /titles shop."""

import logging
from telegram import Update
from telegram.ext import ContextTypes

from kairumi_inokaze import database as db
from kairumi_inokaze.middlewares import check_anti_spam
from kairumi_inokaze.utils.keyboards import titles_keyboard
from kairumi_inokaze.utils.messages import esc

logger = logging.getLogger(__name__)


async def titles_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/titles — show title shop."""
    if update.message is None:
        return

    user = update.effective_user
    if await check_anti_spam(user.id):
        return

    if update.effective_chat.type in ("group", "supergroup"):
        db.add_group(update.effective_chat.id)

    titles = db.get_titles_shop()
    await update.message.reply_text(
        "🎖 <b>Title Shop</b>\n━━━━━━━━━━━━━━━━━━━━\nChoose your title:",
        parse_mode="HTML",
        reply_markup=titles_keyboard(titles),
    )


async def titles_page_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle titles pagination."""
    query = update.callback_query
    await query.answer()
    page = int(query.data.split(":")[1])
    titles = db.get_titles_shop()
    try:
        await query.edit_message_reply_markup(reply_markup=titles_keyboard(titles, page))
    except Exception:
        pass


async def title_buy_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle title purchase."""
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    username = update.effective_user.username or update.effective_user.first_name or str(user_id)

    title_idx = int(query.data.split(":")[1])
    titles = db.get_titles_shop()

    if title_idx >= len(titles):
        await query.edit_message_text("❌ Invalid title.")
        return

    title = titles[title_idx]
    db_user = db.get_or_create_user(user_id, username)

    if db_user.get("balance", 0) < title["price"]:
        await query.edit_message_text(f"❌ You need {title['price']:,} coins.")
        return

    db_user["balance"] -= title["price"]
    db_user["title"] = title["name"]
    db.save_user(db_user)

    await query.edit_message_text(
        f"🎖 <b>Title '{esc(title['name'])}' unlocked!</b>\n💰 Remaining balance: <b>{db_user['balance']:,}</b>",
        parse_mode="HTML",
    )
    logger.info(f"User {user_id} bought title {title['name']}")
