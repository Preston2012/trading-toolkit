"""Telegram alert helper.

Sends HTML-formatted messages to a Telegram chat via the Bot API.
"""

import logging
import os

import requests

logger = logging.getLogger(__name__)

MAX_MESSAGE_LENGTH = 4000

# Module-level defaults from env vars (set via systemd EnvironmentFile)
_DEFAULT_TOKEN = os.environ.get("TELEGRAM_TOKEN", "") or os.environ.get("TG_TOKEN", "")
_DEFAULT_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "") or os.environ.get("TG_CHAT", "") or os.environ.get("TG_CHAT_ID", "")


def send_tg(msg: str, token: str = "", chat_id: str = "") -> bool:
    """Send a Telegram message via Bot API.

    Args:
        msg: HTML-formatted message text (truncated to 4000 chars).
        token: Telegram bot token. Falls back to env var if empty.
        chat_id: Target chat ID. Falls back to env var if empty.

    Returns:
        True if the message was sent successfully.
    """
    token = token or _DEFAULT_TOKEN
    chat_id = chat_id or _DEFAULT_CHAT_ID
    if not token or not chat_id:
        logger.warning("Telegram send skipped: missing token or chat_id")
        return False
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
