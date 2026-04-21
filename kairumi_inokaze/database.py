"""Database abstraction layer using Replit DB (key-value store)."""

import json
import logging
from datetime import datetime, timezone
from typing import Any, Optional

logger = logging.getLogger(__name__)

try:
    from replit import db as _replit_db
    _USE_REPLIT = True
except Exception:
    _USE_REPLIT = False
    _local_store: dict = {}


def _db_get(key: str) -> Any:
    if _USE_REPLIT:
        try:
            val = _replit_db.get(key)
            if val is None:
                return None
            if isinstance(val, str):
                try:
                    return json.loads(val)
                except Exception:
                    return val
            return val
        except Exception:
            return None
    return _local_store.get(key)


def _db_set(key: str, value: Any) -> None:
    if _USE_REPLIT:
        try:
            _replit_db[key] = json.dumps(value) if not isinstance(value, str) else value
        except Exception as e:
            logger.error(f"DB set error for {key}: {e}")
    else:
        _local_store[key] = value


def _db_delete(key: str) -> None:
    if _USE_REPLIT:
        try:
            del _replit_db[key]
        except Exception:
            pass
    else:
        _local_store.pop(key, None)


def _db_keys(prefix: str = "") -> list:
    if _USE_REPLIT:
        try:
            return list(_replit_db.prefix(prefix))
        except Exception:
            return []
    return [k for k in _local_store if k.startswith(prefix)]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _now_ts() -> float:
    return datetime.now(timezone.utc).timestamp()


# ─── USER ───────────────────────────────────────────────────────────────────

def get_user(user_id: int) -> Optional[dict]:
    """Return user record or None."""
    return _db_get(f"user:{user_id}")


def create_user(user_id: int, username: str) -> dict:
    """Create a new user with defaults and return the record."""
    user = {
        "user_id": user_id,
        "username": username or str(user_id),
        "balance": 1000,
        "bank_balance": 0,
        "rank": "Rookie",
        "title": "None",
        "premium": False,
        "premium_expiry": None,
        "protect_expiry": None,
        "dead_status": False,
        "dead_until": None,
        "kills": 0,
        "robs": 0,
        "inventory": [],
        "cars": [],
        "buildings": [],
        "joined_at": _now_iso(),
        "banned": False,
        "last_claim": None,
        "bank_accounts": [],
    }
    _db_set(f"user:{user_id}", user)
    logger.info(f"Created user {user_id} ({username})")
    return user


def get_or_create_user(user_id: int, username: str) -> dict:
    """Get existing user or create new one."""
    user = get_user(user_id)
    if user is None:
        user = create_user(user_id, username)
    else:
        if user.get("username") != username and username:
            user["username"] = username
            save_user(user)
    return user


def save_user(user: dict) -> None:
    """Persist a user record."""
    _db_set(f"user:{user['user_id']}", user)


def get_all_users() -> list:
    """Return all user records."""
    keys = _db_keys("user:")
    users = []
    for k in keys:
        u = _db_get(k)
        if u and isinstance(u, dict) and "user_id" in u:
            users.append(u)
    return users


def add_coins(user_id: int, amount: int) -> int:
    """Add coins (can be negative) to a user. Returns new balance."""
    user = get_user(user_id)
    if user is None:
        return 0
    user["balance"] = max(0, user.get("balance", 0) + amount)
    save_user(user)
    logger.info(f"Coin transaction: user {user_id} amount {amount} new_balance {user['balance']}")
    return user["balance"]


# ─── GROUPS ─────────────────────────────────────────────────────────────────

def get_groups() -> list:
    return _db_get("groups:list") or []


def add_group(chat_id: int) -> None:
    groups = get_groups()
    if chat_id not in groups:
        groups.append(chat_id)
        _db_set("groups:list", groups)


# ─── COOLDOWNS ──────────────────────────────────────────────────────────────

def get_cooldown(user_id: int, cmd: str) -> Optional[float]:
    return _db_get(f"cooldowns:{user_id}:{cmd}")


def set_cooldown(user_id: int, cmd: str) -> None:
    _db_set(f"cooldowns:{user_id}:{cmd}", _now_ts())


def clear_cooldown(user_id: int, cmd: str) -> None:
    _db_delete(f"cooldowns:{user_id}:{cmd}")


# ─── ANIME REQUESTS ──────────────────────────────────────────────────────────

def get_pending_requests() -> list:
    return _db_get("anime_requests:pending") or []


def get_completed_requests() -> list:
    return _db_get("anime_requests:completed") or []


def add_anime_request(entry: dict) -> None:
    pending = get_pending_requests()
    pending.append(entry)
    _db_set("anime_requests:pending", pending)


