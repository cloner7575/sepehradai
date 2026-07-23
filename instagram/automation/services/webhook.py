from __future__ import annotations

import hashlib
import json
import logging
import uuid
from typing import Any

from django.db import IntegrityError, transaction
from django.utils import timezone

from instagram.automation.models import InstagramConnection, InstagramWebhookEvent

logger = logging.getLogger(__name__)


def _fingerprint(payload: dict, event_type: str, object_id: str = '') -> str:
    raw = json.dumps(
        {'t': event_type, 'o': object_id, 'p': payload},
        sort_keys=True,
        ensure_ascii=False,
        default=str,
    )
    return hashlib.sha256(raw.encode('utf-8')).hexdigest()


def redact_payload(payload: Any) -> Any:
    """حذف فیلدهای حساس از payload برای ذخیره/لاگ."""
    if isinstance(payload, dict):
        out = {}
        for k, v in payload.items():
            lk = str(k).lower()
            if lk in ('access_token', 'token', 'authorization', 'app_secret'):
                out[k] = '[REDACTED]'
            else:
                out[k] = redact_payload(v)
        return out
    if isinstance(payload, list):
        return [redact_payload(x) for x in payload]
    return payload


def resolve_connection_from_entry(entry: dict) -> InstagramConnection | None:
    object_id = str(entry.get('id') or '')
    if not object_id:
        return None
    connected = InstagramConnection.objects.filter(
        connection_status=InstagramConnection.ConnectionStatus.CONNECTED,
    ).select_related('workspace')
    return connected.filter(instagram_account_id=object_id).first() or connected.filter(
        facebook_page_id=object_id,
    ).first()


def ingest_webhook_payload(payload: dict) -> list[InstagramWebhookEvent]:
    """ثبت رویدادها و برگرداندن موارد جدید برای صف."""
    created: list[InstagramWebhookEvent] = []
    object_type = payload.get('object') or 'unknown'
    entries = payload.get('entry') or []
    correlation_id = str(uuid.uuid4())

    for entry in entries:
        conn = resolve_connection_from_entry(entry)
        messaging = entry.get('messaging') or []
        changes = entry.get('changes') or []

        for msg in messaging:
            event_type = _infer_messaging_type(msg)
            fp = _fingerprint(msg, event_type, str(entry.get('id') or ''))
            ev = _create_event(
                connection=conn,
                event_type=event_type,
                fingerprint=fp,
                payload=msg,
                correlation_id=correlation_id,
                external_id=str(
                    (msg.get('message') or {}).get('mid')
                    or (msg.get('message_edit') or {}).get('mid')
                    or ''
                ),
            )
            if ev:
                created.append(ev)

        for change in changes:
            field = change.get('field') or 'change'
            value = change.get('value') or {}
            event_type = f'{object_type}.{field}'
            fp = _fingerprint(change, event_type, str(entry.get('id') or ''))
            external = str(value.get('id') or value.get('comment_id') or '')
            ev = _create_event(
                connection=conn,
                event_type=event_type,
                fingerprint=fp,
                payload=change,
                correlation_id=correlation_id,
                external_id=external,
            )
            if ev:
                created.append(ev)

        if not messaging and not changes:
            fp = _fingerprint(entry, f'{object_type}.entry', str(entry.get('id') or ''))
            ev = _create_event(
                connection=conn,
                event_type=f'{object_type}.entry',
                fingerprint=fp,
                payload=entry,
                correlation_id=correlation_id,
            )
            if ev:
                created.append(ev)

    return created


def _infer_messaging_type(msg: dict) -> str:
    if msg.get('message'):
        m = msg['message']
        if m.get('is_deleted'):
            return 'message.deleted'
        if m.get('attachments'):
            return 'message.attachment'
        if (m.get('reply_to') or {}).get('story'):
            return 'message.story_reply'
        return 'message.received'
    if msg.get('message_edit'):
        edit = msg['message_edit'] or {}
        try:
            edit_number = int(edit.get('num_edit') or 0)
        except (TypeError, ValueError):
            edit_number = 0
        return 'message.edited' if edit_number > 0 else 'message.received'
    if msg.get('postback'):
        return 'message.postback'
    if msg.get('referral'):
        return 'message.referral'
    if msg.get('reaction'):
        return 'message.reaction'
    if msg.get('delivery'):
        return 'message.delivered'
    if msg.get('read'):
        return 'message.seen'
    return 'message.unknown'


def _create_event(
    *,
    connection: InstagramConnection | None,
    event_type: str,
    fingerprint: str,
    payload: dict,
    correlation_id: str,
    external_id: str = '',
) -> InstagramWebhookEvent | None:
    try:
        with transaction.atomic():
            ev = InstagramWebhookEvent.objects.create(
                connection=connection,
                workspace_id=connection.workspace_id if connection else None,
                external_event_id=external_id,
                event_type=event_type,
                fingerprint=fingerprint,
                payload_redacted=redact_payload(payload),
                processing_status=InstagramWebhookEvent.ProcessingStatus.QUEUED,
                correlation_id=correlation_id,
            )
            if connection:
                InstagramConnection.objects.filter(pk=connection.pk).update(
                    last_webhook_at=timezone.now(),
                    webhook_status=InstagramConnection.WebhookStatus.ACTIVE,
                )
            return ev
    except IntegrityError:
        logger.info('Duplicate webhook fingerprint=%s', fingerprint[:16])
        return None
