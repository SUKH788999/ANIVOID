import os

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")

MAIN_ADMIN_ID = 7036768966
ADMIN_IDS = [7036768966]

FORCE_JOIN_LINK = "https://t.me/+mkZFEP8IJOBkYzZl"
FORCE_JOIN_ID = "@kairumiinokaze_verify"

FLASK_PORT = 5000

DAILY_CLAIM_AMOUNT = 800
DAILY_CLAIM_COOLDOWN = 86400

ROB_COOLDOWN = 3600
KILL_COOLDOWN = 21600

ROB_SUCCESS_CHANCE = 0.50
KILL_REWARD = 750

KILL_DEAD_DAYS = 3

AUCTION_FEE_PERCENT = 5
AUCTION_MIN_INCREMENT = 50

AD_BROADCAST_INTERVAL = 25200

PREMIUM_PLANS = [
    {"label": "1 Day", "days": 1, "price": 2000},
    {"label": "3 Days", "days": 3, "price": 6500},
    {"label": "7 Days", "days": 7, "price": 13500},
    {"label": "13 Days", "days": 13, "price": 23500},
    {"label": "24 Days", "days": 24, "price": 57000},
    {"label": "27 Days", "days": 27, "price": 77777},
    {"label": "30 Days", "days": 30, "price": 100000},
]

PROTECTION_PLANS = [
    {"label": "1 Day", "days": 1, "price": 1000},
    {"label": "2 Days", "days": 2, "price": 2000},
    {"label": "3 Days", "days": 3, "price": 3000},
    {"label": "4 Days", "days": 4, "price": 4000},
]

DEFAULT_BALANCE = 1000
DEFAULT_RANK = "Rookie"
DEFAULT_TITLE = "None"
