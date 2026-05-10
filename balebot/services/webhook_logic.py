"""پردازش بدنهٔ آپدیت بله (بدون وابستگی به HttpRequest)."""

from __future__ import annotations

import re
from typing import Any

from django.utils import timezone

from balebot.models import BotSettings, CallbackLog, Campaign, InboundMessage, Subscriber
from balebot.services import bale_api
from balebot.services.start_keyboard import (
    build_start_inline_markup,
    build_view_markup,
    parse_back_callback,
    parse_start_nav_segments,
    resolve_button_by_path,
)


def get_or_create_subscriber(from_user: dict[str, Any], chat: dict[str, Any]) -> Subscriber:
    uid = int(from_user['id'])
    cid = int(chat['id'])
    sub, _ = Subscriber.objects.update_or_create(
        bale_user_id=uid,
        defaults={
            'chat_id': cid,
            'first_name': (from_user.get('first_name') or '')[:255],
            'last_name': (from_user.get('last_name') or '')[:255],
            'username': (from_user.get('username') or '')[:255],
        },
    )
    return sub


def build_contact_keyboard(settings_obj: BotSettings) -> dict[str, Any]:
    label = (settings_obj.contact_button_label or 'تماس').strip()[:64]
    return {
        'keyboard': [[{'text': label, 'request_contact': True}]],
        'resize_keyboard': True,
        'one_time_keyboard': True,
    }


def remove_keyboard() -> dict[str, Any]:
    return {'remove_keyboard': True}


def _append_menu_flow(
    sub: Subscriber,
    *,
    kind: str,
    data: str,
    label: str = '',
    flow_key: str | None = None,
    flow_value: str | None = None,
) -> None:
    log = list(sub.menu_flow_log or [])
    log.append(
        {
            'at': timezone.now().isoformat(),
            'kind': kind,
            'data': data[:256],
            'label': (label or '')[:128],
        },
    )
    sub.menu_flow_log = log[-100:]
    update_fields = ['menu_flow_log', 'updated_at']
    if flow_key and flow_value is not None:
        ans = dict(sub.menu_flow_answers or {})
        ans[flow_key] = flow_value[:500]
        sub.menu_flow_answers = ans
        update_fields.append('menu_flow_answers')
    sub.save(update_fields=update_fields)


def _try_edit_start_markup(
    cfg: BotSettings,
    view_path: list[tuple[int, int, int]],
    chat_id: int,
    message_id: int | None,
) -> None:
    if not message_id:
        return
    mk = build_view_markup(cfg, view_path)
    if mk is None:
        mk = build_start_inline_markup(cfg)
    if not mk:
        return
    try:
        bale_api.edit_message_reply_markup(
            chat_id,
            int(message_id),
            reply_markup=mk,
        )
    except bale_api.BaleAPIError:
        pass


def parse_campaign_callback(data: str) -> Campaign | None:
    """فرمت دکمه‌ها: c{campaign_id}_{row}_{col}"""
    m = re.match(r'^c(\d+)_(\d+)_(\d+)$', (data or '').strip())
    if not m:
        return None
    pk = int(m.group(1))
    return Campaign.objects.filter(pk=pk).first()


def store_inbound_from_message(sub: Subscriber, msg: dict[str, Any]) -> None:
    mid = msg.get('message_id')
    if msg.get('contact'):
        c = msg['contact']
        ph = (c.get('phone_number') or '').strip()
        InboundMessage.objects.create(
            subscriber=sub,
            kind=InboundMessage.MessageKind.CONTACT,
            text=ph,
            bale_message_id=mid,
        )
        sub.phone_number = ph[:32]
        sub.is_registered = True
        sub.save(update_fields=['phone_number', 'is_registered', 'updated_at'])
        return

    if msg.get('text'):
        InboundMessage.objects.create(
            subscriber=sub,
            kind=InboundMessage.MessageKind.TEXT,
            text=msg.get('text') or '',
            bale_message_id=mid,
        )
        return

    if msg.get('voice'):
        fid = msg['voice'].get('file_id') or ''
        InboundMessage.objects.create(
            subscriber=sub,
            kind=InboundMessage.MessageKind.VOICE,
            file_id=fid,
            text=msg.get('caption') or '',
            bale_message_id=mid,
        )
        return

    if msg.get('photo'):
        photos = msg['photo']
        fid = photos[-1].get('file_id') if photos else ''
        InboundMessage.objects.create(
            subscriber=sub,
            kind=InboundMessage.MessageKind.PHOTO,
            file_id=fid or '',
            text=msg.get('caption') or '',
            bale_message_id=mid,
        )
        return

    if msg.get('video'):
        fid = (msg.get('video') or {}).get('file_id') or ''
        InboundMessage.objects.create(
            subscriber=sub,
            kind=InboundMessage.MessageKind.VIDEO,
            file_id=fid,
            text=msg.get('caption') or '',
            bale_message_id=mid,
        )
        return

    if msg.get('document'):
        fid = (msg.get('document') or {}).get('file_id') or ''
        InboundMessage.objects.create(
            subscriber=sub,
            kind=InboundMessage.MessageKind.DOCUMENT,
            file_id=fid,
            text=msg.get('caption') or '',
            bale_message_id=mid,
        )
        return

    InboundMessage.objects.create(
        subscriber=sub,
        kind=InboundMessage.MessageKind.OTHER,
        text='',
        bale_message_id=mid,
    )


