"""Alert service for sending notifications to Telegram."""

import os
from typing import Optional

import httpx

from app.logging_config import get_logger

logger = get_logger("alert_service")

ALERT_BOT_TOKEN = os.environ.get("ALERT_BOT_TOKEN")
ALERT_CHAT_ID = os.environ.get("ALERT_CHAT_ID")


def send_alert(level: str, message: str, context: Optional[dict] = None) -> bool:
    """Send alert to Telegram.

    Args:
        level: INFO, WARNING, ERROR, CRITICAL
        message: Alert message
        context: Optional context dict

    Returns:
        True if sent successfully
    """
    if not ALERT_BOT_TOKEN or not ALERT_CHAT_ID:
        logger.warning(f"Alert not configured: {level} - {message}")
        return False

    emoji = {"INFO": "ℹ️", "WARNING": "⚠️", "ERROR": "❌", "CRITICAL": "🔥"}

    text = f"{emoji.get(level, '📢')} *{level}*\n\n{message}"

    if context:
        context_str = "\n".join(f"  {k}: {v}" for k, v in context.items())
        text += f"\n\n```\n{context_str}\n```"

    try:
        with httpx.Client(timeout=10) as client:
            response = client.post(
                f"https://api.telegram.org/bot{ALERT_BOT_TOKEN}/sendMessage",
                json={"chat_id": ALERT_CHAT_ID, "text": text, "parse_mode": "Markdown"},
            )
            return response.status_code == 200
    except Exception as e:
        logger.error(f"Failed to send alert: {e}")
        return False


def alert_error(message: str, context: Optional[dict] = None) -> bool:
    """Shortcut for ERROR level alert."""
    return send_alert("ERROR", message, context)


def alert_critical(message: str, context: Optional[dict] = None) -> bool:
    """Shortcut for CRITICAL level alert."""
    return send_alert("CRITICAL", message, context)


def alert_warning(message: str, context: Optional[dict] = None) -> bool:
    """Shortcut for WARNING level alert."""
    return send_alert("WARNING", message, context)
