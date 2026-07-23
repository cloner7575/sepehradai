from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import timedelta

from django.utils import timezone

from instagram.automation.models import (
    InstagramAutomationActionRun,
    InstagramAutomationRule,
    InstagramRuleCondition,
    InstagramMedia,
)
from instagram.automation.services.normalize import NormalizedEvent
from instagram.automation.services.persian_normalize import match_text

logger = logging.getLogger(__name__)


@dataclass
class RuleMatchResult:
    rule: InstagramAutomationRule | None
    reason: str
    matched_rules: list[int]


def _cooldown_key(contact_id: int) -> str:
    return f'rule_cooldown:{contact_id}'


def _in_cooldown(rule: InstagramAutomationRule, contact_id: int) -> bool:
    if not rule.cooldown_seconds:
        return False
    return rule.action_runs.filter(
        action_key=_cooldown_key(contact_id),
        status=InstagramAutomationActionRun.Status.SUCCEEDED,
        created_at__gt=timezone.now() - timedelta(seconds=rule.cooldown_seconds),
    ).exists()


def _set_cooldown(rule: InstagramAutomationRule, contact_id: int, event: NormalizedEvent) -> None:
    if not rule.cooldown_seconds or not event.raw_event_id:
        return
    InstagramAutomationActionRun.objects.get_or_create(
        workspace_id=rule.workspace_id,
        event_id=event.raw_event_id,
        rule=rule,
        action_key=_cooldown_key(contact_id),
        defaults={'status': InstagramAutomationActionRun.Status.SUCCEEDED},
    )


def _condition_matches(cond: InstagramRuleCondition, event: NormalizedEvent) -> bool:
    field = cond.field or 'text'
    if field == 'text':
        subject = event.text
    elif field == 'message_type':
        subject = event.message_type
    elif field == 'event_type':
        subject = event.event_type
    else:
        subject = str((event.extra or {}).get(field) or '')
    value = cond.value
    if isinstance(value, dict) and 'value' in value:
        value = value['value']
    return match_text(
        subject,
        operator=cond.operator,
        value=value,
        case_sensitive=cond.case_sensitive,
        normalize=cond.normalize_persian,
    )


def _trigger_matches(rule: InstagramAutomationRule, event: NormalizedEvent) -> bool:
    t = rule.trigger_type
    et = event.event_type
    if t == InstagramAutomationRule.TriggerType.MESSAGE_RECEIVED:
        return et in ('message.received', 'message.attachment')
    if t == InstagramAutomationRule.TriggerType.KEYWORD:
        return et.startswith('message.') or et.startswith('comment')
    if t == InstagramAutomationRule.TriggerType.EXACT_TEXT:
        return True
    if t == InstagramAutomationRule.TriggerType.IMAGE:
        return event.message_type in ('image', 'photo')
    if t == InstagramAutomationRule.TriggerType.VIDEO:
        return event.message_type == 'video'
    if t == InstagramAutomationRule.TriggerType.AUDIO:
        return event.message_type in ('audio', 'voice')
    if t == InstagramAutomationRule.TriggerType.STORY_REPLY:
        return et == 'story_reply'
    if t == InstagramAutomationRule.TriggerType.STORY_MENTION:
        return et == 'mention'
    if t == InstagramAutomationRule.TriggerType.COMMENT_ANY:
        return et.startswith('comment')
    if t == InstagramAutomationRule.TriggerType.COMMENT_KEYWORD:
        return et.startswith('comment')
    if t == InstagramAutomationRule.TriggerType.FALLBACK:
        return True
    if t == InstagramAutomationRule.TriggerType.REFERRAL:
        return et in ('referral', 'postback')
    if t == InstagramAutomationRule.TriggerType.WELCOME:
        return et in ('message.received', 'message.attachment')
    # keyword-like triggers
    if t in (
        InstagramAutomationRule.TriggerType.STARTS_WITH,
        InstagramAutomationRule.TriggerType.ENDS_WITH,
        InstagramAutomationRule.TriggerType.ANY_KEYWORDS,
        InstagramAutomationRule.TriggerType.ALL_KEYWORDS,
        InstagramAutomationRule.TriggerType.EXCLUDE_KEYWORDS,
        InstagramAutomationRule.TriggerType.NUMBER,
    ):
        return bool(event.text)
    return et.startswith('message.')



