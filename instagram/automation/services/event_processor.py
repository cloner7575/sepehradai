from __future__ import annotations

import logging
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from instagram.automation.models import (
    InstagramConnection,
    InstagramAutomationActionRun,
    InstagramMessage,
    InstagramWebhookEvent,
)
from instagram.automation.services.contact_resolve import (
    get_or_create_conversation,
    resolve_contact_from_event,
)
from instagram.automation.services.feature_flags import feature_enabled
from instagram.automation.services.flow_engine import execute_flow_step, start_flow_execution
from instagram.automation.services.normalize import normalize_webhook_event
from instagram.automation.services.rule_engine import evaluate_rules

logger = logging.getLogger(__name__)


def process_webhook_event(event_id: int) -> None:
    try:
        event = InstagramWebhookEvent.objects.select_related('connection', 'workspace').get(pk=event_id)
    except InstagramWebhookEvent.DoesNotExist:
        logger.warning('IG webhook event %s missing', event_id)
        return

    if event.processing_status == InstagramWebhookEvent.ProcessingStatus.PROCESSED:
        return

    event.processing_status = InstagramWebhookEvent.ProcessingStatus.PROCESSING
    event.attempts += 1
    event.save(update_fields=['processing_status', 'attempts'])

    try:
        _handle(event)
        if event.processing_status != InstagramWebhookEvent.ProcessingStatus.SKIPPED:
            event.processing_status = InstagramWebhookEvent.ProcessingStatus.PROCESSED
            event.last_error_sanitized = ''
        event.processed_at = timezone.now()
        event.save(update_fields=['processing_status', 'processed_at', 'last_error_sanitized'])
    except Exception as exc:
        logger.exception('IG event %s failed cid=%s', event_id, event.correlation_id)
        event.processing_status = (
            InstagramWebhookEvent.ProcessingStatus.DEAD
            if event.attempts >= 5
            else InstagramWebhookEvent.ProcessingStatus.FAILED
        )
        event.failed_at = timezone.now()
        event.last_error_sanitized = type(exc).__name__
        event.next_retry_at = timezone.now() + timedelta(minutes=min(2 ** event.attempts, 60))
        event.save(
            update_fields=[
                'processing_status',
                'failed_at',
                'last_error_sanitized',
                'next_retry_at',
            ]
        )
        raise


def _handle(event: InstagramWebhookEvent) -> None:
    conn = event.connection
    if not conn or not conn.is_connected:
        _skip_event(event, 'connection_unavailable')
        return

    if not feature_enabled(conn.workspace, 'instagram_module'):
        return

    payload, skip_reason = _hydrate_message_edit(conn, event, event.payload_redacted or {})
    if skip_reason:
        _skip_event(event, skip_reason)
        return

    normalized = normalize_webhook_event(
        event_type=event.event_type,
        payload=payload,
        connection_id=conn.id,
        workspace_id=conn.workspace_id,
        correlation_id=event.correlation_id,
        raw_event_id=event.id,
    )

    if normalized.is_echo:
        _skip_event(event, 'message_echo')
        return

    if (
        normalized.event_type in ('message.received', 'message.edited', 'message.unknown')
        and not normalized.text
        and not normalized.media_url
    ):
        _skip_event(event, 'message_content_unavailable')
        return

    if normalized.event_type in (
        'message.received',
        'message.edited',
        'message.attachment',
        'story_reply',
        'postback',
        'referral',
        'reaction',
    ):
        _handle_inbound_message(conn, event, normalized)
    elif normalized.event_type.startswith('comment'):
        from instagram.automation.services.comment_automation import handle_comment_event

        handle_comment_event(conn, event, normalized)
    # سایر رویدادها فعلاً فقط ثبت می‌شوند


def _skip_event(event: InstagramWebhookEvent, reason: str) -> None:
    event.processing_status = InstagramWebhookEvent.ProcessingStatus.SKIPPED
    event.last_error_sanitized = reason[:512]


def _hydrate_message_edit(conn: InstagramConnection, event: InstagramWebhookEvent, payload: dict):
    """Fetch message text/direction when Meta sends only message_edit metadata."""
    message_edit = payload.get('message_edit') or {}
    if not isinstance(message_edit, dict) or not message_edit:
        return payload, ''

    mid = str(message_edit.get('mid') or '')
    if not mid:
        return payload, 'message_edit_missing_mid'

    from instagram.automation.services.oauth import client_for_connection

    detail = client_for_connection(conn).get(
        mid,
        params={'fields': 'id,message,from,to,created_time'},
        correlation_id=event.correlation_id,
    )
    detail_sender_id = str((detail.get('from') or {}).get('id') or '')
    own_ids = {
        str(conn.instagram_account_id or ''),
        str(conn.facebook_page_id or ''),
    }
    own_ids.discard('')
    if detail_sender_id and detail_sender_id in own_ids:
        return payload, 'message_echo'

    text = str(detail.get('message') or message_edit.get('text') or '')
    if not text:
        return payload, 'message_edit_missing_text'

    hydrated = dict(payload)
    hydrated['message'] = {
        'mid': mid,
        'text': text,
    }
    return hydrated, ''


