"""Handlers for /banks, /mybankaccount, /withdraw."""

import logging
import random
import string
from telegram import Update
from telegram.ext import ContextTypes

from kairumi_inokaze import database as db
from kairumi_inokaze.middlewares import check_anti_spam
from kairumi_inokaze.utils.keyboards import bank_account_keyboard
from kairumi_inokaze.utils.messages import esc
from kairumi_inokaze.utils.validators import parse_positive_int, is_valid_pin

logger = logging.getLogger(__name__)


def _gen_account_number() -> str:
    return "".join(random.choices(string.digits, k=8))


def _gen_pin() -> str:
    return "".join(random.choices(string.digits, k=4))


async def banks_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/banks — list available banks."""
    if update.message is None:
        return

    user = update.effective_user
    if await check_anti_spam(user.id):
        return

    if update.effective_chat.type in ("group", "supergroup"):
        db.add_group(update.effective_chat.id)

    banks = db.get_banks()
    if not banks:
        banks = [
            {"bank_id": "1", "name": "First National Bank", "interest_rate": 2.5},
            {"bank_id": "2", "name": "Kairumi Savings", "interest_rate": 3.0},
            {"bank_id": "3", "name": "Shadow Finance", "interest_rate": 4.5},
        ]
        db.save_banks(banks)

    lines = ["🏦 <b>Available Banks</b>\n━━━━━━━━━━━━━━━━━━\n"]
    for b in banks:
        lines.append(
            f"🏦 <b>{esc(b['name'])}</b>\n"
            f"   Interest Rate: {b['interest_rate']}%/week\n"
        )
    lines.append("\nUse /mybankaccount to open or view your accounts.")

    await update.message.reply_text("\n".join(lines), parse_mode="HTML")


async def my_bank_account_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/mybankaccount — show/open bank accounts."""
    if update.message is None:
        return

    user = update.effective_user
    user_id = user.id
    username = user.username or user.first_name or str(user_id)

    if await check_anti_spam(user_id):
        return

    if update.effective_chat.type in ("group", "supergroup"):
        db.add_group(update.effective_chat.id)

    db_user = db.get_or_create_user(user_id, username)
    accounts = db_user.get("bank_accounts", [])

    if not accounts:
        await update.message.reply_text(
            "🏦 <b>Your Bank Accounts</b>\n━━━━━━━━━━━━━━━━━━\nNo accounts yet!\n\nUse the button below to open one:",
            parse_mode="HTML",
            reply_markup=bank_account_keyboard([]),
        )
    else:
        lines = ["🏦 <b>Your Bank Accounts</b>\n━━━━━━━━━━━━━━━━━━\n"]
        for acc in accounts:
            last4 = str(acc.get("account_number", "????"))[-4:]
            lines.append(
                f"🏦 <b>{esc(acc.get('bank_name', 'Bank'))}</b>\n"
                f"   Account: ****{last4}\n"
                f"   Balance: <b>{acc.get('balance', 0):,}</b> coins\n"
            )
        await update.message.reply_text(
            "\n".join(lines),
            parse_mode="HTML",
            reply_markup=bank_account_keyboard(accounts),
        )


