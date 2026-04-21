"""Handler for /president — voting and presidency system."""

import logging
from datetime import datetime, timedelta, timezone
from telegram import Update
from telegram.ext import ContextTypes
from telegram.error import BadRequest

from kairumi_inokaze import database as db
from kairumi_inokaze.middlewares import check_anti_spam
from kairumi_inokaze.utils.keyboards import president_vote_keyboard
from kairumi_inokaze.utils.messages import president_status, esc

logger = logging.getLogger(__name__)


async def president_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/president — show current president or start election."""
    if update.message is None:
        return

    user = update.effective_user
    user_id = user.id
    username = user.username or user.first_name or str(user_id)

    if await check_anti_spam(user_id):
        return

    if update.effective_chat.type in ("group", "supergroup"):
        db.add_group(update.effective_chat.id)

    president = db.get_president()
    voting = db.get_president_voting()

    # Active voting
    if voting and voting.get("active"):
        candidates = voting.get("candidates", [])
        ends_at = voting.get("ends_at", "Unknown")

        if len(candidates) < 2:
            existing_ids = [c["user_id"] for c in candidates]
            if user_id not in existing_ids:
                candidates.append({
                    "user_id": user_id,
                    "username": username,
                    "votes": 0,
                })
                voting["candidates"] = candidates
                db.set_president_voting(voting)
                candidate_names = ", ".join(f"@{esc(c.get('username', '?'))}" for c in candidates)
                await update.message.reply_text(
                    f"🎖 @{esc(username)} has entered the presidential race!\n"
                    f"📅 Voting ends: {ends_at[:10]}\n\n"
                    f"Candidates: {candidate_names}",
                    parse_mode="HTML",
                    reply_markup=president_vote_keyboard(candidates),
                )
                return

        await update.message.reply_text(
            f"🗳 <b>Presidential Election Active!</b>\n\n"
            f"Cast your vote below:\n📅 Voting ends: {ends_at[:10]}",
            parse_mode="HTML",
            reply_markup=president_vote_keyboard(candidates),
        )
        return

    # Show current president or start new election
    if president:
        now = datetime.now(timezone.utc)
        try:
            expires = datetime.fromisoformat(president.get("expires_at", ""))
            if expires.tzinfo is None:
                expires = expires.replace(tzinfo=timezone.utc)
            if now < expires:
                await update.message.reply_text(president_status(president), parse_mode="HTML")
                return
        except Exception:
            pass

    # Start new election
    ends_at = (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat()
    voting = {
        "active": True,
        "candidates": [{
            "user_id": user_id,
            "username": username,
            "votes": 0,
        }],
        "ends_at": ends_at,
    }
    db.set_president_voting(voting)

    await update.message.reply_text(
        f"🗳 <b>Presidential Election Started!</b>\n\n"
        f"@{esc(username)} has entered the race!\n"
        f"📅 Voting ends in 24 hours.\n\n"
        f"One more candidate needed. Type /president to join!",
        parse_mode="HTML",
    )
    logger.info(f"User {user_id} started presidential election")


async def president_vote_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle vote button press."""
    query = update.callback_query
    await query.answer()

    voter_id = update.effective_user.id
    candidate_id = int(query.data.split(":")[2])

    voting = db.get_president_voting()
    if not voting or not voting.get("active"):
        await query.edit_message_text("❌ No active election.")
        return

    if voter_id == candidate_id:
        await query.answer("❌ You can't vote for yourself!", show_alert=True)
        return

    candidates = voting.get("candidates", [])
    for c in candidates:
        if c["user_id"] == candidate_id:
            c["votes"] = c.get("votes", 0) + 1
            break
    voting["candidates"] = candidates
    db.set_president_voting(voting)

    standings = "\n".join(
        f"@{esc(c.get('username', '?'))} — {c.get('votes', 0)} votes"
        for c in candidates
    )

    try:
        await query.edit_message_text(
            f"✅ <b>Vote cast!</b>\n\nCurrent standings:\n{standings}",
            parse_mode="HTML",
        )
    except BadRequest as e:
        if "not modified" in str(e).lower():
            pass
        else:
            logger.error(f"President vote edit error: {e}")

    logger.info(f"User {voter_id} voted for {candidate_id}")
