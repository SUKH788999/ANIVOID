"""All formatted message templates — uses HTML parse mode for safety."""

import re
from datetime import datetime, timezone
from typing import Optional


# ─── Escape helpers ──────────────────────────────────────────────────────────

def esc(text: str) -> str:
    """Escape a string for Telegram HTML parse mode."""
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def _bool_display(val: bool) -> str:
    return "✅ Yes" if val else "❌ No"


def _expiry_display(expiry_iso: Optional[str]) -> str:
    if not expiry_iso:
        return "❌ No"
    try:
        dt = datetime.fromisoformat(expiry_iso)
        now = datetime.now(timezone.utc)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        if dt > now:
            return f"✅ Until {dt.strftime('%Y-%m-%d')}"
        return "❌ Expired"
    except Exception:
        return "❌ No"


# ─── Message templates ───────────────────────────────────────────────────────

def welcome_message(username: str, user: dict) -> str:
    return (
        f"🌸 <b>Welcome to Kairumi Inokaze, {esc(username)}!</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"💰 Balance: <b>{user.get('balance', 1000):,}</b> coins\n"
        f"⭐ Rank: <b>{esc(user.get('rank', 'Rookie'))}</b>\n"
        f"🎖 Title: <b>{esc(user.get('title', 'None'))}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"Use /help to see all commands"
    )


def balance_card(user: dict) -> str:
    uname = esc(user.get("username", "Unknown"))
    return (
        f"┌─────────────────────────┐\n"
        f"│  👤 @{uname}\n"
        f"├─────────────────────────┤\n"
        f"│ 💰 Balance:  {user.get('balance', 0):,}\n"
        f"│ 🏦 Bank:     {user.get('bank_balance', 0):,}\n"
        f"│ ⭐ Rank:     {esc(user.get('rank', 'Rookie'))}\n"
        f"│ 🎖 Title:    {esc(user.get('title', 'None'))}\n"
        f"│ 👑 Premium:  {_bool_display(user.get('premium', False))}\n"
        f"│ 🛡 Protect:  {_expiry_display(user.get('protect_expiry'))}\n"
        f"│ 💀 Dead:     {_bool_display(user.get('dead_status', False))}\n"
        f"└─────────────────────────┘"
    )


def claim_cooldown_msg(remaining: float) -> str:
    s = int(remaining)
    h = s // 3600
    m = (s % 3600) // 60
    sec = s % 60
    return f"⏳ Come back in <b>{h}h {m}m {sec}s</b>"


def claim_success_msg(amount: int, new_balance: int) -> str:
    return (
        f"✅ <b>Daily reward claimed!</b>\n"
        f"💰 +{amount:,} coins added to your balance\n"
        f"💼 New Balance: <b>{new_balance:,}</b>"
    )


def rob_success_msg(robber: str, target: str, amount: int) -> str:
    return (
        f"🦹 <b>Rob successful!</b>\n"
        f"💰 You stole <b>{amount:,}</b> coins from @{esc(target)}!"
    )


def rob_fail_msg() -> str:
    return "😅 You got caught! Better luck next time."


def rob_protected_msg(target: str) -> str:
    return f"🛡 @{esc(target)} is protected! You cannot rob them."


def rob_dead_msg() -> str:
    return "💀 You cannot rob while you are dead!"


def rob_target_dead_msg(target: str) -> str:
    return f"💀 @{esc(target)} is dead! No fun robbing corpses."


def kill_success_msg(killer: str, target: str, reward: int) -> str:
    return (
        f"💀 @{esc(target)} has been killed by @{esc(killer)}!\n"
        f"⚰️ They will revive in 3 days.\n"
        f"🏆 @{esc(killer)} earned <b>{reward:,}</b> coins!"
    )


def kill_protected_msg(target: str) -> str:
    return f"🛡 @{esc(target)} is protected! You can't kill them."


def kill_dead_msg() -> str:
    return "💀 You cannot kill while you are dead!"


def pay_success_msg(sender: str, target: str, amount: int, new_balance: int) -> str:
    return (
        f"💸 <b>Payment Successful!</b>\n"
        f"📤 You sent <b>{amount:,}</b> coins to @{esc(target)}\n"
        f"💰 Your new balance: <b>{new_balance:,}</b>"
    )


def help_text() -> str:
    return (
        "📖 <b>Kairumi Inokaze — Help Menu</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "🎮 <b>ECONOMY</b>\n"
        "/bal — Your profile card\n"
        "/claim — Daily 800 coins\n"
        "/pay — Send coins (reply)\n"
        "/rob — Rob someone (reply)\n"
        "/kill — Kill someone (reply)\n"
        "/protect — Buy protection\n\n"
        "🎁 <b>SOCIAL</b>\n"
        "/gifts — Send gifts (reply)\n"
        "/premium — Premium plans\n"
        "/ranks — Rank shop\n"
        "/titles — Title shop\n\n"
        "🏆 <b>LEADERBOARD</b>\n"
        "/leaderboard — Top players\n\n"
        "🏦 <b>BANKING</b>\n"
        "/banks — View banks\n"
        "/mybankaccount — My accounts\n"
        "/withdraw — Withdraw funds\n\n"
        "🔨 <b>AUCTION</b>\n"
        "/auction — Auction house\n\n"
        "🚗 <b>ASSETS</b>\n"
        "/cars — Car dealership\n"
        "/buildings — Real estate\n"
        "/collection — Your collection\n\n"
        "🏭 <b>COMPANY</b>\n"
        "/mycompany — Your company\n"
        "/invest — Investment market\n"
        "/employees — Your employees\n\n"
        "👑 <b>PRESIDENT</b>\n"
        "/president — President system\n\n"
        "🎌 <b>ANIME</b>\n"
        "/roa — Request anime\n\n"
        "🤝 <b>OTHER</b>\n"
        "/partnershipRequest — Partner request\n"
        "/help — This menu"
    )


def leaderboard_richest(users: list) -> str:
    lines = ["🏆 <b>Top 10 Richest Players</b>\n━━━━━━━━━━━━━━━━━━━━\n"]
    for i, u in enumerate(users[:10], 1):
        lines.append(f"{i}. @{esc(u.get('username', '?'))} — <b>{u.get('balance', 0):,}</b> coins")
    return "\n".join(lines)


def leaderboard_kills(users: list) -> str:
    lines = ["💀 <b>Top 10 Most Kills</b>\n━━━━━━━━━━━━━━━━━━━━\n"]
    for i, u in enumerate(users[:10], 1):
        lines.append(f"{i}. @{esc(u.get('username', '?'))} — <b>{u.get('kills', 0)}</b> kills")
    return "\n".join(lines)


def leaderboard_robs(users: list) -> str:
    lines = ["🦹 <b>Top 10 Most Robs</b>\n━━━━━━━━━━━━━━━━━━━━\n"]
    for i, u in enumerate(users[:10], 1):
        lines.append(f"{i}. @{esc(u.get('username', '?'))} — <b>{u.get('robs', 0)}</b> robs")
    return "\n".join(lines)


def president_status(p: dict) -> str:
    return (
        f"👑 <b>Current President:</b> @{esc(p.get('username', '?'))}\n"
        f"📅 Term ends: {esc(p.get('expires_at', 'Unknown')[:10])}\n"
        f"🗳 Votes received: <b>{p.get('votes', 0)}</b>"
    )
