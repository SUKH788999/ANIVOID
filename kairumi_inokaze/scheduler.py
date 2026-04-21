"""Scheduled jobs — auto revive, ad broadcast, auction expiry, premium/protect expiry, salaries."""

import logging
import time
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

_app = None


def set_app(application) -> None:
    """Store reference to the PTB Application for sending messages."""
    global _app
    _app = application


async def auto_revive_job(context) -> None:
    """Revive users whose dead_until timestamp has passed."""
    from kairumi_inokaze import database as db
    users = db.get_all_users()
    now = datetime.now(timezone.utc)
    revived = 0

    for user in users:
        if not user.get("dead_status", False):
            continue
        dead_until = user.get("dead_until")
        if not dead_until:
            continue
        try:
            dt = datetime.fromisoformat(dead_until)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            if now >= dt:
                user["dead_status"] = False
                user["dead_until"] = None
                db.save_user(user)
                revived += 1
                try:
                    await context.bot.send_message(
                        user["user_id"],
                        "💊 <b>You have been revived!</b> Welcome back to the living.",
                        parse_mode="HTML",
                    )
                except Exception:
                    pass
        except Exception as e:
            logger.error(f"Revive check error for user {user.get('user_id')}: {e}")

    if revived:
        logger.info(f"Auto-revived {revived} users")


async def premium_expiry_job(context) -> None:
    """Downgrade expired premium users."""
    from kairumi_inokaze import database as db
    users = db.get_all_users()
    now = datetime.now(timezone.utc)
    expired = 0

    for user in users:
        if not user.get("premium"):
            continue
        expiry = user.get("premium_expiry")
        if not expiry:
            continue
        try:
            dt = datetime.fromisoformat(expiry)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            if now >= dt:
                user["premium"] = False
                user["premium_expiry"] = None
                db.save_user(user)
                expired += 1
                try:
                    await context.bot.send_message(
                        user["user_id"],
                        "⚠️ Your <b>Premium</b> has expired! Use /premium to renew.",
                        parse_mode="HTML",
                    )
                except Exception:
                    pass
        except Exception as e:
            logger.error(f"Premium expiry error for {user.get('user_id')}: {e}")

    if expired:
        logger.info(f"Expired premium for {expired} users")


async def protect_expiry_job(context) -> None:
    """Clean up expired protection records."""
    from kairumi_inokaze import database as db
    users = db.get_all_users()
    now = datetime.now(timezone.utc)
    cleared = 0

    for user in users:
        expiry = user.get("protect_expiry")
        if not expiry:
            continue
        try:
            dt = datetime.fromisoformat(expiry)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            if now >= dt:
                user["protect_expiry"] = None
                db.save_user(user)
                cleared += 1
        except Exception:
            pass

    if cleared:
        logger.info(f"Cleared protection for {cleared} users")


async def auction_expiry_job(context) -> None:
    """Check and settle expired auctions."""
    from kairumi_inokaze import database as db
    auctions = db.get_active_auctions()
    now = datetime.now(timezone.utc)
    remaining = []

    for auction in auctions:
        try:
            ends_at = datetime.fromisoformat(auction.get("ends_at", ""))
            if ends_at.tzinfo is None:
                ends_at = ends_at.replace(tzinfo=timezone.utc)

            if now < ends_at:
                remaining.append(auction)
                continue

            # Auction ended
            bidder_id = auction.get("bidder_id")
            if bidder_id:
                final_bid = auction.get("current_bid", 0)
                fee = int(final_bid * (5 / 100))
                paid = final_bid + fee

                winner = db.get_user(bidder_id)
                if winner and winner.get("balance", 0) >= paid:
                    winner["balance"] -= paid
                    db.save_user(winner)

                    seller_id = auction.get("submitted_by")
                    if seller_id:
                        seller = db.get_user(seller_id)
                        if seller:
                            seller["balance"] = seller.get("balance", 0) + final_bid
                            db.save_user(seller)

                    try:
                        await context.bot.send_message(
                            bidder_id,
                            f"🎉 <b>Auction won!</b>\n📦 {auction.get('item', 'Item')}\n💰 Final price: {final_bid:,} coins (+{fee:,} fee)",
                            parse_mode="HTML",
                        )
                    except Exception:
                        pass
                else:
                    logger.warning(f"Auction winner {bidder_id} cannot afford {paid}")
            else:
                logger.info(f"Auction {auction.get('item_id')} ended with no bids")

        except Exception as e:
            logger.error(f"Auction expiry error: {e}")

    db.save_active_auctions(remaining)


