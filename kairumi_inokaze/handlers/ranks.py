"""Handler for /ranks shop."""

import logging
from telegram import Update
from telegram.ext import ContextTypes

from kairumi_inokaze import database as db
from kairumi_inokaze.middlewares import check_anti_spam
from kairumi_inokaze.utils.keyboards import ranks_keyboard
from kairumi_inokaze.utils.messages import esc

logger = logging.getLogger(__name__)


async def ranks_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/ranks — show rank shop."""
    if update.message is None:
        return

    user = update.effective_user
    if await check_anti_spam(user.id):
        return

    if update.effective_chat.type in ("group", "supergroup"):
        db.add_group(update.effective_chat.id)

    ranks = db.get_ranks_shop()
    await update.message.reply_text(
        "⭐ <b>Rank Shop</b>\n━━━━━━━━━━━━━━━━━━━━\nUpgrade your status:",
        parse_mode="HTML",
        reply_markup=ranks_keyboard(ranks),
    )


async def ranks_page_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle rank shop pagination."""
    query = update.callback_query
    await query.answer()
    page = int(query.data.split(":")[1])
    ranks = db.get_ranks_shop()
    try:
        await query.edit_message_reply_markup(reply_markup=ranks_keyboard(ranks, page))
    except Exception:
        pass


async def rank_buy_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle rank purchase."""
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    username = update.effective_user.username or update.effective_user.first_name or str(user_id)

    rank_idx = int(query.data.split(":")[1])
    ranks = db.get_ranks_shop()

    if rank_idx >= len(ranks):
        await query.edit_message_text("❌ Invalid rank.")
        return

    rank = ranks[rank_idx]
    db_user = db.get_or_create_user(user_id, username)

    if db_user.get("balance", 0) < rank["price"]:
        await query.edit_message_text(f"❌ You need {rank['price']:,} coins. You have {db_user.get('balance', 0):,}.")
        return

    db_user["balance"] -= rank["price"]
    db_user["rank"] = rank["name"]
    db.save_user(db_user)

    await query.edit_message_text(
        f"⭐ <b>Rank upgraded to {esc(rank['name'])}!</b>\n💰 Remaining balance: <b>{db_user['balance']:,}</b>",
        parse_mode="HTML",
    )
    logger.info(f"User {user_id} bought rank {rank['name']} for {rank['price']}")
