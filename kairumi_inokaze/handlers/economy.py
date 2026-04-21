"""Handlers for /pay, /rob, /kill, /protect."""

import logging
import random
from datetime import datetime, timedelta, timezone
from telegram import Update
from telegram.ext import ContextTypes

from kairumi_inokaze import database as db
from kairumi_inokaze.config import (
    ROB_SUCCESS_CHANCE, KILL_REWARD, KILL_DEAD_DAYS, PROTECTION_PLANS
)
from kairumi_inokaze.middlewares import check_anti_spam, check_dead_status, check_protected
from kairumi_inokaze.utils.cooldowns import check_cooldown, apply_cooldown, format_cooldown
from kairumi_inokaze.utils.keyboards import protection_keyboard
from kairumi_inokaze.utils.messages import (
    rob_success_msg, rob_fail_msg, rob_protected_msg, rob_dead_msg, rob_target_dead_msg,
    kill_success_msg, kill_protected_msg, kill_dead_msg, pay_success_msg, esc,
)
from kairumi_inokaze.utils.validators import parse_positive_int

logger = logging.getLogger(__name__)


async def pay_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/pay <amount> — reply to target user."""
    if update.message is None:
        return

    sender = update.effective_user
    sender_id = sender.id
    sender_name = sender.username or sender.first_name or str(sender_id)

    if await check_anti_spam(sender_id):
        return

    if update.effective_chat.type in ("group", "supergroup"):
        db.add_group(update.effective_chat.id)

    if not update.message.reply_to_message:
        await update.message.reply_text("📢 Reply to a user with /pay &lt;amount&gt;", parse_mode="HTML")
        return

    target_msg = update.message.reply_to_message
    target_user = target_msg.from_user
    if not target_user or target_user.id == sender_id:
        await update.message.reply_text("❌ Invalid target.")
        return

    args = context.args
    if not args:
        await update.message.reply_text("📢 Usage: /pay &lt;amount&gt;", parse_mode="HTML")
        return

    amount = parse_positive_int(args[0])
    if amount is None:
        await update.message.reply_text("❌ Please enter a valid positive amount.")
        return

    sender_data = db.get_or_create_user(sender_id, sender_name)
    target_data = db.get_or_create_user(
        target_user.id,
        target_user.username or target_user.first_name or str(target_user.id)
    )

    if sender_data.get("banned"):
        await update.message.reply_text("🚫 You are banned.")
        return

    if sender_data.get("balance", 0) < amount:
        await update.message.reply_text("❌ You don't have enough coins.")
        return

    sender_data["balance"] -= amount
    target_data["balance"] = target_data.get("balance", 0) + amount
    db.save_user(sender_data)
    db.save_user(target_data)

    target_name = target_user.username or target_user.first_name or str(target_user.id)
    await update.message.reply_text(
        pay_success_msg(sender_name, target_name, amount, sender_data["balance"]),
        parse_mode="HTML",
    )
    logger.info(f"Pay: {sender_id} -> {target_user.id} amount={amount}")


async def rob_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/rob — reply to target."""
    if update.message is None:
        return

    robber = update.effective_user
    robber_id = robber.id
    robber_name = robber.username or robber.first_name or str(robber_id)

    if await check_anti_spam(robber_id):
        return

    if update.effective_chat.type in ("group", "supergroup"):
        db.add_group(update.effective_chat.id)

    if not update.message.reply_to_message:
        await update.message.reply_text("📢 Reply to a user to rob them.")
        return

    remaining = check_cooldown(robber_id, "rob")
    if remaining:
        await update.message.reply_text(
            f"⏳ Rob cooldown! Try again in <b>{format_cooldown(remaining)}</b>",
            parse_mode="HTML",
        )
        return

    target_user = update.message.reply_to_message.from_user
    if not target_user or target_user.id == robber_id:
        await update.message.reply_text("❌ Invalid target.")
        return

    robber_data = db.get_or_create_user(robber_id, robber_name)
    target_name = target_user.username or target_user.first_name or str(target_user.id)
    target_data = db.get_or_create_user(target_user.id, target_name)

    if robber_data.get("banned"):
        await update.message.reply_text("🚫 You are banned.")
        return

    if await check_dead_status(robber_id):
        await update.message.reply_text(rob_dead_msg(), parse_mode="HTML")
        return

    if await check_dead_status(target_user.id):
        await update.message.reply_text(rob_target_dead_msg(target_name), parse_mode="HTML")
        return

    if await check_protected(target_user.id):
        await update.message.reply_text(rob_protected_msg(target_name), parse_mode="HTML")
        return

    apply_cooldown(robber_id, "rob")

    if random.random() < ROB_SUCCESS_CHANCE:
        stolen = target_data.get("balance", 0)
        if stolen <= 0:
            await update.message.reply_text("😅 Your target is broke! Nothing to steal.")
            return
        target_data["balance"] = 0
        robber_data["balance"] = robber_data.get("balance", 0) + stolen
        robber_data["robs"] = robber_data.get("robs", 0) + 1
        db.save_user(target_data)
        db.save_user(robber_data)
        await update.message.reply_text(rob_success_msg(robber_name, target_name, stolen), parse_mode="HTML")
        logger.info(f"Rob success: {robber_id} stole {stolen} from {target_user.id}")
    else:
        await update.message.reply_text(rob_fail_msg(), parse_mode="HTML")
        logger.info(f"Rob fail: {robber_id} failed to rob {target_user.id}")


