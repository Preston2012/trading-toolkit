"""Telegram alert helper.

Sends HTML-formatted messages to a Telegram chat via the Bot API.
"""

import logging

import requests

logger = logging.getLogger(__name__)

MAX_MESSAGE_LENGTH = 4000


def send_tg(msg: str, token: str, chat_id: str) -> bool:
    """Send a Telegram message via Bot API.

    Args:
        msg: HTML-formatted message text (truncated to 4000 chars).
        token: Telegram bot token.
        chat_id: Target chat ID.

    Returns:
        True if the message was sent successfully.
    """
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    try:
        resp = requests.post(
            url,
            json={
                "chat_id": chat_id,
                "text": msg[:MAX_MESSAGE_LENGTH],
                "parse_mode": "HTML",
            },
            timeout=10,
        )
        resp.raise_for_status()
        return True
    except requests.RequestException as exc:
        logger.warning("Telegram send failed: %s", exc)
        return False
