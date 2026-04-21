"""Handler for /mycompany."""

import logging
from telegram import Update
from telegram.ext import ContextTypes

from kairumi_inokaze import database as db
from kairumi_inokaze.middlewares import check_anti_spam
from kairumi_inokaze.utils.keyboards import company_keyboard
from kairumi_inokaze.utils.messages import esc

logger = logging.getLogger(__name__)


async def company_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/mycompany — show user's company."""
    if update.message is None:
        return

    user = update.effective_user
    user_id = user.id
    username = user.username or user.first_name or str(user_id)

    if await check_anti_spam(user_id):
        return

    if update.effective_chat.type in ("group", "supergroup"):
        db.add_group(update.effective_chat.id)

    company = db.get_company_by_owner(user_id)
    if not company:
        await update.message.reply_text(
            "🏭 You don't own a company yet.\n\nAsk an admin to create one for you via /edit.",
        )
        return

    investors = company.get("investors", [])
    employees = company.get("employees", [])

    await update.message.reply_text(
        f"🏭 <b>{esc(company.get('name', 'Company'))}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 Owner: @{esc(username)}\n"
        f"💰 Revenue: <b>{company.get('revenue', 0):,}</b>/week\n"
        f"👷 Employees: <b>{len(employees)}</b>\n"
        f"📈 Investors: <b>{len(investors)}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━",
        parse_mode="HTML",
        reply_markup=company_keyboard(),
    )


async def company_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle company management actions."""
    query = update.callback_query
    await query.answer()

    action = query.data.split(":")[1]
    user_id = update.effective_user.id
    username = update.effective_user.username or update.effective_user.first_name or str(user_id)

    company = db.get_company_by_owner(user_id)
    if not company:
        await query.edit_message_text("❌ You don't own a company.")
        return

    if action == "rename":
        context.user_data["company_rename"] = True
        await query.edit_message_text("✏️ Enter the new company name:")

    elif action == "investors":
        investors = company.get("investors", [])
        if not investors:
            await query.edit_message_text("📊 No investors yet.")
            return
        lines = ["📊 <b>Company Investors</b>\n"]
        for inv in investors:
            lines.append(f"👤 @{esc(inv.get('username', '?'))} — {inv.get('amount', 0):,} coins invested")
        await query.edit_message_text("\n".join(lines), parse_mode="HTML")

    elif action == "employees":
        employees = company.get("employees", [])
        if not employees:
            await query.edit_message_text("👷 No employees yet.")
            return
        lines = ["👷 <b>Employees</b>\n"]
        for emp in employees:
            lines.append(f"👤 @{esc(emp.get('username', '?'))} — Salary: {emp.get('salary', 0):,}/week")
        await query.edit_message_text("\n".join(lines), parse_mode="HTML")


async def company_rename_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle company rename."""
    if not context.user_data.get("company_rename"):
        return

    user_id = update.effective_user.id
    new_name = update.message.text.strip()
    if not new_name:
        return

    companies = db.get_companies()
    for c in companies:
        if c.get("owner_id") == user_id:
            c["name"] = new_name
            break
    db.save_companies(companies)

    context.user_data.pop("company_rename", None)
    await update.message.reply_text(
        f"✅ Company renamed to <b>{esc(new_name)}</b>!",
        parse_mode="HTML",
    )
