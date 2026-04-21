"""Handler for /invest — investment market."""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from kairumi_inokaze import database as db
from kairumi_inokaze.middlewares import check_anti_spam
from kairumi_inokaze.utils.messages import esc
from kairumi_inokaze.utils.validators import parse_positive_int

logger = logging.getLogger(__name__)


async def invest_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/invest — show investment market."""
    if update.message is None:
        return

    user = update.effective_user
    if await check_anti_spam(user.id):
        return

    if update.effective_chat.type in ("group", "supergroup"):
        db.add_group(update.effective_chat.id)

    companies = db.get_companies()
    if not companies:
        await update.message.reply_text(
            "📈 <b>Investment Market</b>\n━━━━━━━━━━━━━━━━━━━━\n\nNo companies available for investment yet.",
            parse_mode="HTML",
        )
        return

    lines = ["📈 <b>Investment Market</b>\n━━━━━━━━━━━━━━━━━━━━\n"]
    buttons = []
    for c in companies:
        owner_id = c.get("owner_id")
        owner_user = db.get_user(owner_id) if owner_id else None
        owner_name = owner_user.get("username", "Unknown") if owner_user else "Unknown"
        roi = c.get("roi_percent", 5)
        min_invest = c.get("min_investment", 1000)
        lines.append(
            f"🏭 <b>{esc(c.get('name', 'Company'))}</b>\n"
            f"   Owner: @{esc(owner_name)}\n"
            f"   ROI: {roi}%/week\n"
            f"   Min invest: {min_invest:,} coins\n"
        )
        buttons.append([
            InlineKeyboardButton(
                f"💰 Invest in {c.get('name', 'Company')}",
                callback_data=f"invest:buy:{c.get('company_id', '')}",
            )
        ])

    await update.message.reply_text(
        "\n".join(lines),
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(buttons) if buttons else None,
    )


async def invest_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle invest button."""
    query = update.callback_query
    await query.answer()

    parts = query.data.split(":")
    if len(parts) < 3:
        return

    company_id = parts[2]
    user_id = update.effective_user.id
    username = update.effective_user.username or update.effective_user.first_name or str(user_id)

    companies = db.get_companies()
    company = next((c for c in companies if str(c.get("company_id", "")) == str(company_id)), None)
    if not company:
        await query.edit_message_text("❌ Company not found.")
        return

    context.user_data["invest_company_id"] = company_id
    context.user_data["invest_step"] = "amount"
    await query.edit_message_text(
        f"💰 How much do you want to invest in <b>{esc(company.get('name', 'Company'))}</b>?\n"
        f"Minimum: {company.get('min_investment', 1000):,} coins\n\nType the amount:",
        parse_mode="HTML",
    )


async def invest_amount_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle invest amount input."""
    if context.user_data.get("invest_step") != "amount":
        return

    user_id = update.effective_user.id
    username = update.effective_user.username or update.effective_user.first_name or str(user_id)
    company_id = context.user_data.get("invest_company_id")

    amount = parse_positive_int(update.message.text)
    if amount is None:
        await update.message.reply_text("❌ Enter a valid positive number.")
        return

    companies = db.get_companies()
    company = next((c for c in companies if str(c.get("company_id", "")) == str(company_id)), None)
    if not company:
        await update.message.reply_text("❌ Company not found.")
        context.user_data.pop("invest_step", None)
        return

    min_invest = company.get("min_investment", 1000)
    if amount < min_invest:
        await update.message.reply_text(f"❌ Minimum investment is {min_invest:,} coins.")
        return

    db_user = db.get_or_create_user(user_id, username)
    if db_user.get("balance", 0) < amount:
        await update.message.reply_text("❌ Insufficient balance.")
        context.user_data.pop("invest_step", None)
        return

    db_user["balance"] -= amount
    investors = company.get("investors", [])
    existing = next((inv for inv in investors if inv.get("user_id") == user_id), None)
    if existing:
        existing["amount"] = existing.get("amount", 0) + amount
    else:
        investors.append({"user_id": user_id, "username": username, "amount": amount})
    company["investors"] = investors

    db.save_user(db_user)
    db.save_companies(companies)

    context.user_data.pop("invest_step", None)
    context.user_data.pop("invest_company_id", None)

    await update.message.reply_text(
        f"✅ <b>Investment successful!</b>\n"
        f"🏭 Company: <b>{esc(company.get('name', 'Company'))}</b>\n"
        f"💰 Invested: <b>{amount:,}</b> coins\n"
        f"📈 ROI: {company.get('roi_percent', 5)}%/week",
        parse_mode="HTML",
    )
    logger.info(f"User {user_id} invested {amount} in company {company_id}")