def _content_scope_matches(rule, event: NormalizedEvent, connection_id: int) -> bool:
    schedule = rule.schedule or {}
    scope = schedule.get('content_scope') or 'all'
    if scope == 'all':
        return True
    source_id = str(event.media_id or event.story_id or '')
    if not source_id:
        return False
    if scope == 'selected':
        selected = {str(value) for value in schedule.get('selected_media_ids') or []}
        return source_id in selected
    if scope == 'product_bound':
        return InstagramMedia.objects.filter(
            connection_id=connection_id,
            external_media_id=source_id,
            product__isnull=False,
            is_active=True,
        ).exists()
    return False


def evaluate_rules(
    *,
    workspace_id: int,
    connection_id: int,
    contact_id: int,
    event: NormalizedEvent,
    is_first_interaction: bool = False,
) -> RuleMatchResult:
    qs = (
        InstagramAutomationRule.objects.filter(
            workspace_id=workspace_id,
            is_active=True,
        )
        .filter(models_q_connection(connection_id))
        .prefetch_related('conditions')
        .order_by('priority', 'created_at')
    )
    matched: list[InstagramAutomationRule] = []
    for rule in qs:
        if rule.trigger_type == InstagramAutomationRule.TriggerType.FIRST_INTERACTION and not is_first_interaction:
            continue
        if rule.trigger_type == InstagramAutomationRule.TriggerType.FIRST_CONVERSATION and not is_first_interaction:
            continue
        if not _trigger_matches(rule, event):
            continue
        if _in_cooldown(rule, contact_id):
            continue
        if not _content_scope_matches(rule, event, connection_id):
            continue
        conditions = list(rule.conditions.all())
        if conditions:
            results = [_condition_matches(c, event) for c in conditions]
            if rule.match_mode == InstagramAutomationRule.MatchMode.ALL:
                if not all(results):
                    continue
            elif not any(results):
                continue
        else:
            # بدون شرط: برای keyword triggers نیاز به value در schedule یا skip
            if rule.trigger_type in (
                InstagramAutomationRule.TriggerType.KEYWORD,
                InstagramAutomationRule.TriggerType.EXACT_TEXT,
                InstagramAutomationRule.TriggerType.ANY_KEYWORDS,
            ):
                kw = (rule.schedule or {}).get('keywords') or (rule.schedule or {}).get('text')
                if kw:
                    op = 'any_of' if isinstance(kw, list) else 'contains'
                    if not match_text(event.text, operator=op, value=kw):
                        continue
        matched.append(rule)
        if rule.stop_after_match:
            break

    # specificity: قوانین با شرط بیشتر اول — قبلاً با priority مرتب شده
    if not matched:
        fallback = (
            InstagramAutomationRule.objects.filter(
                workspace_id=workspace_id,
                is_active=True,
                trigger_type=InstagramAutomationRule.TriggerType.FALLBACK,
            )
            .filter(models_q_connection(connection_id))
            .order_by('priority', 'created_at')
            .first()
        )
        if fallback and not _in_cooldown(fallback, contact_id):
            _set_cooldown(fallback, contact_id, event)
            return RuleMatchResult(rule=fallback, reason='fallback', matched_rules=[fallback.id])
        return RuleMatchResult(rule=None, reason='no_match', matched_rules=[])

    winner = matched[0]
    _set_cooldown(winner, contact_id, event)
    InstagramAutomationRule.objects.filter(pk=winner.pk).update(
        last_executed_at=timezone.now(),
        execution_count=winner.execution_count + 1,
    )
    return RuleMatchResult(
        rule=winner,
        reason='priority_match',
        matched_rules=[r.id for r in matched],
    )


def models_q_connection(connection_id: int):
    from django.db.models import Q

    return Q(connection_id=connection_id) | Q(connection__isnull=True)
