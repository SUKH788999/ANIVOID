"""All InlineKeyboard and ReplyKeyboard builders."""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from kairumi_inokaze.config import (
    FORCE_JOIN_LINK,
    PREMIUM_PLANS,
    PROTECTION_PLANS,
)


def main_menu_keyboard() -> ReplyKeyboardMarkup:
    """Reply keyboard for main menu."""
    buttons = [
        ["💰 Balance", "🎁 Daily Claim"],
        ["🏆 Leaderboard", "🛍 Shop"],
        ["🔨 Auction", "🏭 My Company"],
        ["📖 Help", "🎒 Collection"],
    ]
    return ReplyKeyboardMarkup(buttons, resize_keyboard=True)


def force_join_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔗 JOIN GROUP", url=FORCE_JOIN_LINK)],
        [InlineKeyboardButton("✅ VERIFY", callback_data="verify_join")],
    ])


def verify_button() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ VERIFY", callback_data="verify_join")],
    ])


def premium_keyboard() -> InlineKeyboardMarkup:
    rows = []
    for i, plan in enumerate(PREMIUM_PLANS):
        rows.append([
            InlineKeyboardButton(
                f"⚡ {plan['label']} — {plan['price']:,} coins",
                callback_data=f"premium_buy:{i}",
            )
        ])
    return InlineKeyboardMarkup(rows)


def protection_keyboard() -> InlineKeyboardMarkup:
    rows = []
    for i, plan in enumerate(PROTECTION_PLANS):
        rows.append([
            InlineKeyboardButton(
                f"🛡 {plan['label']} — {plan['price']:,} coins",
                callback_data=f"protect_buy:{i}",
            )
        ])
    return InlineKeyboardMarkup(rows)


def leaderboard_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💰 Richest Players", callback_data="lb:richest")],
        [InlineKeyboardButton("⭐ Most Expensive Rank", callback_data="lb:ranks")],
        [InlineKeyboardButton("🏭 Most Profitable Companies", callback_data="lb:companies")],
        [InlineKeyboardButton("💀 Most Kills", callback_data="lb:kills")],
        [InlineKeyboardButton("🦹 Most Robs", callback_data="lb:robs")],
        [InlineKeyboardButton("🎖 Most Unique Titles", callback_data="lb:titles")],
    ])


def gifts_keyboard(target_username: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"1 💊 Revive Friend — 500 coins", callback_data="gift:revive")],
        [InlineKeyboardButton(f"2 💰 Send Coins", callback_data="gift:coins")],
        [InlineKeyboardButton(f"3 😂 Send Emoji Pack", callback_data="gift:emoji")],
        [InlineKeyboardButton(f"4 ⭐ Send Rank", callback_data="gift:rank")],
        [InlineKeyboardButton(f"5 🎖 Send Title", callback_data="gift:title")],
        [InlineKeyboardButton(f"6 👑 Send Premium", callback_data="gift:premium")],
        [InlineKeyboardButton(f"7 🎒 Inventory (Coming Soon)", callback_data="gift:inventory")],
    ])


def auction_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🛒 Browse & Bid Active Auctions", callback_data="auction:browse")],
        [InlineKeyboardButton("📦 Sell an Item", callback_data="auction:sell")],
    ])


def cars_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🛒 Browse Cars", callback_data="cars:browse")],
        [InlineKeyboardButton("💼 My Cars", callback_data="cars:mine")],
        [InlineKeyboardButton("💸 Sell My Car", callback_data="cars:sell")],
    ])


def buildings_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🛒 Browse Buildings", callback_data="buildings:browse")],
        [InlineKeyboardButton("🏠 My Buildings", callback_data="buildings:mine")],
        [InlineKeyboardButton("📊 Use for Company", callback_data="buildings:company")],
    ])


def collection_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📦 Inventory", callback_data="collection:inventory")],
        [InlineKeyboardButton("🚗 My Cars", callback_data="collection:cars")],
        [InlineKeyboardButton("🏠 My Buildings", callback_data="collection:buildings")],
    ])


def help_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("❓ I Have an Issue", callback_data="help:issue")],
    ])


