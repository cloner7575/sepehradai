from __future__ import annotations

import logging
import random

from django.core.cache import cache
from django.utils import timezone

from instagram.automation.models import (
    InstagramAutomationActionRun,
    InstagramCommentAutomation,
    InstagramMessage,
)
from instagram.automation.services.contact_resolve import (
    get_or_create_conversation,
    resolve_contact_from_event,
)
from instagram.automation.services.feature_flags import feature_enabled, meta_capability_status
from instagram.automation.services.flow_engine import execute_flow_step, start_flow_execution
from instagram.automation.services.oauth import client_for_connection
from instagram.automation.services.persian_normalize import match_text, normalize_persian
from instagram.automation.models import InstagramFlow

logger = logging.getLogger(__name__)


def handle_comment_event(conn, event, normalized) -> None:
    if not feature_enabled(conn.workspace, 'instagram_comment_automation'):
        return
    status = meta_capability_status(conn.workspace, 'comments')
    if status == 'disabled':
        return

    contact = resolve_contact_from_event(connection=conn, event=normalized)
    conversation = get_or_create_conversation(connection=conn, contact=contact)

    automations = InstagramCommentAutomation.objects.filter(
        connection=conn,
        is_active=True,
    )
    matched = None
    for auto in automations:
        if auto.media_id and normalized.media_id and auto.media_id != normalized.media_id:
            continue
        text_n = normalize_persian(normalized.text)
        if auto.exclude_keywords:
            if match_text(text_n, operator='any_of', value=auto.exclude_keywords, normalize=False):
                continue
        if auto.include_keywords:
            if not match_text(text_n, operator='any_of', value=auto.include_keywords, normalize=False):
                continue
        if auto.skip_own_comments and normalized.sender_scoped_id == conn.instagram_account_id:
            continue
        cd_key = f'ig:cmt:cd:{auto.id}:{contact.id}'
        if auto.cooldown_seconds and cache.get(cd_key):
            continue
        matched = auto
        break

    if not matched:
        return

    cache.set(
        f'ig:cmt:cd:{matched.id}:{contact.id}',
        1,
        matched.cooldown_seconds or 60,
    )

    # مراحل مستقل برای جلوگیری از تکرار مرحله موفق
    stage_key = f'ig:cmt:stage:{event.id}'
    stages = cache.get(stage_key) or {}

    client = None
    if status == 'enabled' and not stages.get('public') and matched.public_reply_enabled:
        replies = matched.public_replies or []
        if replies and normalized.comment_id:
            try:
                client = client_for_connection(conn)
                text = random.choice(replies)
                client.reply_to_comment(
                    comment_id=normalized.comment_id,
                    message=text,
                    correlation_id=event.correlation_id,
                )
                stages['public'] = True
            except Exception:
                logger.exception('public comment reply failed')
                stages['public_failed'] = True

    pr_status = meta_capability_status(conn.workspace, 'private_reply')
    private_run, _ = InstagramAutomationActionRun.objects.get_or_create(
        workspace_id=conn.workspace_id,
        event=event,
        rule=matched.rule,
        action_key=f'comment_private_reply:{matched.pk}',
    )
    if (
        pr_status == 'enabled'
        and feature_enabled(conn.workspace, 'instagram_private_reply')
        and matched.private_reply_enabled
        and matched.private_reply_text
        and private_run.status != InstagramAutomationActionRun.Status.SUCCEEDED
        and normalized.comment_id
    ):
        try:
            client = client or client_for_connection(conn)
            client.private_reply_to_comment(
                page_id=conn.facebook_page_id,
                comment_id=normalized.comment_id,
                message=matched.private_reply_text,
                correlation_id=event.correlation_id,
            )
            stages['private'] = True
            InstagramMessage.objects.create(
                workspace_id=conn.workspace_id,
                conversation=conversation,
                direction=InstagramMessage.Direction.OUTBOUND,
                sender_type=InstagramMessage.SenderType.AUTOMATION,
                message_type='private_reply',
                text=matched.private_reply_text,
                delivery_status=InstagramMessage.DeliveryStatus.SENT,
                sent_at=timezone.now(),
                raw_event=event,
            )
            private_run.status = InstagramAutomationActionRun.Status.SUCCEEDED
            private_run.attempts += 1
            private_run.save(update_fields=['status', 'attempts', 'updated_at'])
        except Exception:
            logger.exception('private reply failed')
            stages['private_failed'] = True
            private_run.status = InstagramAutomationActionRun.Status.FAILED
            private_run.attempts += 1
            private_run.error_code = 'private_reply_failed'
            private_run.save(update_fields=['status', 'attempts', 'error_code', 'updated_at'])

    if matched.tag_id and not stages.get('tag'):
        contact.tags.add(matched.tag_id)
        stages['tag'] = True

    if matched.flow_id and not stages.get('flow'):
        flow = matched.flow
        if flow and flow.status == InstagramFlow.Status.ACTIVE:
            execution = start_flow_execution(
                flow=flow,
                contact=contact,
                conversation=conversation,
            )
            for _ in range(10):
                execution = execute_flow_step(execution)
                if execution.status != execution.Status.RUNNING:
                    break
            stages['flow'] = True

    cache.set(stage_key, stages, 86400)
