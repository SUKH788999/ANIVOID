"""Logging setup for Kairumi Inokaze."""

import logging
import sys
from logging.handlers import RotatingFileHandler


def setup_logger() -> logging.Logger:
    """Configure and return the root logger."""
    fmt = "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s"
    datefmt = "%Y-%m-%d %H:%M:%S"

    formatter = logging.Formatter(fmt, datefmt=datefmt)

    root = logging.getLogger()
    root.setLevel(logging.INFO)

    # Console handler
    ch = logging.StreamHandler(sys.stdout)
    ch.setFormatter(formatter)
    root.addHandler(ch)

    # File handler (rotating, 5 MB max)
    try:
        fh = RotatingFileHandler("bot.log", maxBytes=5 * 1024 * 1024, backupCount=3)
        fh.setFormatter(formatter)
        root.addHandler(fh)
    except Exception:
        pass

    # Silence noisy libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("telegram").setLevel(logging.WARNING)
    logging.getLogger("apscheduler").setLevel(logging.WARNING)

    return root


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