def admin_panel_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💰 Add/Remove Coins", callback_data="admin:coins")],
        [InlineKeyboardButton("🎖 Add Title", callback_data="admin:title")],
        [InlineKeyboardButton("⭐ Add Rank", callback_data="admin:rank")],
        [InlineKeyboardButton("🔄 Reset User", callback_data="admin:reset")],
        [InlineKeyboardButton("🚫 Ban / Unban User", callback_data="admin:ban")],
        [InlineKeyboardButton("🏭 Add/Remove Company", callback_data="admin:company")],
        [InlineKeyboardButton("🏦 Add/Remove Bank", callback_data="admin:bank")],
        [InlineKeyboardButton("👑 Add/Remove Admin", callback_data="admin:admin")],
        [InlineKeyboardButton("🚗 Add Car to Shop", callback_data="admin:car")],
        [InlineKeyboardButton("🏗 Add Building to Shop", callback_data="admin:building")],
    ])


def bank_account_keyboard(accounts: list) -> InlineKeyboardMarkup:
    rows = []
    for acc in accounts:
        last4 = str(acc.get("account_number", "????"))[-4:]
        rows.append([
            InlineKeyboardButton(
                f"🏦 {acc.get('bank_name', 'Bank')} — ****{last4}",
                callback_data=f"bank:view:{acc.get('account_id', '')}",
            )
        ])
    rows.append([InlineKeyboardButton("➕ Open New Account", callback_data="bank:open")])
    return InlineKeyboardMarkup(rows)


def company_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✏️ Change Name", callback_data="company:rename")],
        [InlineKeyboardButton("📊 View Investors", callback_data="company:investors")],
        [InlineKeyboardButton("💼 Manage Employees", callback_data="company:employees")],
    ])


def ranks_keyboard(ranks: list, page: int = 0) -> InlineKeyboardMarkup:
    rows = []
    page_size = 5
    start = page * page_size
    chunk = ranks[start: start + page_size]
    for i, r in enumerate(chunk):
        rows.append([
            InlineKeyboardButton(
                f"⭐ {r['name']} — {r['price']:,} coins",
                callback_data=f"rank_buy:{start + i}",
            )
        ])
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("◀️ Prev", callback_data=f"ranks_page:{page - 1}"))
    if start + page_size < len(ranks):
        nav.append(InlineKeyboardButton("Next ▶️", callback_data=f"ranks_page:{page + 1}"))
    if nav:
        rows.append(nav)
    return InlineKeyboardMarkup(rows)


def titles_keyboard(titles: list, page: int = 0) -> InlineKeyboardMarkup:
    rows = []
    page_size = 5
    start = page * page_size
    chunk = titles[start: start + page_size]
    for i, t in enumerate(chunk):
        rows.append([
            InlineKeyboardButton(
                f"🎖 {t['name']} — {t['price']:,} coins",
                callback_data=f"title_buy:{start + i}",
            )
        ])
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("◀️ Prev", callback_data=f"titles_page:{page - 1}"))
    if start + page_size < len(titles):
        nav.append(InlineKeyboardButton("Next ▶️", callback_data=f"titles_page:{page + 1}"))
    if nav:
        rows.append(nav)
    return InlineKeyboardMarkup(rows)


def anime_request_keyboard(req_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Mark Complete", callback_data=f"req:complete:{req_id}"),
            InlineKeyboardButton("❌ Reject", callback_data=f"req:reject:{req_id}"),
        ]
    ])


def partnership_keyboard(user_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Accept", callback_data=f"partner:accept:{user_id}"),
            InlineKeyboardButton("❌ Reject", callback_data=f"partner:reject:{user_id}"),
        ]
    ])


def president_vote_keyboard(candidates: list) -> InlineKeyboardMarkup:
    rows = []
    for c in candidates:
        rows.append([
            InlineKeyboardButton(
                f"🗳 Vote for @{c.get('username', c['user_id'])}",
                callback_data=f"president:vote:{c['user_id']}",
            )
        ])
    return InlineKeyboardMarkup(rows)
