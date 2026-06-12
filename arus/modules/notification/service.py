import json
import logging
from typing import Optional

import requests

from arus.shared.config import settings
from arus.modules.notification.repository import NotificationRepository
from arus.modules.notification.templates import (
    format_for_telegram,
    format_for_discord,
    format_for_slack,
)

logger = logging.getLogger(__name__)


def send_telegram(config: dict, data: dict) -> bool:
    bot_token = config.get("bot_token", "")
    chat_id = config.get("chat_id", "")
    if not bot_token or not chat_id:
        logger.error("Telegram target missing bot_token or chat_id")
        return False
    try:
        text = format_for_telegram(data)
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        resp = requests.post(url, json={
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
        }, timeout=10)
        if resp.status_code == 200:
            return True
        else:
            logger.error(f"Telegram API error: {resp.status_code} {resp.text[:200]}")
            return False
    except requests.RequestException as e:
        logger.error(f"Telegram request failed: {e}")
        return False


def send_discord(config: dict, data: dict) -> bool:
    webhook_url = config.get("webhook_url", "")
    if not webhook_url:
        logger.error("Discord target missing webhook_url")
        return False
    try:
        payload = format_for_discord(data)
        resp = requests.post(webhook_url, json=payload, timeout=10)
        if 200 <= resp.status_code < 300:
            return True
        else:
            logger.error(f"Discord webhook error: {resp.status_code} {resp.text[:200]}")
            return False
    except requests.RequestException as e:
        logger.error(f"Discord webhook failed: {e}")
        return False


def send_slack(config: dict, data: dict) -> bool:
    webhook_url = config.get("webhook_url", "")
    if not webhook_url:
        logger.error("Slack target missing webhook_url")
        return False
    try:
        payload = format_for_slack(data)
        resp = requests.post(webhook_url, json=payload, timeout=10)
        if 200 <= resp.status_code < 300:
            return True
        else:
            logger.error(f"Slack webhook error: {resp.status_code} {resp.text[:200]}")
            return False
    except requests.RequestException as e:
        logger.error(f"Slack webhook failed: {e}")
        return False


SENDERS = {
    "telegram": send_telegram,
    "discord": send_discord,
    "slack": send_slack,
}


class NotificationService:
    def __init__(self, repo: NotificationRepository):
        self.repo = repo

    def notify_pipeline_event(
        self,
        pipeline_id: str,
        event_type: str,
        pipeline_name: str,
        run_id: str = "",
        error: str = "",
        extra: Optional[dict] = None,
        source_name: str = "",
        destination_name: str = "",
        schedule: str = "",
    ):
        """Send notification to all targets linked to this pipeline for this event type."""
        links = self.repo.list_by_pipeline(pipeline_id)
        if not links:
            return

        from arus.modules.notification.templates import BUILDERS

        builder = BUILDERS.get(event_type)
        if not builder:
            logger.warning(f"Unknown event_type: {event_type}")
            return

        data = builder(
            pipeline_name=pipeline_name,
            pipeline_id=pipeline_id,
            run_id=run_id,
            error=error,
            extra=extra,
            source_name=source_name,
            destination_name=destination_name,
            schedule=schedule,
        )

        for link in links:
            event_types = link.get("event_types") or []
            if event_type not in event_types:
                continue

            target = self.repo.get_target(link["target_id"])
            if not target or not target.get("is_active"):
                continue

            sender = SENDERS.get(target["type"])
            if not sender:
                logger.warning(f"No sender for type: {target['type']}")
                continue

            try:
                success = sender(target["config"], data)
                if not success:
                    logger.warning(f"Failed to send {event_type} notification to {target['name']} ({target['type']})")
            except Exception as e:
                logger.error(f"Error sending notification to {target['name']}: {e}")
