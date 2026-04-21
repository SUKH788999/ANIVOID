# Kairumi Inokaze — Telegram Bot

## Overview

A full production-level Telegram economy bot built with python-telegram-bot v20+ (async). Features a complete economy system, admin panel, AI replies via OpenAI, and a Flask uptime server for 24/7 deployment.

## Stack

- **Language**: Python 3.11
- **Telegram Library**: python-telegram-bot 20.7 (async, with job-queue)
- **Database**: Replit DB (key-value, via `replit` package)
- **Web Server**: Flask on port 5000 (UptimeRobot keep-alive)
- **AI**: OpenAI gpt-3.5-turbo for smart private replies
- **Scheduler**: APScheduler via PTB JobQueue

## Project Structure

```
kairumi_inokaze/
├── main.py           # Bot entry + handler registration
├── config.py         # Constants, tokens, admin IDs
├── database.py       # Replit DB abstraction layer
├── scheduler.py      # Timed jobs (revive, ads, auctions, premium)
├── middlewares.py    # Anti-spam, force-join, dead/protect checks
├── flask_server.py   # Flask keep-alive server
├── handlers/         # All command & callback handlers
│   ├── start.py       /start, force-join, verify
│   ├── balance.py     /bal
│   ├── economy.py     /pay, /rob, /kill, /protect
│   ├── claims.py      /claim
│   ├── premium.py     /premium shop
│   ├── gifts.py       /gifts (reply-based)
│   ├── leaderboard.py /leaderboard
│   ├── ranks.py       /ranks shop
│   ├── titles.py      /titles shop
│   ├── help.py        /help + issue reporter
│   ├── bank.py        /banks, /mybankaccount, /withdraw
│   ├── auction.py     /auction, /bid
│   ├── cars.py        /cars
│   ├── buildings.py   /buildings
│   ├── employees.py   /employees
│   ├── invest.py      /invest
│   ├── company.py     /mycompany
│   ├── president.py   /president
│   ├── collection.py  /collection
│   ├── anime_request.py /roa, /ric, /tr, /trc
│   ├── partnership.py /partnershipRequest
│   ├── ads.py         /ads, /broadcast
│   └── admin.py       /edit admin panel
└── utils/
    ├── keyboards.py   All keyboard builders
    ├── messages.py    Formatted message templates
    ├── cooldowns.py   Cooldown tracker
    ├── logger.py      Logging setup (console + bot.log)
    ├── openai_helper.py OpenAI integration
    └── validators.py  Input validation helpers
```

## Environment Secrets Required

- `BOT_TOKEN` — Telegram Bot Token (from @BotFather)
- `OPENAI_API_KEY` — OpenAI API Key

## Key Commands

- `python main.py` — Start the bot
- Bot also runs on workflow: "Kairumi Inokaze Bot"

## Scheduled Jobs

| Job | Interval | Purpose |
|-----|----------|---------|
| Auto Revive | 1h | Revive users whose dead timer expired |
| Premium Expiry | 1h | Downgrade expired premium users |
| Protect Expiry | 1h | Clear expired protections |
| Auction Expiry | 5min | Settle ended auctions |
| Ad Broadcast | 7h | Send ads to all groups |
| Salary Payment | Weekly | Deduct payroll from companies |
| President Election | 1h | Finalize ended elections |

## Features

- Force-join gate with inline verify button
- Economy: /bal, /claim (800/day), /pay, /rob (50% chance), /kill (3-day dead)
- Protection shop (1-4 days), Premium shop (7 tiers)
- Gifts: revive, coins, rank, title, premium transfer
- Leaderboard: richest, kills, robs, ranks, companies, titles
- Banking: open accounts, deposit, withdraw with PIN
- Auction house: list items, admin approves, bid notifications
- Cars & Buildings shops (admin-added)
- Company system: employees, investors, weekly payroll
- Investment market
- Presidential election (24h voting)
- Anime request system with admin approve/reject
- Partnership request flow
- Admin panel: add coins, ban/unban, reset, add cars/buildings/companies/banks
- Anti-spam middleware (5 msgs/3s → 30s mute)
- AI-powered private chat replies via OpenAI
- Auto-collect group IDs for ad broadcasting
