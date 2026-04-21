"""Handler for /collection."""

import logging
from telegram import Update
from telegram.ext import ContextTypes

from kairumi_inokaze import database as db
from kairumi_inokaze.middlewares import check_anti_spam
from kairumi_inokaze.utils.keyboards import collection_keyboard
from kairumi_inokaze.utils.messages import esc

logger = logging.getLogger(__name__)


async def collection_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/collection — show user's collection."""
    if update.message is None:
        return

    user = update.effective_user
    if await check_anti_spam(user.id):
        return

    if update.effective_chat.type in ("group", "supergroup"):
        db.add_group(update.effective_chat.id)

    await update.message.reply_text(
        "🎒 <b>Your Collection</b>\n━━━━━━━━━━━━━━━━━━\nWhat would you like to view?",
        parse_mode="HTML",
        reply_markup=collection_keyboard(),
    )


async def collection_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle collection menu selection."""
    query = update.callback_query
    await query.answer()

    action = query.data.split(":")[1]
    user_id = update.effective_user.id
    username = update.effective_user.username or update.effective_user.first_name or str(user_id)
    db_user = db.get_or_create_user(user_id, username)

    if action == "inventory":
        inventory = db_user.get("inventory", [])
        if not inventory:
            await query.edit_message_text("📦 Your inventory is empty.")
            return
        lines = ["📦 <b>Inventory</b>\n"]
        for item in inventory:
            lines.append(f"• {esc(str(item))}")
        await query.edit_message_text("\n".join(lines), parse_mode="HTML")

    elif action == "cars":
        cars = db_user.get("cars", [])
        if not cars:
            await query.edit_message_text("🚗 You don't own any cars yet.")
            return
        lines = ["🚗 <b>My Cars</b>\n"]
        for car in cars:
            lines.append(f"🚗 <b>{esc(car.get('name', 'Car'))}</b> — Prestige: {car.get('prestige', '?')}/10")
        await query.edit_message_text("\n".join(lines), parse_mode="HTML")

    elif action == "buildings":
        buildings = db_user.get("buildings", [])
        if not buildings:
            await query.edit_message_text("🏠 You don't own any buildings yet.")
            return
        lines = ["🏠 <b>My Buildings</b>\n"]
        for b in buildings:
            lines.append(f"🏢 <b>{esc(b.get('name', 'Building'))}</b> — Revenue: {b.get('revenue', 0):,}/week")
        await query.edit_message_text("\n".join(lines), parse_mode="HTML")