async def kill_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/kill — reply to target."""
    if update.message is None:
        return

    killer = update.effective_user
    killer_id = killer.id
    killer_name = killer.username or killer.first_name or str(killer_id)

    if await check_anti_spam(killer_id):
        return

    if update.effective_chat.type in ("group", "supergroup"):
        db.add_group(update.effective_chat.id)

    if not update.message.reply_to_message:
        await update.message.reply_text("📢 Reply to a user to kill them.")
        return

    remaining = check_cooldown(killer_id, "kill")
    if remaining:
        await update.message.reply_text(
            f"⏳ Kill cooldown! Try again in <b>{format_cooldown(remaining)}</b>",
            parse_mode="HTML",
        )
        return

    target_user = update.message.reply_to_message.from_user
    if not target_user or target_user.id == killer_id:
        await update.message.reply_text("❌ Invalid target.")
        return

    killer_data = db.get_or_create_user(killer_id, killer_name)
    target_name = target_user.username or target_user.first_name or str(target_user.id)
    target_data = db.get_or_create_user(target_user.id, target_name)

    if killer_data.get("banned"):
        await update.message.reply_text("🚫 You are banned.")
        return

    if await check_dead_status(killer_id):
        await update.message.reply_text(kill_dead_msg(), parse_mode="HTML")
        return

    if await check_protected(target_user.id):
        await update.message.reply_text(kill_protected_msg(target_name), parse_mode="HTML")
        return

    apply_cooldown(killer_id, "kill")

    dead_until = (datetime.now(timezone.utc) + timedelta(days=KILL_DEAD_DAYS)).isoformat()
    target_data["dead_status"] = True
    target_data["dead_until"] = dead_until
    db.save_user(target_data)

    killer_data["balance"] = killer_data.get("balance", 0) + KILL_REWARD
    killer_data["kills"] = killer_data.get("kills", 0) + 1
    db.save_user(killer_data)

    await update.message.reply_text(
        kill_success_msg(killer_name, target_name, KILL_REWARD),
        parse_mode="HTML",
    )
    logger.info(f"Kill: {killer_id} killed {target_user.id}, dead until {dead_until}")


async def protect_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/protect — show protection shop."""
    if update.message is None:
        return

    user = update.effective_user
    if await check_anti_spam(user.id):
        return

    if update.effective_chat.type in ("group", "supergroup"):
        db.add_group(update.effective_chat.id)

    await update.message.reply_text(
        "🛡 <b>Protection Shop</b>\n━━━━━━━━━━━━━━━\nChoose your protection duration:",
        parse_mode="HTML",
        reply_markup=protection_keyboard(),
    )


async def protect_buy_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle protection plan purchase callback."""
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    username = update.effective_user.username or update.effective_user.first_name or str(user_id)

    data = query.data
    try:
        plan_idx = int(data.split(":")[1])
        plan = PROTECTION_PLANS[plan_idx]
    except (IndexError, ValueError):
        await query.edit_message_text("❌ Invalid plan.")
        return

    db_user = db.get_or_create_user(user_id, username)

    if db_user.get("balance", 0) < plan["price"]:
        await query.edit_message_text(
            f"❌ You need {plan['price']:,} coins. You have {db_user.get('balance', 0):,}."
        )
        return

    db_user["balance"] -= plan["price"]
    expiry = (datetime.now(timezone.utc) + timedelta(days=plan["days"])).isoformat()
    db_user["protect_expiry"] = expiry
    db.save_user(db_user)

    await query.edit_message_text(
        f"🛡 <b>Protection activated!</b>\n"
        f"Duration: <b>{esc(plan['label'])}</b>\n"
        f"Expires: {expiry[:10]}\n"
        f"💰 Remaining balance: <b>{db_user['balance']:,}</b>",
        parse_mode="HTML",
    )
    logger.info(f"User {user_id} bought protection plan {plan['label']}")