def handle_message(msg: dict[str, Any]) -> None:
    from_user = msg.get('from') or {}
    chat = msg.get('chat') or {}
    if not from_user or not chat:
        return

    sub = get_or_create_subscriber(from_user, chat)
    text = (msg.get('text') or '').strip()
    cfg = BotSettings.get_solo()

    if text.startswith('/start'):
        welcome = (cfg.welcome_message or '').strip()
        start_markup = build_start_inline_markup(cfg)
        has_inline = start_markup is not None
        need_contact = cfg.collect_contact_on_start and not sub.is_registered
        if need_contact:
            if has_inline:
                bale_api.send_message(
                    sub.chat_id,
                    welcome,
                    reply_markup=start_markup,
                )
                prompt = (cfg.contact_prompt_message or '').strip() or (
                    'برای تکمیل ثبت‌نام، شمارهٔ خود را با دکمهٔ زیر ارسال کنید.'
                )
                bale_api.send_message(
                    sub.chat_id,
                    prompt,
                    reply_markup=build_contact_keyboard(cfg),
                )
            else:
                bale_api.send_message(
                    sub.chat_id,
                    welcome,
                    reply_markup=build_contact_keyboard(cfg),
                )
        else:
            bale_api.send_message(
                sub.chat_id,
                welcome,
                reply_markup=start_markup,
            )
        return

    if cfg.enable_help_command and text.startswith('/help'):
        hm = (cfg.help_message or '').strip()
        if hm:
            bale_api.send_message(sub.chat_id, hm)
        return

    if text.startswith('/stop'):
        if not cfg.enable_stop_command:
            return
        sub.is_active = False
        sub.save(update_fields=['is_active', 'updated_at'])
        bale_api.send_message(
            sub.chat_id,
            (cfg.unsubscribe_message or '').strip(),
            reply_markup=remove_keyboard(),
        )
        return

    if msg.get('contact'):
        store_inbound_from_message(sub, msg)
        bale_api.send_message(
            sub.chat_id,
            (cfg.registration_success_message or '').strip(),
            reply_markup=remove_keyboard(),
        )
        return

    store_inbound_from_message(sub, msg)


def handle_callback(cb: dict[str, Any]) -> None:
    from_user = cb.get('from') or {}
    if not from_user:
        return
    cid_raw = cb.get('id') or ''
    data = (cb.get('data') or '')[:256]
    msg = cb.get('message') or {}
    chat = msg.get('chat') or {}
    if not chat.get('id'):
        chat = {'id': from_user.get('id')}
    sub = get_or_create_subscriber(from_user, chat)
    data_stripped = (data or '').strip()
    chat_id = int(chat.get('id') or from_user.get('id') or 0)
    mid = msg.get('message_id')

    if data_stripped.startswith('b'):
        cfg = BotSettings.get_solo()
        flow_kind = ''
        flow_label = ''
        fk_store: str | None = None
        fv_store: str | None = None

        if data_stripped == 'bz':
            _try_edit_start_markup(cfg, [], chat_id, mid)
            flow_kind = 'root'
        elif data_stripped.startswith('bb'):
            parent = parse_back_callback(data_stripped)
            if parent is not None:
                _try_edit_start_markup(cfg, parent, chat_id, mid)
                flow_kind = 'back'
            else:
                flow_kind = 'invalid_back'
        else:
            segments = parse_start_nav_segments(data_stripped)
            if not segments:
                flow_kind = 'invalid_nav'
            else:
                btn = resolve_button_by_path(cfg, segments)
                if not btn:
                    flow_kind = 'unknown_button'
                else:
                    flow_label = str(btn.get('text') or '')[:128]
                    fk_raw = (btn.get('flow_key') or '').strip()
                    if fk_raw:
                        fk_store = fk_raw[:64]
                        fv_store = str(btn.get('text') or '').strip()[:500]
                    action = (btn.get('action') or 'none').strip().lower()
                    if action == 'submenu':
                        _try_edit_start_markup(cfg, segments, chat_id, mid)
                        flow_kind = 'submenu'
                    elif action == 'reply':
                        reply_txt = (btn.get('reply_text') or '').strip()
                        if reply_txt and chat_id:
                            try:
                                bale_api.send_message(chat_id, reply_txt[:4096])
                            except bale_api.BaleAPIError:
                                pass
                        flow_kind = 'reply'
                    else:
                        flow_kind = action or 'none'

        _append_menu_flow(
            sub,
            kind=flow_kind or 'click',
            data=data_stripped,
            label=flow_label,
            flow_key=fk_store,
            flow_value=fv_store,
        )

        CallbackLog.objects.create(
            subscriber=sub,
            callback_query_id=str(cid_raw),
            data=data,
            campaign=None,
        )
        try:
            ack = (cfg.callback_ack_message or '').strip()
            if ack:
                bale_api.answer_callback_query(str(cid_raw), text=ack[:200])
            else:
                bale_api.answer_callback_query(str(cid_raw))
        except bale_api.BaleAPIError:
            pass
        return

    camp = parse_campaign_callback(data)

    CallbackLog.objects.create(
        subscriber=sub,
        callback_query_id=str(cid_raw),
        data=data,
        campaign=camp,
    )

    try:
        cfg = BotSettings.get_solo()
        ack = (cfg.callback_ack_message or '').strip()
        if ack:
            bale_api.answer_callback_query(str(cid_raw), text=ack[:200])
        else:
            bale_api.answer_callback_query(str(cid_raw))
    except bale_api.BaleAPIError:
        pass
