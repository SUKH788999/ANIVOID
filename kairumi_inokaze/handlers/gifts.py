"""Handler for /gifts — reply-based gift system."""

import logging
from datetime import datetime, timedelta, timezone
from telegram import Update
from telegram.ext import ContextTypes

from kairumi_inokaze import database as db
from kairumi_inokaze.middlewares import check_anti_spam
from kairumi_inokaze.utils.keyboards import gifts_keyboard
from kairumi_inokaze.utils.messages import esc
from kairumi_inokaze.utils.validators import parse_positive_int

logger = logging.getLogger(__name__)


async def gifts_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/gifts — show gift menu (reply to user)."""
    if update.message is None:
        return

    user = update.effective_user
    if await check_anti_spam(user.id):
        return

    if update.effective_chat.type in ("group", "supergroup"):
        db.add_group(update.effective_chat.id)

    if not update.message.reply_to_message:
        await update.message.reply_text("📢 Reply to a user to send them a gift.")
        return

    target_user = update.message.reply_to_message.from_user
    if not target_user or target_user.id == user.id:
        await update.message.reply_text("❌ Invalid target.")
        return

    target_name = target_user.username or target_user.first_name or str(target_user.id)
    context.user_data["gift_target_id"] = target_user.id
    context.user_data["gift_target_name"] = target_name

    await update.message.reply_text(
        f"🎁 <b>Gift Menu — Sending to @{esc(target_name)}</b>\n━━━━━━━━━━━━━━━━━━━━━━━━\nChoose a gift:",
        parse_mode="HTML",
        reply_markup=gifts_keyboard(target_name),
    )


async def gift_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle gift type selection."""
    query = update.callback_query
    await query.answer()

    gift_type = query.data.split(":")[1]
    sender_id = update.effective_user.id
    sender_name = update.effective_user.username or update.effective_user.first_name or str(sender_id)

    target_id = context.user_data.get("gift_target_id")
    target_name = context.user_data.get("gift_target_name", "Unknown")

    if not target_id:
        await query.edit_message_text("❌ Session expired. Use /gifts again.")
        return

    sender_data = db.get_or_create_user(sender_id, sender_name)
    target_data = db.get_or_create_user(target_id, target_name)

    if gift_type == "revive":
        if target_data.get("dead_status", False):
            cost = 500
            if sender_data.get("balance", 0) < cost:
                await query.edit_message_text(f"❌ You need {cost:,} coins to revive.")
                return
            sender_data["balance"] -= cost
            target_data["dead_status"] = False
            target_data["dead_until"] = None
            target_data["protect_expiry"] = (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat()
            db.save_user(sender_data)
            db.save_user(target_data)
            await query.edit_message_text(
                f"💊 @{esc(target_name)} has been revived!\n🛡 24h protection granted!\n💰 Cost: 500 coins",
                parse_mode="HTML",
            )
        else:
            await query.edit_message_text(f"❌ @{esc(target_name)} is not dead.", parse_mode="HTML")

    elif gift_type == "coins":
        context.user_data["gift_type"] = "coins"
        await query.edit_message_text(f"💰 How many coins do you want to send to @{esc(target_name)}? Type the amount:", parse_mode="HTML")

    elif gift_type == "rank":
        current_rank = sender_data.get("rank", "Rookie")
        target_data["rank"] = current_rank
        db.save_user(target_data)
        await query.edit_message_text(
            f"⭐ You gifted your rank <b>{esc(current_rank)}</b> to @{esc(target_name)}!",
            parse_mode="HTML",
        )

    elif gift_type == "title":
        current_title = sender_data.get("title", "None")
        if current_title == "None":
            await query.edit_message_text("❌ You don't have a title to gift.")
            return
        target_data["title"] = current_title
        db.save_user(target_data)
        await query.edit_message_text(
            f"🎖 You gifted your title <b>{esc(current_title)}</b> to @{esc(target_name)}!",
            parse_mode="HTML",
        )

    elif gift_type == "premium":
        if not sender_data.get("premium"):
            await query.edit_message_text("❌ You don't have premium to gift.")
            return
        target_data["premium"] = True
        target_data["premium_expiry"] = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
        db.save_user(target_data)
        await query.edit_message_text(
            f"👑 You gifted 1 day of Premium to @{esc(target_name)}!",
            parse_mode="HTML",
        )

    elif gift_type == "emoji":
        cost = 200
        if sender_data.get("balance", 0) < cost:
            await query.edit_message_text(f"❌ You need {cost:,} coins.")
            return
        sender_data["balance"] -= cost
        db.save_user(sender_data)
        await query.edit_message_text(f"😂 Emoji pack sent to @{esc(target_name)}! 🎉🎊🥳🎈✨", parse_mode="HTML")

    elif gift_type == "inventory":
        await query.edit_message_text("🎒 Inventory gifting is <b>Coming Soon!</b>", parse_mode="HTML")


async def gift_coins_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle coin amount input for coin gifting."""
    if context.user_data.get("gift_type") != "coins":
        return

    sender_id = update.effective_user.id
    sender_name = update.effective_user.username or update.effective_user.first_name or str(sender_id)
    target_id = context.user_data.get("gift_target_id")
    target_name = context.user_data.get("gift_target_name", "Unknown")

    if not target_id:
        return

    amount = parse_positive_int(update.message.text)
    if amount is None:
        await update.message.reply_text("❌ Enter a valid positive number.")
        return

    sender_data = db.get_or_create_user(sender_id, sender_name)
    target_data = db.get_or_create_user(target_id, target_name)

    if sender_data.get("balance", 0) < amount:
        await update.message.reply_text(f"❌ You only have {sender_data.get('balance', 0):,} coins.")
        context.user_data.pop("gift_type", None)
        return

    sender_data["balance"] -= amount
    target_data["balance"] = target_data.get("balance", 0) + amount
    db.save_user(sender_data)
    db.save_user(target_data)
    context.user_data.pop("gift_type", None)

    await update.message.reply_text(
        f"💰 You sent <b>{amount:,}</b> coins to @{esc(target_name)}!\n"
        f"Your new balance: <b>{sender_data['balance']:,}</b>",
        parse_mode="HTML",
    )
    logger.info(f"Gift coins: {sender_id} -> {target_id}, amount={amount}")
