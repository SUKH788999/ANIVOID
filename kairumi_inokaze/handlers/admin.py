"""Handler for /edit — comprehensive admin panel."""

import logging
import uuid
from datetime import datetime, timedelta, timezone
from telegram import Update
from telegram.ext import ContextTypes

from kairumi_inokaze import database as db
from kairumi_inokaze.config import ADMIN_IDS
from kairumi_inokaze.middlewares import is_admin
from kairumi_inokaze.utils.keyboards import admin_panel_keyboard
from kairumi_inokaze.utils.messages import esc
from kairumi_inokaze.utils.validators import parse_positive_int

logger = logging.getLogger(__name__)


async def admin_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/edit — admin panel entry point."""
    if update.message is None:
        return

    user = update.effective_user
    if not is_admin(user.id):
        await update.message.reply_text("🚫 Admin only command.")
        return

    await update.message.reply_text(
        "⚙️ <b>Admin Panel</b>\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\nSelect an action:",
        parse_mode="HTML",
        reply_markup=admin_panel_keyboard(),
    )


async def admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle admin panel action selection."""
    query = update.callback_query
    await query.answer()

    if not is_admin(update.effective_user.id):
        await query.answer("🚫 Admin only.", show_alert=True)
        return

    action = query.data.split(":")[1]
    context.user_data["admin_action"] = action
    context.user_data["admin_step"] = "user_id"

    prompts = {
        "coins": "💰 Enter user ID and coin change (e.g. <code>123456 +500</code> or <code>123456 -200</code>):",
        "title": "🎖 Enter user ID and new title (e.g. <code>123456 The Ghost</code>):",
        "rank": "⭐ Enter user ID and new rank (e.g. <code>123456 Crime Boss</code>):",
        "reset": "🔄 Enter user ID to reset:",
        "ban": "🚫 Enter user ID and action (e.g. <code>123456 ban</code> or <code>123456 unban</code>):",
        "company": "🏭 Enter owner ID, company name, revenue (e.g. <code>123456 BigCorp 5000</code>):",
        "bank": "🏦 Enter bank name and interest rate (e.g. <code>MyBank 3.5</code>):",
        "admin": "👑 Enter user ID to add/remove admin (e.g. <code>123456 add</code> or <code>123456 remove</code>):",
        "car": "🚗 Enter car name, price, speed, prestige (e.g. <code>Ferrari 50000 9 10</code>):",
        "building": "🏗 Enter building name, price, revenue/week (e.g. <code>Factory 20000 3000</code>):",
    }

    prompt = prompts.get(action, "Enter details:")
    await query.edit_message_text(prompt, parse_mode="HTML")