def complete_anime_request(req_id: str, completed_by: str) -> bool:
    pending = get_pending_requests()
    completed = get_completed_requests()
    for i, r in enumerate(pending):
        if str(r.get("id")) == str(req_id):
            r["completed_at"] = _now_iso()
            r["completed_by"] = completed_by
            r["status"] = "completed"
            completed.append(r)
            pending.pop(i)
            _db_set("anime_requests:pending", pending)
            _db_set("anime_requests:completed", completed)
            return True
    return False


def reject_anime_request(req_id: str) -> bool:
    pending = get_pending_requests()
    completed = get_completed_requests()
    for i, r in enumerate(pending):
        if str(r.get("id")) == str(req_id):
            r["status"] = "rejected"
            r["rejected_at"] = _now_iso()
            completed.append(r)
            pending.pop(i)
            _db_set("anime_requests:pending", pending)
            _db_set("anime_requests:completed", completed)
            return True
    return False


# ─── BANKS ───────────────────────────────────────────────────────────────────

def get_banks() -> list:
    return _db_get("banks:list") or []


def save_banks(banks: list) -> None:
    _db_set("banks:list", banks)


def get_bank_by_id(bank_id: str) -> Optional[dict]:
    for b in get_banks():
        if str(b.get("bank_id")) == str(bank_id):
            return b
    return None


# ─── AUCTIONS ────────────────────────────────────────────────────────────────

def get_active_auctions() -> list:
    return _db_get("auction:active") or []


def save_active_auctions(auctions: list) -> None:
    _db_set("auction:active", auctions)


def get_pending_auctions() -> list:
    return _db_get("auction:pending") or []


def save_pending_auctions(auctions: list) -> None:
    _db_set("auction:pending", auctions)


# ─── COMPANIES ───────────────────────────────────────────────────────────────

def get_companies() -> list:
    return _db_get("companies:list") or []


def save_companies(companies: list) -> None:
    _db_set("companies:list", companies)


def get_company_by_owner(owner_id: int) -> Optional[dict]:
    for c in get_companies():
        if c.get("owner_id") == owner_id:
            return c
    return None


# ─── PRESIDENT ───────────────────────────────────────────────────────────────

def get_president() -> Optional[dict]:
    return _db_get("president:current")


def set_president(data: dict) -> None:
    _db_set("president:current", data)


def get_president_voting() -> Optional[dict]:
    return _db_get("president:voting")


def set_president_voting(data: dict) -> None:
    _db_set("president:voting", data)


# ─── ADS ─────────────────────────────────────────────────────────────────────

def get_last_ad() -> Optional[dict]:
    return _db_get("ads:last")


def set_last_ad(data: dict) -> None:
    _db_set("ads:last", data)


def get_ad_last_sent() -> Optional[float]:
    return _db_get("ads:last_sent")


def set_ad_last_sent(ts: float) -> None:
    _db_set("ads:last_sent", ts)


# ─── RANKS / TITLES ──────────────────────────────────────────────────────────

def get_ranks_shop() -> list:
    return _db_get("shop:ranks") or [
        {"name": "Rookie", "price": 0},
        {"name": "Street Hustler", "price": 2500},
        {"name": "Gang Member", "price": 8000},
        {"name": "Crime Boss", "price": 20000},
        {"name": "Cartel Leader", "price": 55000},
        {"name": "Warlord", "price": 120000},
        {"name": "Shadow Emperor", "price": 300000},
    ]


def get_titles_shop() -> list:
    return _db_get("shop:titles") or [
        {"name": "The Ghost", "price": 3000},
        {"name": "Iron Fist", "price": 7000},
        {"name": "The Oracle", "price": 15000},
        {"name": "Blood Moon", "price": 30000},
        {"name": "The Untouchable", "price": 75000},
    ]


# ─── CARS / BUILDINGS ────────────────────────────────────────────────────────

def get_cars_shop() -> list:
    return _db_get("shop:cars") or []


def save_cars_shop(cars: list) -> None:
    _db_set("shop:cars", cars)


def get_buildings_shop() -> list:
    return _db_get("shop:buildings") or []


def save_buildings_shop(buildings: list) -> None:
    _db_set("shop:buildings", buildings)


# ─── ANTI-SPAM ────────────────────────────────────────────────────────────────

def get_spam_data(user_id: int) -> dict:
    return _db_get(f"spam:{user_id}") or {"timestamps": [], "muted_until": None}


def save_spam_data(user_id: int, data: dict) -> None:
    _db_set(f"spam:{user_id}", data)
