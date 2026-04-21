"""Handler for /help + issue reporter."""

import logging
from telegram import Update
from telegram.ext import ContextTypes

from kairumi_inokaze import database as db
from kairumi_inokaze.config import ADMIN_IDS
from kairumi_inokaze.middlewares import check_anti_spam
from kairumi_inokaze.utils.keyboards import help_keyboard
from kairumi_inokaze.utils.messages import help_text, esc

logger = logging.getLogger(__name__)


async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/help — show all commands."""
    if update.message is None:
        return

    user = update.effective_user
    if await check_anti_spam(user.id):
        return

    if update.effective_chat.type in ("group", "supergroup"):
        db.add_group(update.effective_chat.id)

    await update.message.reply_text(help_text(), parse_mode="HTML", reply_markup=help_keyboard())


async def help_issue_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle 'I Have an Issue' button."""
    query = update.callback_query
    await query.answer()
    context.user_data["awaiting_issue"] = True
    await query.edit_message_text("📝 Please type your issue and I'll forward it to the admins:")


async def issue_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Capture and forward user issue to all admins."""
    if not context.user_data.get("awaiting_issue"):
        return
    if update.message is None:
        return

    context.user_data["awaiting_issue"] = False

    user = update.effective_user
    user_id = user.id
    username = user.username or user.first_name or str(user_id)
    issue_text = update.message.text

    await update.message.reply_text("✅ Your issue has been forwarded to the admins. We'll get back to you soon!")

    admin_msg = (
        f"🆘 <b>Issue Report</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"👤 User: @{esc(username)} ({user_id})\n"
        f"📝 Issue: {esc(issue_text)}"
    )

    for admin_id in ADMIN_IDS:
        try:
            await context.bot.send_message(admin_id, admin_msg, parse_mode="HTML")
        except Exception as e:
            logger.error(f"Failed to forward issue to admin {admin_id}: {e}")
