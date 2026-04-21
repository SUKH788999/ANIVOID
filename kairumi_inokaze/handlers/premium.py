"""Handler for /premium shop."""

import logging
from datetime import datetime, timedelta, timezone
from telegram import Update
from telegram.ext import ContextTypes

from kairumi_inokaze import database as db
from kairumi_inokaze.config import PREMIUM_PLANS
from kairumi_inokaze.middlewares import check_anti_spam
from kairumi_inokaze.utils.keyboards import premium_keyboard
from kairumi_inokaze.utils.messages import esc

logger = logging.getLogger(__name__)


async def premium_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/premium — show premium plans."""
    if update.message is None:
        return

    user = update.effective_user
    if await check_anti_spam(user.id):
        return

    if update.effective_chat.type in ("group", "supergroup"):
        db.add_group(update.effective_chat.id)

    await update.message.reply_text(
        "👑 <b>Premium Plans</b>\n━━━━━━━━━━━━━━━━━━━━\nChoose a premium duration:",
        parse_mode="HTML",
        reply_markup=premium_keyboard(),
    )


async def premium_buy_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle premium purchase callback."""
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    username = update.effective_user.username or update.effective_user.first_name or str(user_id)

    data = query.data
    try:
        plan_idx = int(data.split(":")[1])
        plan = PREMIUM_PLANS[plan_idx]
    except (IndexError, ValueError):
        await query.edit_message_text("❌ Invalid plan.")
        return

    db_user = db.get_or_create_user(user_id, username)

    if db_user.get("balance", 0) < plan["price"]:
        await query.edit_message_text(
            f"❌ You need <b>{plan['price']:,}</b> coins. You have <b>{db_user.get('balance', 0):,}</b>.",
            parse_mode="HTML",
        )
        return

    db_user["balance"] -= plan["price"]

    existing_expiry = db_user.get("premium_expiry")
    if existing_expiry and db_user.get("premium"):
        try:
            base = datetime.fromisoformat(existing_expiry)
            if base.tzinfo is None:
                base = base.replace(tzinfo=timezone.utc)
            if base < datetime.now(timezone.utc):
                base = datetime.now(timezone.utc)
        except Exception:
            base = datetime.now(timezone.utc)
    else:
        base = datetime.now(timezone.utc)

    expiry = (base + timedelta(days=plan["days"])).isoformat()
    db_user["premium"] = True
    db_user["premium_expiry"] = expiry
    db.save_user(db_user)

    await query.edit_message_text(
        f"⚡ <b>Premium activated!</b>\n"
        f"Plan: <b>{esc(plan['label'])}</b>\n"
        f"Expires: {expiry[:10]}\n"
        f"💰 Remaining balance: <b>{db_user['balance']:,}</b>",
        parse_mode="HTML",
    )
    logger.info(f"User {user_id} bought premium plan {plan['label']}")