async def bank_open_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle opening a new bank account."""
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    username = update.effective_user.username or update.effective_user.first_name or str(user_id)
    db_user = db.get_or_create_user(user_id, username)

    banks = db.get_banks() or [{"bank_id": "1", "name": "First National Bank", "interest_rate": 2.5}]
    bank = random.choice(banks)

    account_number = _gen_account_number()
    pin = _gen_pin()

    new_account = {
        "account_id": account_number,
        "bank_id": bank["bank_id"],
        "bank_name": bank["name"],
        "account_number": account_number,
        "pin": pin,
        "balance": 0,
    }

    accounts = db_user.get("bank_accounts", [])
    accounts.append(new_account)
    db_user["bank_accounts"] = accounts
    db.save_user(db_user)

    last4 = account_number[-4:]
    await query.edit_message_text(
        f"✅ <b>Account opened at {esc(bank['name'])}!</b>\n\n"
        f"📋 Account Number: ****{last4}\n"
        f"🔑 PIN: <code>{pin}</code> (keep this safe!)\n\n"
        f"Use /mybankaccount to manage your account.",
        parse_mode="HTML",
    )
    logger.info(f"User {user_id} opened bank account at {bank['name']}")


async def withdraw_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/withdraw — start withdrawal flow."""
    if update.message is None:
        return

    user = update.effective_user
    user_id = user.id
    username = user.username or user.first_name or str(user_id)

    if await check_anti_spam(user_id):
        return

    if update.effective_chat.type in ("group", "supergroup"):
        db.add_group(update.effective_chat.id)

    db_user = db.get_or_create_user(user_id, username)
    accounts = db_user.get("bank_accounts", [])

    if not accounts:
        await update.message.reply_text("❌ You have no bank accounts. Use /mybankaccount to open one.")
        return

    context.user_data["withdraw_step"] = "select_account"
    context.user_data["withdraw_accounts"] = accounts

    lines = ["🏦 <b>Select account to withdraw from:</b>\n"]
    for i, acc in enumerate(accounts, 1):
        last4 = str(acc.get("account_number", "????"))[-4:]
        lines.append(f"{i}. {esc(acc.get('bank_name', 'Bank'))} — ****{last4} — Balance: {acc.get('balance', 0):,}")

    lines.append("\nReply with the account number (1, 2, etc):")
    await update.message.reply_text("\n".join(lines), parse_mode="HTML")


async def withdraw_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Multi-step withdraw flow handler."""
    step = context.user_data.get("withdraw_step")
    if not step:
        return

    user_id = update.effective_user.id
    username = update.effective_user.username or update.effective_user.first_name or str(user_id)
    text = update.message.text.strip()

    if step == "select_account":
        accounts = context.user_data.get("withdraw_accounts", [])
        try:
            idx = int(text) - 1
            if idx < 0 or idx >= len(accounts):
                raise ValueError
        except ValueError:
            await update.message.reply_text("❌ Invalid selection.")
            return
        context.user_data["withdraw_account"] = accounts[idx]
        context.user_data["withdraw_step"] = "enter_pin"
        await update.message.reply_text("🔑 Enter your 4-digit PIN:")

    elif step == "enter_pin":
        acc = context.user_data.get("withdraw_account")
        if not acc:
            context.user_data.pop("withdraw_step", None)
            return
        if text != acc.get("pin", ""):
            await update.message.reply_text("❌ Incorrect PIN. Withdrawal cancelled.")
            context.user_data.pop("withdraw_step", None)
            context.user_data.pop("withdraw_account", None)
            return
        context.user_data["withdraw_step"] = "enter_amount"
        await update.message.reply_text(f"💰 Enter amount to withdraw (available: {acc.get('balance', 0):,} coins):")

    elif step == "enter_amount":
        acc = context.user_data.get("withdraw_account")
        if not acc:
            context.user_data.pop("withdraw_step", None)
            return
        amount = parse_positive_int(text)
        if amount is None or amount > acc.get("balance", 0):
            await update.message.reply_text(f"❌ Invalid amount. Available: {acc.get('balance', 0):,}")
            return

        db_user = db.get_or_create_user(user_id, username)
        accounts = db_user.get("bank_accounts", [])
        for a in accounts:
            if a.get("account_id") == acc.get("account_id"):
                a["balance"] = a.get("balance", 0) - amount
                break
        db_user["bank_accounts"] = accounts
        db_user["balance"] = db_user.get("balance", 0) + amount
        db.save_user(db_user)

        context.user_data.pop("withdraw_step", None)
        context.user_data.pop("withdraw_account", None)
        context.user_data.pop("withdraw_accounts", None)

        await update.message.reply_text(
            f"✅ <b>Withdrawal successful!</b>\n"
            f"💰 Withdrew <b>{amount:,}</b> coins\n"
            f"💼 Wallet balance: <b>{db_user['balance']:,}</b>",
            parse_mode="HTML",
        )
        logger.info(f"User {user_id} withdrew {amount} from bank")
