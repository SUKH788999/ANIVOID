"""Main entry point — starts Flask + Telegram bot."""

import asyncio
import logging
import sys

from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
)

from kairumi_inokaze.utils.logger import setup_logger
from kairumi_inokaze.config import BOT_TOKEN, FLASK_PORT
from kairumi_inokaze.flask_server import start_flask_thread
from kairumi_inokaze.scheduler import setup_scheduler

# Handlers
from kairumi_inokaze.handlers.start import start_handler, verify_callback
from kairumi_inokaze.handlers.balance import balance_handler
from kairumi_inokaze.handlers.claims import claim_handler
from kairumi_inokaze.handlers.economy import (
    pay_handler, rob_handler, kill_handler, protect_handler, protect_buy_callback
)
from kairumi_inokaze.handlers.premium import premium_handler, premium_buy_callback
from kairumi_inokaze.handlers.gifts import gifts_handler, gift_callback, gift_coins_message
from kairumi_inokaze.handlers.leaderboard import leaderboard_handler, leaderboard_callback
from kairumi_inokaze.handlers.help import help_handler, help_issue_callback, issue_message_handler
from kairumi_inokaze.handlers.bank import (
    banks_handler, my_bank_account_handler, bank_open_callback,
    withdraw_handler, withdraw_message_handler
)
from kairumi_inokaze.handlers.auction import auction_handler, auction_callback, auction_sell_message, bid_handler
from kairumi_inokaze.handlers.cars import cars_handler, cars_callback, sell_car_message
from kairumi_inokaze.handlers.buildings import buildings_handler, buildings_callback
from kairumi_inokaze.handlers.invest import invest_handler, invest_callback, invest_amount_message
from kairumi_inokaze.handlers.company import company_handler, company_callback, company_rename_message
from kairumi_inokaze.handlers.employees import employees_handler
from kairumi_inokaze.handlers.president import president_handler, president_vote_callback
from kairumi_inokaze.handlers.collection import collection_handler, collection_callback
from kairumi_inokaze.handlers.anime_request import (
    roa_handler, tr_handler, ric_handler, trc_handler, anime_request_callback
)
from kairumi_inokaze.handlers.partnership import (
    partnership_handler, partnership_message_handler, partnership_callback
)
from kairumi_inokaze.handlers.ads import ads_handler, ads_media_handler, broadcast_handler
from kairumi_inokaze.handlers.admin import admin_handler, admin_callback, admin_input_message
from kairumi_inokaze.handlers.ranks import ranks_handler, ranks_page_callback, rank_buy_callback
from kairumi_inokaze.handlers.titles import titles_handler, titles_page_callback, title_buy_callback


setup_logger()
logger = logging.getLogger(__name__)


async def _global_error_handler(update: object, context) -> None:
    """Global error handler — logs all unhandled exceptions."""
    from telegram.error import BadRequest, NetworkError, TimedOut
    error = context.error

    if isinstance(error, BadRequest):
        if "not modified" in str(error).lower():
            return  # Ignore harmless "message not modified" errors
        logger.warning(f"BadRequest: {error}")
    elif isinstance(error, (NetworkError, TimedOut)):
        logger.warning(f"Network error: {error}")
    else:
        logger.error(f"Unhandled error: {error}", exc_info=error)


async def smart_reply_handler(update, context) -> None:
    """Handle non-command messages in private chat with OpenAI replies."""
    from kairumi_inokaze import database as db
    from kairumi_inokaze.utils.openai_helper import get_smart_reply
    from kairumi_inokaze.middlewares import check_anti_spam

    if update.message is None:
        return

    user = update.effective_user
    user_id = user.id
    username = user.username or user.first_name or str(user_id)

    if await check_anti_spam(user_id):
        return

    # Auto-collect groups
    if update.effective_chat and update.effective_chat.type in ("group", "supergroup"):
        db.add_group(update.effective_chat.id)
        return  # Don't reply in groups unless triggered

    # Private chat: smart reply
    if update.effective_chat.type == "private":
        text = update.message.text or ""
        if not text:
            return
        reply = await get_smart_reply(text, username)
        await update.message.reply_text(reply)


