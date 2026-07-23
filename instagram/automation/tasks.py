from __future__ import annotations

import logging
import random
from datetime import timedelta

from celery import shared_task
from django.db import DatabaseError
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    max_retries=5,
    default_retry_delay=5,
    queue='instagram',
    autoretry_for=(DatabaseError,),
    retry_backoff=True,
    name='instagram.automation.tasks.process_instagram_webhook',
)
def process_instagram_webhook(self, event_id: int) -> None:
    from instagram.automation.services.event_processor import process_webhook_event

    from instagram.automation.services.meta_client import MetaAPIError, MetaErrorCategory
    try:
        process_webhook_event(event_id)
    except MetaAPIError as exc:
        if exc.category in (MetaErrorCategory.RETRYABLE, MetaErrorCategory.RATE_LIMIT):
            countdown = max(1, float(exc.retry_after or (2 ** min(self.request.retries + 1, 6))))
            raise self.retry(exc=exc, countdown=countdown + random.uniform(0, 1.5))
        from instagram.automation.models import InstagramWebhookEvent

        InstagramWebhookEvent.objects.filter(pk=event_id).update(
            processing_status=InstagramWebhookEvent.ProcessingStatus.DEAD,
            last_error_sanitized=exc.internal_code,
            next_retry_at=None,
        )
    except DatabaseError as exc:
        raise self.retry(exc=exc)
    except Exception:
        from instagram.automation.models import InstagramWebhookEvent

        InstagramWebhookEvent.objects.filter(pk=event_id).update(
            processing_status=InstagramWebhookEvent.ProcessingStatus.DEAD,
            next_retry_at=None,
        )


@shared_task(queue='instagram', name='instagram.automation.tasks.retry_failed_instagram_event')
def retry_failed_instagram_event(event_id: int) -> None:
    from instagram.automation.models import InstagramWebhookEvent

    ev = InstagramWebhookEvent.objects.filter(pk=event_id).first()
    if not ev:
        return
    if ev.processing_status not in (
        InstagramWebhookEvent.ProcessingStatus.FAILED,
        InstagramWebhookEvent.ProcessingStatus.DEAD,
    ):
        return
    ev.processing_status = InstagramWebhookEvent.ProcessingStatus.QUEUED
    ev.save(update_fields=['processing_status'])
    process_instagram_webhook.delay(ev.id)


@shared_task(queue='instagram', name='instagram.automation.tasks.refresh_instagram_token')
def refresh_instagram_token(connection_id: int) -> None:
    from instagram.automation.models import InstagramConnection, InstagramAuditLog
    from instagram.automation.services.oauth import refresh_long_lived_token
    from instagram.automation.services.token_crypto import decrypt_token, encrypt_token

    conn = InstagramConnection.objects.filter(pk=connection_id).first()
    if not conn or conn.auth_provider != InstagramConnection.AuthProvider.INSTAGRAM_LOGIN:
        return
    data = refresh_long_lived_token(decrypt_token(conn.encrypted_access_token))
    conn.encrypted_access_token = encrypt_token(data['access_token'])
    conn.token_expires_at = timezone.now() + timedelta(seconds=int(data.get('expires_in') or 5184000))
    conn.token_last_refreshed_at = timezone.now()
    conn.connection_status = InstagramConnection.ConnectionStatus.CONNECTED
    conn.last_error_code = ''
    conn.last_error_message_sanitized = ''
    conn.save(update_fields=[
        'encrypted_access_token', 'token_expires_at', 'token_last_refreshed_at',
        'connection_status', 'last_error_code', 'last_error_message_sanitized', 'updated_at',
    ])
    InstagramAuditLog.objects.create(
        workspace_id=conn.workspace_id,
        actor_type=InstagramAuditLog.ActorType.SYSTEM,
        action='instagram.token_refreshed',
        entity_type='InstagramConnection',
        entity_id=str(conn.id),
    )