async def admin_input_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle admin input for the selected action."""
    action = context.user_data.get("admin_action")
    step = context.user_data.get("admin_step")

    if not action or step != "user_id":
        return

    if not is_admin(update.effective_user.id):
        return

    text = update.message.text.strip()
    parts = text.split()

    context.user_data.pop("admin_action", None)
    context.user_data.pop("admin_step", None)

    try:
        if action == "coins":
            user_id = int(parts[0])
            change_str = parts[1]
            if change_str.startswith("+"):
                amount = int(change_str[1:])
            elif change_str.startswith("-"):
                amount = -int(change_str[1:])
            else:
                amount = int(change_str)
            new_bal = db.add_coins(user_id, amount)
            await update.message.reply_text(
                f"✅ Coins updated! User {user_id} new balance: <b>{new_bal:,}</b>",
                parse_mode="HTML",
            )
            logger.info(f"Admin {update.effective_user.id} changed coins for {user_id} by {amount}")

        elif action == "title":
            user_id = int(parts[0])
            title = " ".join(parts[1:])
            user = db.get_or_create_user(user_id, str(user_id))
            user["title"] = title
            db.save_user(user)
            await update.message.reply_text(
                f"✅ Title '<b>{esc(title)}</b>' set for user {user_id}.",
                parse_mode="HTML",
            )

        elif action == "rank":
            user_id = int(parts[0])
            rank = " ".join(parts[1:])
            user = db.get_or_create_user(user_id, str(user_id))
            user["rank"] = rank
            db.save_user(user)
            await update.message.reply_text(
                f"✅ Rank '<b>{esc(rank)}</b>' set for user {user_id}.",
                parse_mode="HTML",
            )

        elif action == "reset":
            user_id = int(parts[0])
            user = db.get_or_create_user(user_id, str(user_id))
            user["balance"] = 1000
            user["bank_balance"] = 0
            user["kills"] = 0
            user["robs"] = 0
            user["dead_status"] = False
            user["dead_until"] = None
            user["protect_expiry"] = None
            user["rank"] = "Rookie"
            user["title"] = "None"
            user["premium"] = False
            user["premium_expiry"] = None
            db.save_user(user)
            await update.message.reply_text(f"✅ User {user_id} has been reset.")

        elif action == "ban":
            user_id = int(parts[0])
            action_type = parts[1].lower() if len(parts) > 1 else "ban"
            user = db.get_or_create_user(user_id, str(user_id))
            user["banned"] = (action_type == "ban")
            db.save_user(user)
            status = "banned" if user["banned"] else "unbanned"
            await update.message.reply_text(f"✅ User {user_id} has been {status}.")
            logger.info(f"Admin {update.effective_user.id} {status} user {user_id}")

        elif action == "company":
            owner_id = int(parts[0])
            name = parts[1] if len(parts) > 1 else "My Company"
            revenue = int(parts[2]) if len(parts) > 2 else 1000
            companies = db.get_companies()
            company_id = str(uuid.uuid4())[:8]
            companies.append({
                "company_id": company_id,
                "name": name,
                "owner_id": owner_id,
                "revenue": revenue,
                "roi_percent": 5,
                "min_investment": 1000,
                "employees": [],
                "investors": [],
            })
            db.save_companies(companies)
            await update.message.reply_text(
                f"✅ Company '<b>{esc(name)}</b>' created for user {owner_id}.",
                parse_mode="HTML",
            )

        elif action == "bank":
            name = parts[0] if parts else "New Bank"
            rate = float(parts[1]) if len(parts) > 1 else 2.5
            banks = db.get_banks()
            bank_id = str(len(banks) + 1)
            banks.append({"bank_id": bank_id, "name": name, "interest_rate": rate, "accounts": []})
            db.save_banks(banks)
            await update.message.reply_text(
                f"✅ Bank '<b>{esc(name)}</b>' added at {rate}%/week.",
                parse_mode="HTML",
            )

        elif action == "admin":
            user_id = int(parts[0])
            action_type = parts[1].lower() if len(parts) > 1 else "add"
            admin_list = db._db_get("admins:list") or list(ADMIN_IDS)
            if action_type == "add" and user_id not in admin_list:
                admin_list.append(user_id)
            elif action_type == "remove" and user_id in admin_list:
                admin_list.remove(user_id)
            db._db_set("admins:list", admin_list)
            await update.message.reply_text(f"✅ Admin list updated. User {user_id} {action_type}ed.")

        elif action == "car":
            name = parts[0]
            price = int(parts[1]) if len(parts) > 1 else 10000
            speed = int(parts[2]) if len(parts) > 2 else 5
            prestige = int(parts[3]) if len(parts) > 3 else 5
            cars = db.get_cars_shop()
            cars.append({"name": name, "price": price, "speed": speed, "prestige": prestige})
            db.save_cars_shop(cars)
            await update.message.reply_text(
                f"✅ Car '<b>{esc(name)}</b>' added to shop.",
                parse_mode="HTML",
            )

        elif action == "building":
            name = parts[0]
            price = int(parts[1]) if len(parts) > 1 else 20000
            revenue = int(parts[2]) if len(parts) > 2 else 2000
            buildings = db.get_buildings_shop()
            buildings.append({"name": name, "price": price, "revenue": revenue})
            db.save_buildings_shop(buildings)
            await update.message.reply_text(
                f"✅ Building '<b>{esc(name)}</b>' added to shop.",
                parse_mode="HTML",
            )

        else:
            await update.message.reply_text("❌ Unknown admin action.")

    except (ValueError, IndexError) as e:
        await update.message.reply_text(f"❌ Invalid input: {esc(str(e))}", parse_mode="HTML")
        logger.error(f"Admin input error: {e}")
