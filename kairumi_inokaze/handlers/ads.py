"""Handler for /ads — admin broadcast system."""

import logging
from telegram import Update
from telegram.ext import ContextTypes

from kairumi_inokaze import database as db
from kairumi_inokaze.config import ADMIN_IDS
from kairumi_inokaze.middlewares import check_anti_spam, is_admin

logger = logging.getLogger(__name__)


async def ads_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/ads — admin only broadcast tool."""
    if update.message is None:
        return

    user = update.effective_user
    user_id = user.id

    if not is_admin(user_id):
        await update.message.reply_text("🚫 Admin only command.")
        return

    context.user_data["ads_step"] = "waiting_media"
    await update.message.reply_text(
        "📢 <b>Ad Broadcast Setup</b>\n\n"
        "Send your ad media now (photo/GIF/video) with a caption.\n"
        "Or send text-only for a text broadcast.",
        parse_mode="HTML",
    )


async def ads_media_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Capture ad media from admin."""
    if context.user_data.get("ads_step") != "waiting_media":
        return

    if update.message is None:
        return

    user = update.effective_user
    if not is_admin(user.id):
        return

    msg = update.message
    ad_data = {}

    if msg.photo:
        ad_data["type"] = "photo"
        ad_data["file_id"] = msg.photo[-1].file_id
        ad_data["caption"] = msg.caption or ""
    elif msg.video:
        ad_data["type"] = "video"
        ad_data["file_id"] = msg.video.file_id
        ad_data["caption"] = msg.caption or ""
    elif msg.animation:
        ad_data["type"] = "animation"
        ad_data["file_id"] = msg.animation.file_id
        ad_data["caption"] = msg.caption or ""
    elif msg.text:
        ad_data["type"] = "text"
        ad_data["text"] = msg.text
    else:
        await update.message.reply_text("❌ Unsupported media type. Send photo, GIF, video, or text.")
        return

    db.set_last_ad(ad_data)
    context.user_data.pop("ads_step", None)

    groups = db.get_groups()
    await update.message.reply_text(
        f"✅ <b>Ad saved!</b>\n"
        f"📡 Will broadcast to <b>{len(groups)}</b> groups\n"
        f"⏰ Auto-broadcast every 7 hours\n\n"
        f"Use /broadcast to send immediately.",
        parse_mode="HTML",
    )
    logger.info(f"Admin {user.id} set new ad: type={ad_data.get('type')}")


async def broadcast_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/broadcast — immediately send current ad to all groups."""
    if update.message is None:
        return

    user = update.effective_user
    if not is_admin(user.id):
        await update.message.reply_text("🚫 Admin only.")
        return

    await _broadcast_ad(context)
    await update.message.reply_text("📡 Broadcast sent to all groups!")


async def _broadcast_ad(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send the current ad to all groups in the DB."""
    import time
    ad = db.get_last_ad()
    if not ad:
        logger.info("No ad to broadcast")
        return

    groups = db.get_groups()
    sent = 0
    for chat_id in groups:
        try:
            if ad.get("type") == "photo":
                await context.bot.send_photo(chat_id, ad["file_id"], caption=ad.get("caption"))
            elif ad.get("type") == "video":
                await context.bot.send_video(chat_id, ad["file_id"], caption=ad.get("caption"))
            elif ad.get("type") == "animation":
                await context.bot.send_animation(chat_id, ad["file_id"], caption=ad.get("caption"))
            elif ad.get("type") == "text":
                await context.bot.send_message(chat_id, ad.get("text", ""))
            sent += 1
        except Exception as e:
            logger.warning(f"Failed to send ad to {chat_id}: {e}")

    db.set_ad_last_sent(time.time())
    logger.info(f"Ad broadcast sent to {sent}/{len(groups)} groups")