@shared_task(queue='instagram', name='instagram.automation.tasks.sync_instagram_media')
def sync_instagram_media(connection_id: int | None = None) -> dict:
    from instagram.automation.models import InstagramConnection
    from instagram.automation.services.media_sync import sync_connection_media

    qs = InstagramConnection.objects.filter(
        connection_status=InstagramConnection.ConnectionStatus.CONNECTED,
    )
    if connection_id:
        qs = qs.filter(pk=connection_id)
    result = {'connections': 0, 'created': 0, 'updated': 0}
    for connection in qs.iterator():
        synced = sync_connection_media(connection)
        result['connections'] += 1
        result['created'] += synced['created']
        result['updated'] += synced['updated']
    return result


@shared_task(queue='instagram', name='instagram.automation.tasks.refresh_due_instagram_tokens')
def refresh_due_instagram_tokens() -> dict:
    from instagram.automation.models import InstagramConnection

    due = InstagramConnection.objects.filter(
        auth_provider=InstagramConnection.AuthProvider.INSTAGRAM_LOGIN,
        connection_status=InstagramConnection.ConnectionStatus.CONNECTED,
        token_expires_at__isnull=False,
        token_expires_at__lte=timezone.now() + timedelta(days=7),
    )
    count = 0
    for connection_id in due.values_list('pk', flat=True)[:100]:
        refresh_instagram_token.delay(connection_id)
        count += 1
    return {'enqueued': count}

@shared_task(queue='instagram', name='instagram.automation.tasks.retry_due_instagram_events')
def retry_due_instagram_events() -> dict:
    from instagram.automation.models import InstagramWebhookEvent

    now = timezone.now()
    qs = InstagramWebhookEvent.objects.filter(
        processing_status=InstagramWebhookEvent.ProcessingStatus.FAILED,
        next_retry_at__lte=now,
        attempts__lt=5,
    ).order_by('next_retry_at')[:50]
    n = 0
    for ev in qs:
        process_instagram_webhook.delay(ev.id)
        n += 1
    return {'enqueued': n}


@shared_task(queue='instagram', name='instagram.automation.tasks.cleanup_instagram_data')
def cleanup_instagram_data(days: int = 180) -> dict:
    from instagram.automation.models import InstagramWebhookEvent

    cutoff = timezone.now() - timedelta(days=days)
    deleted, _ = InstagramWebhookEvent.objects.filter(
        received_at__lt=cutoff,
        processing_status=InstagramWebhookEvent.ProcessingStatus.PROCESSED,
    ).delete()
    return {'deleted_events': deleted}


@shared_task(queue='instagram', name='instagram.automation.tasks.notify_instagram_connection_error')
def notify_instagram_connection_error(connection_id: int, message: str) -> None:
    from instagram.automation.models import InstagramConnection, InstagramAuditLog

    conn = InstagramConnection.objects.filter(pk=connection_id).first()
    if not conn:
        return
    InstagramAuditLog.objects.create(
        workspace_id=conn.workspace_id,
        actor_type=InstagramAuditLog.ActorType.SYSTEM,
        action='instagram.connection_error',
        entity_type='InstagramConnection',
        entity_id=str(conn.id),
        after_data_redacted={'message': (message or '')[:200]},
    )


@shared_task(queue='instagram', name='instagram.automation.tasks.execute_instagram_flow')
def execute_instagram_flow(execution_id: int) -> None:
    from instagram.automation.models import InstagramFlowExecution
    from instagram.automation.services.flow_engine import execute_flow_step

    execution = InstagramFlowExecution.objects.filter(pk=execution_id).first()
    if not execution:
        return
    for _ in range(20):
        execution = execute_flow_step(execution)
        if execution.status != InstagramFlowExecution.Status.RUNNING:
            break


@shared_task(queue='instagram', name='instagram.automation.tasks.calculate_instagram_analytics')
def calculate_instagram_analytics(workspace_id: int) -> dict:
    from balebot.models import Workspace
    from instagram.automation.services.analytics import analytics_summary

    ws = Workspace.objects.filter(pk=workspace_id).first()
    if not ws:
        return {}
    return analytics_summary(ws)
