"""Handler for /leaderboard."""

import logging
from telegram import Update
from telegram.ext import ContextTypes
from telegram.error import BadRequest

from kairumi_inokaze import database as db
from kairumi_inokaze.middlewares import check_anti_spam
from kairumi_inokaze.utils.keyboards import leaderboard_keyboard
from kairumi_inokaze.utils.messages import (
    leaderboard_richest, leaderboard_kills, leaderboard_robs, esc
)

logger = logging.getLogger(__name__)


async def leaderboard_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/leaderboard — show leaderboard menu."""
    if update.message is None:
        return

    user = update.effective_user
    if await check_anti_spam(user.id):
        return

    if update.effective_chat.type in ("group", "supergroup"):
        db.add_group(update.effective_chat.id)

    await update.message.reply_text(
        "🏆 <b>Leaderboard</b>\n━━━━━━━━━━━━━━\nSelect a category:",
        parse_mode="HTML",
        reply_markup=leaderboard_keyboard(),
    )


async def leaderboard_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle leaderboard category selection."""
    query = update.callback_query
    await query.answer()

    category = query.data.split(":")[1]
    users = db.get_all_users()

    if category == "richest":
        sorted_users = sorted(users, key=lambda u: u.get("balance", 0), reverse=True)
        text = leaderboard_richest(sorted_users)
    elif category == "kills":
        sorted_users = sorted(users, key=lambda u: u.get("kills", 0), reverse=True)
        text = leaderboard_kills(sorted_users)
    elif category == "robs":
        sorted_users = sorted(users, key=lambda u: u.get("robs", 0), reverse=True)
        text = leaderboard_robs(sorted_users)
    elif category == "ranks":
        rank_values = {r["name"]: r["price"] for r in db.get_ranks_shop()}
        sorted_users = sorted(users, key=lambda u: rank_values.get(u.get("rank", "Rookie"), 0), reverse=True)
        lines = ["⭐ <b>Top 10 Most Expensive Ranks</b>\n━━━━━━━━━━━━━━━━━━━━\n"]
        for i, u in enumerate(sorted_users[:10], 1):
            lines.append(f"{i}. @{esc(u.get('username', '?'))} — <b>{esc(u.get('rank', 'Rookie'))}</b>")
        text = "\n".join(lines)
    elif category == "companies":
        companies = db.get_companies()
        sorted_companies = sorted(companies, key=lambda c: c.get("revenue", 0), reverse=True)
        lines = ["🏭 <b>Top 10 Most Profitable Companies</b>\n━━━━━━━━━━━━━━━━━━━━\n"]
        for i, c in enumerate(sorted_companies[:10], 1):
            lines.append(f"{i}. {esc(c.get('name', '?'))} — <b>{c.get('revenue', 0):,}</b>/week")
        text = "\n".join(lines)
    elif category == "titles":
        sorted_users = sorted(users, key=lambda u: u.get("title", "None") != "None", reverse=True)
        lines = ["🎖 <b>Top 10 Unique Titles</b>\n━━━━━━━━━━━━━━━━━━━━\n"]
        for i, u in enumerate(sorted_users[:10], 1):
            lines.append(f"{i}. @{esc(u.get('username', '?'))} — <b>{esc(u.get('title', 'None'))}</b>")
        text = "\n".join(lines)
    else:
        text = "❌ Unknown category."

    try:
        await query.edit_message_text(text, parse_mode="HTML", reply_markup=leaderboard_keyboard())
    except BadRequest as e:
        if "not modified" in str(e).lower():
            pass  # User clicked same button again — ignore
        else:
            logger.error(f"Leaderboard edit error: {e}")
