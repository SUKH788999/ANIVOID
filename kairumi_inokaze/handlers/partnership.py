"""Handler for /partnershipRequest — partnership request flow."""

import logging
from telegram import Update
from telegram.ext import ContextTypes

from kairumi_inokaze import database as db
from kairumi_inokaze.config import ADMIN_IDS
from kairumi_inokaze.middlewares import check_anti_spam, is_admin
from kairumi_inokaze.utils.keyboards import partnership_keyboard
from kairumi_inokaze.utils.messages import esc

logger = logging.getLogger(__name__)

PARTNER_NAME = "partner_name"
PARTNER_REASON = "partner_reason"


async def partnership_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/partnershipRequest — start partnership conversation flow."""
    if update.message is None:
        return

    user = update.effective_user
    user_id = user.id
    username = user.username or user.first_name or str(user_id)

    if await check_anti_spam(user_id):
        return

    if update.effective_chat.type in ("group", "supergroup"):
        db.add_group(update.effective_chat.id)

    context.user_data["partner_step"] = PARTNER_NAME
    await update.message.reply_text(
        "🤝 <b>Partnership Request</b>\n\nWhat is your name or company name?",
        parse_mode="HTML",
    )


async def partnership_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Multi-step partnership flow."""
    step = context.user_data.get("partner_step")
    if not step:
        return

    user = update.effective_user
    user_id = user.id
    username = user.username or user.first_name or str(user_id)
    text = update.message.text.strip()

    if step == PARTNER_NAME:
        context.user_data["partner_name"] = text
        context.user_data["partner_step"] = PARTNER_REASON
        await update.message.reply_text("📝 What is your reason for requesting a partnership?")

    elif step == PARTNER_REASON:
        name = context.user_data.get("partner_name", "Unknown")
        reason = text

        context.user_data.pop("partner_step", None)
        context.user_data.pop("partner_name", None)

        await update.message.reply_text(
            "✅ <b>Partnership request submitted!</b>\n\nWe'll review your request and get back to you.",
            parse_mode="HTML",
        )

        admin_msg = (
            f"🤝 <b>Partnership Request</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"👤 User: @{esc(username)} ({user_id})\n"
            f"📛 Name: {esc(name)}\n"
            f"📝 Reason: {esc(reason)}"
        )

        for admin_id in ADMIN_IDS:
            try:
                await context.bot.send_message(
                    admin_id,
                    admin_msg,
                    parse_mode="HTML",
                    reply_markup=partnership_keyboard(user_id),
                )
            except Exception as e:
                logger.error(f"Failed to notify admin {admin_id}: {e}")

        logger.info(f"User {user_id} submitted partnership request")


async def partnership_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle partnership accept/reject by admin."""
    query = update.callback_query
    await query.answer()

    if not is_admin(update.effective_user.id):
        await query.answer("🚫 Admin only.", show_alert=True)
        return

    parts = query.data.split(":")
    action = parts[1]
    target_user_id = int(parts[2])

    if action == "accept":
        await query.edit_message_text(
            f"✅ Partnership accepted for user {target_user_id}.",
        )
        try:
            await context.bot.send_message(
                target_user_id,
                "🎉 <b>Your partnership request has been accepted!</b> Welcome aboard!",
                parse_mode="HTML",
            )
        except Exception:
            pass
    elif action == "reject":
        await query.edit_message_text(f"❌ Partnership rejected for user {target_user_id}.")
        try:
            await context.bot.send_message(
                target_user_id,
                "😔 Your partnership request was not accepted at this time.",
            )
        except Exception:
            pass
