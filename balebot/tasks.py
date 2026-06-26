"""Celery tasks for async webhook processing and scheduled campaigns."""

from __future__ import annotations

import logging

from celery import shared_task
from django.db import DatabaseError

from balebot.models import BotSettings
from balebot.services import messenger_api, webhook_logic
from balebot.services.campaign_runner import process_due_campaigns_batch

logger = logging.getLogger(__name__)


def dispatch_webhook_payload(cfg: BotSettings, payload: dict) -> None:
    """Shared handler for sync and async webhook processing."""
    if payload.get('message'):
        webhook_logic.handle_message(cfg, payload['message'])
    elif payload.get('callback_query'):
        webhook_logic.handle_callback(cfg, payload['callback_query'])


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=2,
    queue='webhooks',
    autoretry_for=(DatabaseError,),
    retry_backoff=True,
)
def process_webhook_update(self, bot_settings_id: int, payload: dict) -> None:
    try:
        cfg = BotSettings.objects.select_related('workspace').get(pk=bot_settings_id)
    except BotSettings.DoesNotExist:
        logger.warning('Webhook task: BotSettings %s not found', bot_settings_id)
        return

    try:
        dispatch_webhook_payload(cfg, payload)
    except messenger_api.MessengerAPIError as exc:
        logger.warning('Webhook messenger API error (%s): %s', cfg.platform, exc)
    except DatabaseError:
        raise
    except Exception:
        logger.exception('Webhook task error (%s)', cfg.platform)


@shared_task(queue='campaigns')
def run_due_campaigns() -> dict[str, int]:
    return process_due_campaigns_batch()