def build_application() -> Application:
    """Build and configure the PTB Application with all handlers."""
    if not BOT_TOKEN:
        logger.critical("BOT_TOKEN is not set! Cannot start bot.")
        sys.exit(1)

    app = Application.builder().token(BOT_TOKEN).build()

    # ── Command Handlers ──────────────────────────────────────────────────
    app.add_handler(CommandHandler("start", start_handler))
    app.add_handler(CommandHandler(["bal", "balance", "profile"], balance_handler))
    app.add_handler(CommandHandler("claim", claim_handler))
    app.add_handler(CommandHandler("pay", pay_handler))
    app.add_handler(CommandHandler("rob", rob_handler))
    app.add_handler(CommandHandler("kill", kill_handler))
    app.add_handler(CommandHandler("protect", protect_handler))
    app.add_handler(CommandHandler("premium", premium_handler))
    app.add_handler(CommandHandler("gifts", gifts_handler))
    app.add_handler(CommandHandler("leaderboard", leaderboard_handler))
    app.add_handler(CommandHandler("help", help_handler))
    app.add_handler(CommandHandler("banks", banks_handler))
    app.add_handler(CommandHandler("mybankaccount", my_bank_account_handler))
    app.add_handler(CommandHandler("withdraw", withdraw_handler))
    app.add_handler(CommandHandler("auction", auction_handler))
    app.add_handler(CommandHandler("bid", bid_handler))
    app.add_handler(CommandHandler("cars", cars_handler))
    app.add_handler(CommandHandler("buildings", buildings_handler))
    app.add_handler(CommandHandler("invest", invest_handler))
    app.add_handler(CommandHandler("mycompany", company_handler))
    app.add_handler(CommandHandler("employees", employees_handler))
    app.add_handler(CommandHandler(["President", "president"], president_handler))
    app.add_handler(CommandHandler("collection", collection_handler))
    app.add_handler(CommandHandler("roa", roa_handler))
    app.add_handler(CommandHandler("tr", tr_handler))
    app.add_handler(CommandHandler("ric", ric_handler))
    app.add_handler(CommandHandler("trc", trc_handler))
    app.add_handler(CommandHandler("partnershipRequest", partnership_handler))
    app.add_handler(CommandHandler("ranks", ranks_handler))
    app.add_handler(CommandHandler("titles", titles_handler))
    app.add_handler(CommandHandler("ads", ads_handler))
    app.add_handler(CommandHandler("broadcast", broadcast_handler))
    app.add_handler(CommandHandler("edit", admin_handler))

    # ── Callback Query Handlers ──────────────────────────────────────────
    app.add_handler(CallbackQueryHandler(verify_callback, pattern="^verify_join$"))
    app.add_handler(CallbackQueryHandler(protect_buy_callback, pattern="^protect_buy:"))
    app.add_handler(CallbackQueryHandler(premium_buy_callback, pattern="^premium_buy:"))
    app.add_handler(CallbackQueryHandler(gift_callback, pattern="^gift:"))
    app.add_handler(CallbackQueryHandler(leaderboard_callback, pattern="^lb:"))
    app.add_handler(CallbackQueryHandler(help_issue_callback, pattern="^help:issue$"))
    app.add_handler(CallbackQueryHandler(bank_open_callback, pattern="^bank:open$"))
    app.add_handler(CallbackQueryHandler(auction_callback, pattern="^auction:"))
    app.add_handler(CallbackQueryHandler(cars_callback, pattern="^cars:"))
    app.add_handler(CallbackQueryHandler(buildings_callback, pattern="^buildings:"))
    app.add_handler(CallbackQueryHandler(invest_callback, pattern="^invest:buy:"))
    app.add_handler(CallbackQueryHandler(company_callback, pattern="^company:"))
    app.add_handler(CallbackQueryHandler(collection_callback, pattern="^collection:"))
    app.add_handler(CallbackQueryHandler(president_vote_callback, pattern="^president:vote:"))
    app.add_handler(CallbackQueryHandler(anime_request_callback, pattern="^req:"))
    app.add_handler(CallbackQueryHandler(partnership_callback, pattern="^partner:"))
    app.add_handler(CallbackQueryHandler(rank_buy_callback, pattern="^rank_buy:"))
    app.add_handler(CallbackQueryHandler(ranks_page_callback, pattern="^ranks_page:"))
    app.add_handler(CallbackQueryHandler(title_buy_callback, pattern="^title_buy:"))
    app.add_handler(CallbackQueryHandler(titles_page_callback, pattern="^titles_page:"))
    app.add_handler(CallbackQueryHandler(admin_callback, pattern="^admin:"))

    # ── Message Handlers (multi-step flows + fallback) ─────────────────
    # Order matters: specific state-based handlers before generic fallback
    app.add_handler(MessageHandler(filters.PHOTO | filters.VIDEO | filters.ANIMATION, ads_media_handler))

    # Generic text message handler — handles all multi-step flows + AI fallback
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, _combined_text_handler))

    # ── Global Error Handler ──────────────────────────────────────────────
    app.add_error_handler(_global_error_handler)

    logger.info("All handlers registered")
    return app


async def _combined_text_handler(update, context) -> None:
    """Route text messages to the appropriate multi-step flow or AI fallback."""
    # Check each possible active conversation state
    if context.user_data.get("withdraw_step"):
        await withdraw_message_handler(update, context)
        return
    if context.user_data.get("auction_step"):
        await auction_sell_message(update, context)
        return
    if context.user_data.get("gift_type") == "coins":
        await gift_coins_message(update, context)
        return
    if context.user_data.get("sell_car_step"):
        await sell_car_message(update, context)
        return
    if context.user_data.get("invest_step"):
        await invest_amount_message(update, context)
        return
    if context.user_data.get("company_rename"):
        await company_rename_message(update, context)
        return
    if context.user_data.get("partner_step"):
        await partnership_message_handler(update, context)
        return
    if context.user_data.get("awaiting_issue"):
        await issue_message_handler(update, context)
        return
    if context.user_data.get("ads_step"):
        await ads_media_handler(update, context)
        return
    if context.user_data.get("admin_step"):
        await admin_input_message(update, context)
        return

    # AI fallback (private chats only)
    await smart_reply_handler(update, context)


def main() -> None:
    """Start Flask server and Telegram bot."""
    logger.info("🚀 Starting Kairumi Inokaze Bot...")

    # Start Flask in daemon thread
    start_flask_thread(FLASK_PORT)

    # Build and configure the bot
    app = build_application()

    # Setup scheduler jobs
    setup_scheduler(app)

    logger.info("✅ Bot is running. Polling for updates...")
    app.run_polling(
        allowed_updates=["message", "callback_query", "chat_member"],
        drop_pending_updates=True,
    )


if __name__ == "__main__":
    main()
