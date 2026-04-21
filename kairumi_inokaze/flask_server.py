"""Flask uptime server for UptimeRobot / keep-alive."""

import threading
import logging
from flask import Flask, jsonify

logger = logging.getLogger(__name__)

app = Flask(__name__)


@app.route("/")
def home():
    """Root endpoint — used by UptimeRobot to confirm bot is alive."""
    return "🤖 Kairumi Inokaze Bot is Alive!", 200


@app.route("/health")
def health():
    """Health check endpoint."""
    return jsonify({"status": "running", "bot": "Kairumi Inokaze"}), 200


def run_flask(port: int = 8080) -> None:
    """Run Flask server (blocking)."""
    app.run(host="0.0.0.0", port=port, use_reloader=False, threaded=True)


def start_flask_thread(port: int = 8080) -> threading.Thread:
    """Start Flask in a daemon thread and return the thread."""
    thread = threading.Thread(target=run_flask, args=(port,), daemon=True)
    thread.start()
    logger.info(f"Flask uptime server started on port {port}")
    return thread
