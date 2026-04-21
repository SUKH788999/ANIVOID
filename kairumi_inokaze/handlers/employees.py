"""Handler for /employees — employee management and salary system."""

import logging
from telegram import Update
from telegram.ext import ContextTypes

from kairumi_inokaze import database as db
from kairumi_inokaze.middlewares import check_anti_spam
from kairumi_inokaze.utils.messages import esc

logger = logging.getLogger(__name__)


async def employees_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/employees — show employee list and payroll info."""
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
            "🏭 You don't own a company yet.\nAsk an admin to create one via /edit.",
        )
        return

    employees = company.get("employees", [])
    total_payroll = sum(e.get("salary", 0) for e in employees)

    if not employees:
        await update.message.reply_text(
            f"👷 <b>Your Employees</b>\n━━━━━━━━━━━━━━━━\n"
            f"No employees yet. Hire people via /edit admin panel.\n\n"
            f"💸 Total weekly payroll: <b>0</b> coins",
            parse_mode="HTML",
        )
        return

    lines = ["👷 <b>Your Employees</b>\n━━━━━━━━━━━━━━━━\n"]
    for emp in employees:
        lines.append(f"👤 @{esc(emp.get('username', '?'))} — Salary: <b>{emp.get('salary', 0):,}</b>/week")

    lines.append(f"\n━━━━━━━━━━━━━━━━")
    lines.append(f"💸 Total weekly payroll: <b>{total_payroll:,}</b> coins")

    db_user = db.get_or_create_user(user_id, username)
    if db_user.get("balance", 0) < total_payroll:
        lines.append(f"\n⚠️ <b>WARNING: Insufficient funds for payroll!</b>")

    await update.message.reply_text("\n".join(lines), parse_mode="HTML")
