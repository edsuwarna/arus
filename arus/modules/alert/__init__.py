"""
Alert Integration (Telegram)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Sends Telegram notifications on pipeline failure, dead letter rows created,
or schema drift detected.

Config: ARUS_TELEGRAM_BOT_TOKEN, ARUS_TELEGRAM_CHAT_ID env vars.
"""

import logging
from typing import Optional

import requests

from arus.shared.config import settings

logger = logging.getLogger(__name__)


class AlertManager:
    """Sends alerts via Telegram Bot API."""

    def __init__(self):
        self.bot_token: Optional[str] = settings.telegram_bot_token
        self.chat_id: Optional[str] = settings.telegram_chat_id
        self._enabled = bool(self.bot_token and self.chat_id)

        if not self._enabled:
            logger.info(
                "Telegram alerts disabled — set ARUS_TELEGRAM_BOT_TOKEN and "
                "ARUS_TELEGRAM_CHAT_ID to enable"
            )

    def is_enabled(self) -> bool:
        return self._enabled

    def send_message(self, text: str) -> bool:
        """Send a plain text message to the configured Telegram chat."""
        if not self._enabled:
            return False

        try:
            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            resp = requests.post(
                url,
                json={
                    "chat_id": self.chat_id,
                    "text": text,
                    "parse_mode": "HTML",
                },
                timeout=10,
            )
            if resp.status_code == 200:
                logger.debug(f"Telegram alert sent: {text[:100]}...")
                return True
            else:
                logger.error(
                    f"Telegram API error: {resp.status_code} {resp.text[:200]}"
                )
                return False
        except requests.RequestException as e:
            logger.error(f"Telegram request failed: {e}")
            return False

    def alert_pipeline_failure(
        self,
        pipeline_id: str,
        pipeline_name: str,
        run_id: str,
        error: str,
    ) -> bool:
        """Send alert on pipeline failure."""
        text = (
            f"🚨 <b>Pipeline Failed</b>\n"
            f"Name: {pipeline_name}\n"
            f"ID: <code>{pipeline_id}</code>\n"
            f"Run: <code>{run_id}</code>\n"
            f"Error: {error[:500]}"
        )
        return self.send_message(text)

    def alert_dead_letter(
        self,
        pipeline_id: str,
        pipeline_name: str,
        run_id: str,
        table_name: str,
        row_count: int,
        error: str,
    ) -> bool:
        """Send alert when rows are sent to dead letter queue."""
        text = (
            f"⚠️ <b>Dead Letter Rows Created</b>\n"
            f"Pipeline: {pipeline_name} (<code>{pipeline_id}</code>)\n"
            f"Run: <code>{run_id}</code>\n"
            f"Table: <code>{table_name}</code>\n"
            f"Rows: {row_count}\n"
            f"Error: {error[:300]}"
        )
        return self.send_message(text)

    def alert_schema_drift(
        self,
        pipeline_id: str,
        pipeline_name: str,
        table_name: str,
        new_columns: list[str],
    ) -> bool:
        """Send alert when schema drift is detected."""
        cols_str = ", ".join(new_columns)
        text = (
            f"🔀 <b>Schema Drift Detected</b>\n"
            f"Pipeline: {pipeline_name} (<code>{pipeline_id}</code>)\n"
            f"Table: <code>{table_name}</code>\n"
            f"New Columns: {cols_str}"
        )
        return self.send_message(text)
