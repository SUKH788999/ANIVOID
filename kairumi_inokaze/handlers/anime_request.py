"""Handlers for /roa, /ric, /tr, /trc — anime request system."""

import logging
import uuid
from datetime import datetime, timezone
from telegram import Update
from telegram.ext import ContextTypes

from kairumi_inokaze import database as db
from kairumi_inokaze.config import ADMIN_IDS
from kairumi_inokaze.middlewares import check_anti_spam, is_admin
from kairumi_inokaze.utils.keyboards import anime_request_keyboard
from kairumi_inokaze.utils.messages import esc

logger = logging.getLogger(__name__)


async def roa_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/roa <anime> — submit anime request."""
    if update.message is None:
        return

    user = update.effective_user
    user_id = user.id
    username = user.username or user.first_name or str(user_id)

    if await check_anti_spam(user_id):
        return

    if update.effective_chat.type in ("group", "supergroup"):
        db.add_group(update.effective_chat.id)

    if not context.args:
        await update.message.reply_text("📢 Usage: /roa &lt;anime name&gt;", parse_mode="HTML")
        return

    anime_name = " ".join(context.args)
    db_user = db.get_or_create_user(user_id, username)

    req_id = str(uuid.uuid4())[:8]
    entry = {
        "id": req_id,
        "user_id": user_id,
        "username": username,
        "anime": anime_name,
        "premium": db_user.get("premium", False),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "status": "pending",
    }

    db.add_anime_request(entry)
    await update.message.reply_text(
        f"✅ <b>Anime Request Submitted!</b>\n"
        f"🎌 Anime: <b>{esc(anime_name)}</b>\n"
        f"🆔 Request ID: <code>{req_id}</code>\n"
        f"⏳ Status: Pending review",
        parse_mode="HTML",
    )

    admin_msg = (
        f"📨 <b>New Anime Request</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"👤 User: @{esc(username)} ({user_id})\n"
        f"🎌 Anime: <b>{esc(anime_name)}</b>\n"
        f"👑 Premium: {'Yes' if entry['premium'] else 'No'}\n"
        f"🕐 Time: {entry['timestamp'][:19]}\n"
        f"━━━━━━━━━━━━━━━━━━"
    )

    for admin_id in ADMIN_IDS:
        try:
            await context.bot.send_message(
                admin_id,
                admin_msg,
                parse_mode="HTML",
                reply_markup=anime_request_keyboard(req_id),
            )
        except Exception as e:
            logger.error(f"Failed to notify admin {admin_id}: {e}")

    logger.info(f"User {user_id} submitted anime request: {anime_name}")


async def tr_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/tr — list pending anime requests (admin only)."""
    if update.message is None:
        return

    user = update.effective_user
    if not is_admin(user.id):
        await update.message.reply_text("🚫 Admin only.")
        return

    pending = db.get_pending_requests()
    if not pending:
        await update.message.reply_text("📭 No pending anime requests.")
        return

    for req in pending:
        await update.message.reply_text(
            f"📋 <b>Pending Request</b>\n"
            f"🆔 ID: <code>{req.get('id', '?')}</code>\n"
            f"👤 @{esc(req.get('username', '?'))} ({req.get('user_id', '?')})\n"
            f"🎌 Anime: <b>{esc(req.get('anime', '?'))}</b>\n"
            f"👑 Premium: {'Yes' if req.get('premium') else 'No'}\n"
            f"🕐 {req.get('timestamp', '')[:19]}",
            parse_mode="HTML",
            reply_markup=anime_request_keyboard(req.get("id", "")),
        )


async def ric_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/ric — completed requests (admin only)."""
    if update.message is None:
        return

    user = update.effective_user
    if not is_admin(user.id):
        await update.message.reply_text("🚫 Admin only.")
        return

    completed = db.get_completed_requests()
    completed_only = [r for r in completed if r.get("status") == "completed"]

    if not completed_only:
        await update.message.reply_text("📭 No completed anime requests.")
        return

    lines = [f"✅ <b>Completed Requests ({len(completed_only)})</b>\n"]
    for req in completed_only[-10:]:
        lines.append(
            f"🎌 <b>{esc(req.get('anime', '?'))}</b> — @{esc(req.get('username', '?'))}\n"
            f"   Completed by: {esc(req.get('completed_by', '?'))} at {req.get('completed_at', '')[:10]}"
        )
    await update.message.reply_text("\n".join(lines), parse_mode="HTML")


async def trc_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/trc — full request history (admin only)."""
    if update.message is None:
        return

    user = update.effective_user
    if not is_admin(user.id):
        await update.message.reply_text("🚫 Admin only.")
        return

    pending = db.get_pending_requests()
    completed = db.get_completed_requests()
    all_reqs = pending + completed
    all_reqs.sort(key=lambda r: r.get("timestamp", ""), reverse=True)

    if not all_reqs:
        await update.message.reply_text("📭 No requests yet.")
        return

    lines = [f"📋 <b>Full Request History</b> ({len(all_reqs)} total)\n"]
    for req in all_reqs[:20]:
        status_emoji = {"pending": "⏳", "completed": "✅", "rejected": "❌"}.get(req.get("status", ""), "❓")
        lines.append(
            f"{status_emoji} <b>{esc(req.get('anime', '?'))}</b> — @{esc(req.get('username', '?'))}\n"
            f"   {req.get('timestamp', '')[:10]} | Status: {req.get('status', '?')}"
        )
    await update.message.reply_text("\n".join(lines), parse_mode="HTML")


async def anime_request_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle complete/reject buttons on anime requests."""
    query = update.callback_query
    await query.answer()

    user = update.effective_user
    if not is_admin(user.id):
        await query.answer("🚫 Admin only.", show_alert=True)
        return

    parts = query.data.split(":")
    action = parts[1]
    req_id = parts[2]

    admin_name = user.username or user.first_name or str(user.id)

    if action == "complete":
        success = db.complete_anime_request(req_id, admin_name)
        if success:
            await query.edit_message_text(
                f"✅ <b>Request {req_id} marked complete by @{esc(admin_name)}</b>",
                parse_mode="HTML",
            )
        else:
            await query.edit_message_text(f"❌ Request {req_id} not found.")

    elif action == "reject":
        success = db.reject_anime_request(req_id)
        if success:
            await query.edit_message_text(
                f"❌ <b>Request {req_id} rejected by @{esc(admin_name)}</b>",
                parse_mode="HTML",
            )
        else:
            await query.edit_message_text(f"❌ Request {req_id} not found.")
