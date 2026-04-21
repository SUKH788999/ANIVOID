"""Handler for /auction — buy/sell/bid system."""

import logging
import uuid
from datetime import datetime, timedelta, timezone
from telegram import Update
from telegram.ext import ContextTypes

from kairumi_inokaze import database as db
from kairumi_inokaze.config import AUCTION_FEE_PERCENT, AUCTION_MIN_INCREMENT, ADMIN_IDS
from kairumi_inokaze.middlewares import check_anti_spam
from kairumi_inokaze.utils.keyboards import auction_keyboard
from kairumi_inokaze.utils.messages import esc
from kairumi_inokaze.utils.validators import parse_positive_int

logger = logging.getLogger(__name__)


async def auction_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/auction — show auction menu."""
    if update.message is None:
        return

    user = update.effective_user
    if await check_anti_spam(user.id):
        return

    if update.effective_chat.type in ("group", "supergroup"):
        db.add_group(update.effective_chat.id)

    await update.message.reply_text(
        "🔨 <b>Auction House</b>\n━━━━━━━━━━━━━━━\nBuy, sell, and bid on rare items:",
        parse_mode="HTML",
        reply_markup=auction_keyboard(),
    )


async def auction_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle auction menu selection."""
    query = update.callback_query
    await query.answer()

    action = query.data.split(":")[1]
    user_id = update.effective_user.id
    username = update.effective_user.username or update.effective_user.first_name or str(user_id)

    if action == "browse":
        auctions = db.get_active_auctions()
        if not auctions:
            await query.edit_message_text(
                "🔨 <b>Auction House</b>\n━━━━━━━━━━━━━━━\n📭 No active auctions right now!\nCheck back soon or sell an item.",
                parse_mode="HTML",
                reply_markup=auction_keyboard(),
            )
            return

        now = datetime.now(timezone.utc)
        lines = ["🔨 <b>Active Auctions</b>\n━━━━━━━━━━━━━━━\n"]
        for a in auctions:
            try:
                ends = datetime.fromisoformat(a.get("ends_at", ""))
                if ends.tzinfo is None:
                    ends = ends.replace(tzinfo=timezone.utc)
                remaining = max(0, int((ends - now).total_seconds()))
                h, m = divmod(remaining // 60, 60)
                time_str = f"{h}h {m}m"
            except Exception:
                time_str = "Unknown"

            lines.append(
                f"📦 <b>{esc(a.get('item', 'Item'))}</b>\n"
                f"   Current Bid: <b>{a.get('current_bid', a.get('start_price', 0)):,}</b> coins\n"
                f"   Bidder: @{esc(a.get('bidder_username', 'None'))}\n"
                f"   Time Left: {time_str}\n"
                f"   To bid: <code>/bid {a.get('item_id', '')} &lt;amount&gt;</code>\n"
            )
        await query.edit_message_text("\n".join(lines), parse_mode="HTML")

    elif action == "sell":
        context.user_data["auction_step"] = "item_name"
        context.user_data["auction_seller_id"] = user_id
        context.user_data["auction_seller_name"] = username
        await query.edit_message_text(
            "📦 <b>Sell on Auction House</b>\n\nWhat is the name of the item you want to sell?",
            parse_mode="HTML",
        )


async def auction_sell_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Multi-step auction sell flow."""
    step = context.user_data.get("auction_step")
    if not step or not step.startswith("item"):
        return

    user_id = update.effective_user.id
    text = update.message.text.strip()

    if step == "item_name":
        context.user_data["auction_item_name"] = text
        context.user_data["auction_step"] = "item_desc"
        await update.message.reply_text("📝 Describe the item:")

    elif step == "item_desc":
        context.user_data["auction_item_desc"] = text
        context.user_data["auction_step"] = "item_price"
        await update.message.reply_text("💰 Set the starting price (coins):")

    elif step == "item_price":
        price = parse_positive_int(text)
        if price is None:
            await update.message.reply_text("❌ Enter a valid positive number.")
            return

        item_id = str(uuid.uuid4())[:8]
        pending = {
            "item_id": item_id,
            "submitted_by": user_id,
            "seller_username": context.user_data.get("auction_seller_name", "Unknown"),
            "item": context.user_data.get("auction_item_name", "Item"),
            "description": context.user_data.get("auction_item_desc", ""),
            "start_price": price,
            "submitted_at": datetime.now(timezone.utc).isoformat(),
        }

        pending_list = db.get_pending_auctions()
        pending_list.append(pending)
        db.save_pending_auctions(pending_list)

        context.user_data.pop("auction_step", None)

        await update.message.reply_text(
            f"✅ <b>Item submitted for auction!</b>\n"
            f"📦 {esc(pending['item'])}\n"
            f"💰 Starting price: {price:,} coins\n\n"
            f"An admin will approve and set the duration.",
            parse_mode="HTML",
        )

        for admin_id in ADMIN_IDS:
            try:
                await context.bot.send_message(
                    admin_id,
                    f"🔨 <b>New Auction Submission</b>\n"
                    f"━━━━━━━━━━━━━━━━━━\n"
                    f"👤 Seller: @{esc(pending['seller_username'])} ({user_id})\n"
                    f"📦 Item: {esc(pending['item'])}\n"
                    f"📝 Desc: {esc(pending['description'])}\n"
                    f"💰 Start: {price:,}\n\n"
                    f"Use /edit to approve this auction.",
                    parse_mode="HTML",
                )
            except Exception as e:
                logger.error(f"Failed to notify admin {admin_id}: {e}")


async def bid_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/bid <item_id> <amount> — place a bid."""
    if update.message is None:
        return

    user = update.effective_user
    user_id = user.id
    username = user.username or user.first_name or str(user_id)

    if await check_anti_spam(user_id):
        return

    args = context.args
    if not args or len(args) < 2:
        await update.message.reply_text("📢 Usage: /bid &lt;item_id&gt; &lt;amount&gt;", parse_mode="HTML")
        return

    item_id = args[0]
    amount = parse_positive_int(args[1])
    if amount is None:
        await update.message.reply_text("❌ Invalid amount.")
        return

    auctions = db.get_active_auctions()
    target = next((a for a in auctions if a.get("item_id") == item_id), None)

    if not target:
        await update.message.reply_text("❌ Auction not found or has ended.")
        return

    current_bid = target.get("current_bid", target.get("start_price", 0))
    if amount < current_bid + AUCTION_MIN_INCREMENT:
        await update.message.reply_text(
            f"❌ Minimum bid is <b>{current_bid + AUCTION_MIN_INCREMENT:,}</b> coins.",
            parse_mode="HTML",
        )
        return

    db_user = db.get_or_create_user(user_id, username)
    if db_user.get("balance", 0) < amount:
        await update.message.reply_text("❌ You don't have enough coins.")
        return

    prev_bidder_id = target.get("bidder_id")

    target["current_bid"] = amount
    target["bidder_id"] = user_id
    target["bidder_username"] = username
    db.save_active_auctions(auctions)

    await update.message.reply_text(
        f"✅ <b>Bid placed!</b>\n📦 {esc(target['item'])}\n💰 Your bid: <b>{amount:,}</b> coins",
        parse_mode="HTML",
    )

    if prev_bidder_id and prev_bidder_id != user_id:
        try:
            await context.bot.send_message(
                prev_bidder_id,
                f"⚠️ You've been outbid on <b>{esc(target['item'])}</b>!\n"
                f"New bid: <b>{amount:,}</b> coins by @{esc(username)}",
                parse_mode="HTML",
            )
        except Exception:
            pass

    logger.info(f"Bid: {user_id} bid {amount} on {item_id}")
