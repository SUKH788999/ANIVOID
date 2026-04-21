"""Root entry point for Kairumi Inokaze Telegram Bot."""

import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from kairumi_inokaze.main import main

if __name__ == "__main__":
    main()
