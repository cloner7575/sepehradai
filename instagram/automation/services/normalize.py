from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class NormalizedEvent:
    event_type: str
    connection_id: int | None
    workspace_id: int | None
    correlation_id: str
    raw_event_id: int | None = None
    sender_scoped_id: str = ''
    recipient_scoped_id: str = ''
    external_message_id: str = ''
    text: str = ''
    message_type: str = 'text'
    media_url: str = ''
    comment_id: str = ''
    media_id: str = ''
    story_id: str = ''
    story_url: str = ''
    postback_payload: str = ''
    is_echo: bool = False
    extra: dict[str, Any] = field(default_factory=dict)


def normalize_webhook_event(
    *,
    event_type: str,
    payload: dict,
    connection_id: int | None,
    workspace_id: int | None,
    correlation_id: str,
    raw_event_id: int | None = None,
) -> NormalizedEvent:
    if event_type.startswith('message.'):
        return _normalize_message(
            event_type=event_type,
            payload=payload,
            connection_id=connection_id,
            workspace_id=workspace_id,
            correlation_id=correlation_id,
            raw_event_id=raw_event_id,
        )
    if 'comments' in event_type or event_type.endswith('.comments'):
        return _normalize_comment(
            event_type=event_type,
            payload=payload,
            connection_id=connection_id,
            workspace_id=workspace_id,
            correlation_id=correlation_id,
            raw_event_id=raw_event_id,
        )
    if 'mentions' in event_type:
        value = payload.get('value') or payload
        return NormalizedEvent(
            event_type='mention',
            connection_id=connection_id,
            workspace_id=workspace_id,
            correlation_id=correlation_id,
            raw_event_id=raw_event_id,
            media_id=str(value.get('media_id') or ''),
            sender_scoped_id=str((value.get('from') or {}).get('id') or ''),
            text=str(value.get('text') or ''),
            extra={'value': value},
        )
    return NormalizedEvent(
        event_type=event_type,
        connection_id=connection_id,
        workspace_id=workspace_id,
        correlation_id=correlation_id,
        raw_event_id=raw_event_id,
        extra={'payload': payload},
    )


def _normalize_message(**kwargs) -> NormalizedEvent:
    payload = kwargs['payload']
    sender = str((payload.get('sender') or {}).get('id') or '')
    recipient = str((payload.get('recipient') or {}).get('id') or '')
    message = payload.get('message') or {}
    postback = payload.get('postback') or {}
    referral = payload.get('referral') or postback.get('referral') or {}
    reaction = payload.get('reaction') or {}
    text = str(message.get('text') or '')
    mid = str(message.get('mid') or '')
    msg_type = 'text'
    media_url = ''
    attachments = message.get('attachments') or []
    if attachments:
        att = attachments[0] or {}
        msg_type = str(att.get('type') or 'attachment')
        media_url = str((att.get('payload') or {}).get('url') or '')
    is_echo = bool(message.get('is_echo'))
    event_type = kwargs['event_type']
    story = (message.get('reply_to') or {}).get('story') or {}
    if story:
        event_type = 'story_reply'
    elif postback:
        event_type = 'postback'
        text = str(postback.get('title') or postback.get('payload') or '')
    elif referral:
        event_type = 'referral'
    elif reaction:
        event_type = 'reaction'
    return NormalizedEvent(
        event_type=event_type,
        connection_id=kwargs['connection_id'],
        workspace_id=kwargs['workspace_id'],
        correlation_id=kwargs['correlation_id'],
        raw_event_id=kwargs.get('raw_event_id'),
        sender_scoped_id=sender,
        recipient_scoped_id=recipient,
        external_message_id=mid,
        text=text,
        message_type=msg_type,
        media_url=media_url,
        media_id=str(story.get('id') or referral.get('media_id') or ''),
        story_id=str(story.get('id') or ''),
        story_url=str(story.get('url') or ''),
        postback_payload=str(postback.get('payload') or ''),
        is_echo=is_echo,
        extra={
            'timestamp': payload.get('timestamp'),
            'attachments': attachments,
            'reply_to': message.get('reply_to') or {},
            'referral': referral,
            'postback': postback,
            'reaction': reaction,
            'read': payload.get('read') or {},
        },
    )


def _normalize_comment(**kwargs) -> NormalizedEvent:
    payload = kwargs['payload']
    value = payload.get('value') or payload
    from_user = value.get('from') or {}
    return NormalizedEvent(
        event_type='comment.created',
        connection_id=kwargs['connection_id'],
        workspace_id=kwargs['workspace_id'],
        correlation_id=kwargs['correlation_id'],
        raw_event_id=kwargs.get('raw_event_id'),
        sender_scoped_id=str(from_user.get('id') or ''),
        text=str(value.get('text') or ''),
        comment_id=str(value.get('id') or ''),
        media_id=str(value.get('media') or {}).get('id')
        if isinstance(value.get('media'), dict)
        else str(value.get('media_id') or ''),
        extra={'username': from_user.get('username') or ''},
    )