async def ad_broadcast_job(context) -> None:
    """Broadcast the current ad to all groups every 7 hours."""
    from kairumi_inokaze import database as db
    from kairumi_inokaze.config import AD_BROADCAST_INTERVAL

    last_sent = db.get_ad_last_sent()
    now = time.time()

    if last_sent and (now - last_sent) < AD_BROADCAST_INTERVAL:
        return

    from kairumi_inokaze.handlers.ads import _broadcast_ad
    await _broadcast_ad(context)


async def salary_payment_job(context) -> None:
    """Weekly payroll deduction for all companies."""
    from kairumi_inokaze import database as db
    companies = db.get_companies()

    for company in companies:
        owner_id = company.get("owner_id")
        if not owner_id:
            continue

        employees = company.get("employees", [])
        total_salary = sum(e.get("salary", 0) for e in employees)
        if total_salary == 0:
            continue

        owner = db.get_user(owner_id)
        if not owner:
            continue

        if owner.get("balance", 0) >= total_salary:
            owner["balance"] -= total_salary
            db.save_user(owner)
            logger.info(f"Paid {total_salary} salary for company {company.get('name')} owner {owner_id}")
        else:
            # Mark bankrupt warning
            logger.warning(f"Company {company.get('name')} owner {owner_id} can't afford salary of {total_salary}")
            try:
                await context.bot.send_message(
                    owner_id,
                    f"⚠️ <b>Payroll Alert!</b>\nYour company <b>{company.get('name', 'Company')}</b> cannot afford the weekly payroll of <b>{total_salary:,}</b> coins!\n\nAdd coins before next cycle to avoid bankruptcy.",
                    parse_mode="HTML",
                )
            except Exception:
                pass


async def president_election_job(context) -> None:
    """Finalize presidential elections when voting period ends."""
    from kairumi_inokaze import database as db
    voting = db.get_president_voting()
    if not voting or not voting.get("active"):
        return

    now = datetime.now(timezone.utc)
    ends_at_str = voting.get("ends_at", "")
    try:
        ends_at = datetime.fromisoformat(ends_at_str)
        if ends_at.tzinfo is None:
            ends_at = ends_at.replace(tzinfo=timezone.utc)
        if now < ends_at:
            return
    except Exception:
        return

    candidates = voting.get("candidates", [])
    if not candidates:
        voting["active"] = False
        db.set_president_voting(voting)
        return

    winner = max(candidates, key=lambda c: c.get("votes", 0))
    from datetime import timedelta
    term_end = (now + timedelta(days=7)).isoformat()

    president = {
        "user_id": winner["user_id"],
        "username": winner.get("username", str(winner["user_id"])),
        "elected_at": now.isoformat(),
        "expires_at": term_end,
        "votes": winner.get("votes", 0),
    }
    db.set_president(president)
    voting["active"] = False
    db.set_president_voting(voting)

    try:
        await context.bot.send_message(
            winner["user_id"],
            f"👑 <b>Congratulations!</b> You are now the President!\n"
            f"📅 Your term ends: {term_end[:10]}\n"
            f"🗳 Votes received: {winner.get('votes', 0)}",
            parse_mode="HTML",
        )
    except Exception:
        pass

    logger.info(f"President elected: {winner.get('username')} with {winner.get('votes', 0)} votes")


def setup_scheduler(application) -> None:
    """Register all scheduled jobs with PTB's JobQueue."""
    jq = application.job_queue
    if jq is None:
        logger.warning("JobQueue not available — scheduled jobs disabled")
        return

    jq.run_repeating(auto_revive_job, interval=3600, first=60, name="auto_revive")
    jq.run_repeating(premium_expiry_job, interval=3600, first=120, name="premium_expiry")
    jq.run_repeating(protect_expiry_job, interval=3600, first=180, name="protect_expiry")
    jq.run_repeating(auction_expiry_job, interval=300, first=60, name="auction_expiry")
    jq.run_repeating(ad_broadcast_job, interval=25200, first=300, name="ad_broadcast")
    jq.run_repeating(salary_payment_job, interval=604800, first=3600, name="salary_payment")
    jq.run_repeating(president_election_job, interval=3600, first=240, name="president_election")

    logger.info("All scheduled jobs registered")
