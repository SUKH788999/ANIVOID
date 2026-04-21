"""Handler for /buildings — real estate."""

import logging
from telegram import Update
from telegram.ext import ContextTypes

from kairumi_inokaze import database as db
from kairumi_inokaze.middlewares import check_anti_spam
from kairumi_inokaze.utils.keyboards import buildings_keyboard
from kairumi_inokaze.utils.messages import esc

logger = logging.getLogger(__name__)


async def buildings_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/buildings — real estate menu."""
    if update.message is None:
        return

    user = update.effective_user
    if await check_anti_spam(user.id):
        return

    if update.effective_chat.type in ("group", "supergroup"):
        db.add_group(update.effective_chat.id)

    await update.message.reply_text(
        "🏗 <b>Real Estate</b>\n━━━━━━━━━━━━━━\nBrowse and invest in buildings:",
        parse_mode="HTML",
        reply_markup=buildings_keyboard(),
    )


async def buildings_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle building menu selection."""
    query = update.callback_query
    await query.answer()

    action = query.data.split(":")[1]
    user_id = update.effective_user.id
    username = update.effective_user.username or update.effective_user.first_name or str(user_id)

    if action == "browse":
        buildings = db.get_buildings_shop()
        if not buildings:
            await query.edit_message_text(
                "🏗 <b>Real Estate</b>\n━━━━━━━━━━━━━━\n🏢 No buildings available yet!\nAsk an admin to add properties.",
                parse_mode="HTML",
                reply_markup=buildings_keyboard(),
            )
            return

        lines = ["🏗 <b>Available Properties</b>\n━━━━━━━━━━━━━━\n"]
        for b in buildings:
            lines.append(
                f"🏢 <b>{esc(b.get('name', 'Building'))}</b>\n"
                f"   💰 Price: {b.get('price', 0):,} coins\n"
                f"   📈 Revenue: {b.get('revenue', 0):,}/week\n"
            )
        await query.edit_message_text("\n".join(lines), parse_mode="HTML")

    elif action == "mine":
        db_user = db.get_or_create_user(user_id, username)
        my_buildings = db_user.get("buildings", [])
        if not my_buildings:
            await query.edit_message_text("🏗 You don't own any buildings yet!")
            return
        lines = ["🏠 <b>Your Buildings</b>\n━━━━━━━━━━━━━━\n"]
        for b in my_buildings:
            lines.append(f"🏢 <b>{esc(b.get('name', 'Building'))}</b> — Revenue: {b.get('revenue', 0):,}/week")
        await query.edit_message_text("\n".join(lines), parse_mode="HTML")

    elif action == "company":
        company = db.get_company_by_owner(user_id)
        if not company:
            await query.edit_message_text("🏭 You don't own a company yet. Create one via admin.")
            return
        db_user = db.get_or_create_user(user_id, username)
        my_buildings = db_user.get("buildings", [])
        if not my_buildings:
            await query.edit_message_text("🏠 You have no buildings to assign.")
            return
        await query.edit_message_text(
            f"🏭 Building assignment for <b>{esc(company.get('name', 'Company'))}</b>\n\nContact admin to link buildings to your company.",
            parse_mode="HTML",
        )