def _handle_inbound_message(conn, event, normalized) -> None:
    if not feature_enabled(conn.workspace, 'instagram_inbox'):
        return
    if not normalized.sender_scoped_id:
        return

    with transaction.atomic():
        contact = resolve_contact_from_event(connection=conn, event=normalized)
        is_first = contact.first_interaction_at and (
            abs((contact.last_interaction_at - contact.first_interaction_at).total_seconds()) < 2
            if contact.last_interaction_at and contact.first_interaction_at
            else False
        )
        # تقریب first: اگر فقط همین تعامل است
        is_first = InstagramMessage.objects.filter(
            conversation__contact=contact,
        ).count() == 0

        conversation = get_or_create_conversation(connection=conn, contact=contact)
        msg, created = InstagramMessage.objects.get_or_create(
            conversation=conversation,
            external_message_id=normalized.external_message_id or f'local-{event.id}',
            defaults={
                'workspace_id': conn.workspace_id,
                'direction': InstagramMessage.Direction.INBOUND,
                'sender_type': InstagramMessage.SenderType.CUSTOMER,
                'message_type': normalized.message_type,
                'text': normalized.text,
                'media_url': normalized.media_url,
                'delivery_status': InstagramMessage.DeliveryStatus.DELIVERED,
                'delivered_at': timezone.now(),
                'raw_event': event,
            },
        )
        if not created:
            if normalized.event_type == 'message.edited' and normalized.text and msg.text != normalized.text:
                msg.text = normalized.text
                msg.raw_event = event
                msg.save(update_fields=['text', 'raw_event'])
            return
        conversation.last_message_at = conversation.last_customer_message_at = timezone.now()
        conversation.unread_count = (conversation.unread_count or 0) + 1
        conversation.save(update_fields=['last_message_at', 'last_customer_message_at', 'unread_count', 'updated_at'])

    if not conversation.is_automation_active():
        return
    if not feature_enabled(conn.workspace, 'instagram_dm_automation'):
        return

    result = evaluate_rules(
        workspace_id=conn.workspace_id,
        connection_id=conn.id,
        contact_id=contact.id,
        event=normalized,
        is_first_interaction=is_first,
    )
    if not result.rule or not result.rule.flow_id:
        return
    flow = result.rule.flow
    if flow.status != flow.Status.ACTIVE and not flow.status:
        return
    from instagram.automation.models import InstagramFlow

    if flow.status != InstagramFlow.Status.ACTIVE:
        return

    action_run, created = InstagramAutomationActionRun.objects.get_or_create(
        workspace_id=conn.workspace_id,
        event=event,
        rule=result.rule,
        action_key='start_flow',
    )
    if not created and action_run.status in (
        InstagramAutomationActionRun.Status.PENDING,
        InstagramAutomationActionRun.Status.SUCCEEDED,
    ):
        return
    from instagram.automation.services.product_context import resolve_source_product

    product, media = resolve_source_product(connection=conn, event=normalized, rule=result.rule)
    execution = start_flow_execution(
        flow=flow,
        contact=contact,
        conversation=conversation,
        variables={
            'webhook_event_id': event.pk,
            'rule_id': result.rule.pk,
            'source_product_id': product.pk if product else None,
            'source_media_id': media.pk if media else None,
            'source_external_media_id': normalized.media_id or normalized.story_id,
        },
    )
    # اجرای چند گام تا wait/stop
    for _ in range(50):
        execution = execute_flow_step(execution)
        if execution.status != execution.Status.RUNNING:
            break
    if execution.status in (execution.Status.COMPLETED, execution.Status.WAITING):
        action_run.status = InstagramAutomationActionRun.Status.SUCCEEDED
        action_run.error_code = ''
    else:
        action_run.status = InstagramAutomationActionRun.Status.FAILED
        action_run.error_code = (
            'flow_step_batch_exhausted'
            if execution.status == execution.Status.RUNNING
            else 'flow_execution_failed'
        )
    action_run.attempts += 1
    action_run.save(update_fields=['status', 'error_code', 'attempts', 'updated_at'])
