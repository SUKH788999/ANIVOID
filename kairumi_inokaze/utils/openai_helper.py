"""OpenAI API integration for smart bot replies."""

import logging
from kairumi_inokaze.config import OPENAI_API_KEY

logger = logging.getLogger(__name__)

_client = None


def _get_client():
    global _client
    if _client is None and OPENAI_API_KEY:
        try:
            from openai import AsyncOpenAI
            _client = AsyncOpenAI(api_key=OPENAI_API_KEY)
        except Exception as e:
            logger.error(f"Failed to init OpenAI client: {e}")
    return _client


async def get_smart_reply(user_message: str, username: str) -> str:
    """Get a smart AI reply for a user message."""
    client = _get_client()
    if client is None:
        return "🤖 Hey! Use /help to see what I can do."

    try:
        system_prompt = (
            "You are Kairumi Inokaze, a friendly Telegram bot assistant "
            "in a gaming economy world. Keep replies short, fun, with emojis. "
            "You help users with an economy system including coins, ranks, "
            "robberies, kills, auctions, and more. Stay in character."
        )
        response = await client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"{username}: {user_message}"},
            ],
            max_tokens=200,
            temperature=0.85,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"OpenAI error: {e}")
        return "🤖 I'm having trouble thinking right now. Try /help!"


async def generate_event_announcement(event: str) -> str:
    """Generate a creative event announcement."""
    client = _get_client()
    if client is None:
        return f"📢 {event}"

    try:
        response = await client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are Kairumi Inokaze bot. Generate a short, exciting "
                        "Telegram announcement for the given event. Use emojis, "
                        "make it hype. Max 3 sentences."
                    ),
                },
                {"role": "user", "content": f"Event: {event}"},
            ],
            max_tokens=150,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"OpenAI event error: {e}")
        return f"📢 {event}"
