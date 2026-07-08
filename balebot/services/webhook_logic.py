"""پردازش بدنهٔ آپدیت (بدون وابستگی به HttpRequest)."""

from __future__ import annotations

import re
from typing import Any

from django.utils import timezone

from balebot.models import (
    BotSettings,
    CallbackLog,
    Campaign,
    InboundMessage,
    Platform,
    Subscriber,
    SupportTicketMessage,
)
from balebot.services import messenger_api
from balebot.services import catalog_payment
from balebot.services.flow_engine import (
    get_flow,
    handle_flow_callback,
    merge_support_into_markup,
    parse_flow_back_callback,
    parse_flow_callback,
    render_root_flow,
    _send_inline_keyboard_message,
    _send_message_with_inline_markup,
)


def get_or_create_subscriber(
    cfg: BotSettings,
    from_user: dict[str, Any],
    chat: dict[str, Any],
) -> Subscriber:
    uid = int(from_user['id'])
    cid = int(chat['id'])
    sub, _ = Subscriber.objects.update_or_create(
        workspace=cfg.workspace,
        platform=cfg.platform,
        messenger_user_id=uid,
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
    rows: list[list[dict[str, Any]]] = [[{'text': label, 'request_contact': True}]]
    if settings_obj.enable_support:
        support_label = (settings_obj.support_button_label or 'پیام به پشتیبانی').strip()[:64]
        if support_label:
            rows.append([{'text': support_label}])
    return {
        'keyboard': rows,
        'resize_keyboard': True,
        'one_time_keyboard': True,
    }


def remove_keyboard() -> dict[str, Any]:
    return {'remove_keyboard': True}


def _flow_has_content(cfg: BotSettings) -> bool:
    flow = get_flow(cfg)
    root = flow.get('root') or {}
    items = root.get('items') or []
    return bool(items)


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


def parse_campaign_callback(data: str, cfg: BotSettings) -> Campaign | None:
    """فرمت دکمه‌ها: c{campaign_id}_{row}_{col}"""
    m = re.match(r'^c(\d+)_(\d+)_(\d+)$', (data or '').strip())
    if not m:
        return None
    pk = int(m.group(1))
    return Campaign.objects.filter(
        pk=pk,
        platform=cfg.platform,
        workspace=cfg.workspace,
    ).first()


def parse_support_continue_callback(data: str) -> int | None:
    m = re.match(r'^stc(\d+)$', (data or '').strip())
    if not m:
        return None
    return int(m.group(1))


def store_inbound_from_message(
    sub: Subscriber,
    msg: dict[str, Any],
    *,
    is_support_request: bool = False,
) -> InboundMessage:
    mid = msg.get('message_id')
    if msg.get('contact'):
        c = msg['contact']
        ph = (c.get('phone_number') or '').strip()
        rec = InboundMessage.objects.create(
            subscriber=sub,
            kind=InboundMessage.MessageKind.CONTACT,
            text=ph,
            messenger_message_id=mid,
            is_support_request=is_support_request,
        )
        sub.phone_number = ph[:32]
        sub.is_registered = True
        sub.save(update_fields=['phone_number', 'is_registered', 'updated_at'])
        return rec

    if msg.get('text'):
        return InboundMessage.objects.create(
            subscriber=sub,
            kind=InboundMessage.MessageKind.TEXT,
            text=msg.get('text') or '',
            messenger_message_id=mid,
            is_support_request=is_support_request,
        )

    if msg.get('voice'):
        fid = msg['voice'].get('file_id') or ''
        return InboundMessage.objects.create(
            subscriber=sub,
            kind=InboundMessage.MessageKind.VOICE,
            file_id=fid,
            text=msg.get('caption') or '',
            messenger_message_id=mid,
            is_support_request=is_support_request,
        )

    if msg.get('photo'):
        photos = msg['photo']
        fid = photos[-1].get('file_id') if photos else ''
        return InboundMessage.objects.create(
            subscriber=sub,
            kind=InboundMessage.MessageKind.PHOTO,
            file_id=fid or '',
            text=msg.get('caption') or '',
            messenger_message_id=mid,
            is_support_request=is_support_request,
        )

    if msg.get('video'):
        fid = (msg.get('video') or {}).get('file_id') or ''
        return InboundMessage.objects.create(
            subscriber=sub,
            kind=InboundMessage.MessageKind.VIDEO,
            file_id=fid,
            text=msg.get('caption') or '',
            messenger_message_id=mid,
            is_support_request=is_support_request,
        )

    if msg.get('document'):
        fid = (msg.get('document') or {}).get('file_id') or ''
        return InboundMessage.objects.create(
            subscriber=sub,
            kind=InboundMessage.MessageKind.DOCUMENT,
            file_id=fid,
            text=msg.get('caption') or '',
            messenger_message_id=mid,
            is_support_request=is_support_request,
        )

    return InboundMessage.objects.create(
        subscriber=sub,
        kind=InboundMessage.MessageKind.OTHER,
        text='',
        messenger_message_id=mid,
        is_support_request=is_support_request,
    )


def _send_start_with_flow(cfg: BotSettings, sub: Subscriber) -> None:
    platform = cfg.platform
    chat_id = sub.chat_id
    has_flow = _flow_has_content(cfg)

    if has_flow:
        render_root_flow(cfg, chat_id, sub=sub, markup_already_sent=False)
        return

    msg_normal = (cfg.start_message_normal or '').strip()
    if msg_normal:
        combined_markup = merge_support_into_markup(cfg, None) if cfg.enable_support else None
        if combined_markup:
            _send_message_with_inline_markup(cfg, chat_id, msg_normal, combined_markup)
        else:
            try:
                messenger_api.send_message(platform, chat_id, msg_normal, settings=cfg)
            except messenger_api.MessengerAPIError:
                pass
    elif cfg.enable_support:
        mk = merge_support_into_markup(cfg, None)
        if mk:
            _send_inline_keyboard_message(cfg, chat_id, mk)


def handle_message(cfg: BotSettings, msg: dict[str, Any]) -> None:
    from_user = msg.get('from') or {}
    chat = msg.get('chat') or {}
    if not from_user or not chat:
        return

    if msg.get('web_app_data'):
        catalog_payment.handle_web_app_data(cfg, msg)
        return

    if msg.get('successful_payment'):
        sp = msg['successful_payment']
        payload = (sp.get('invoice_payload') or sp.get('payload') or '').strip()
        if payload.startswith('order:'):
            from balebot.models import CatalogOrder

            token = payload.split(':', 1)[1]
            order = CatalogOrder.objects.filter(
                public_token=token,
                workspace=cfg.workspace,
                platform=cfg.platform,
            ).first()
            if order and order.status != CatalogOrder.Status.PAID:
                charge_id = str(sp.get('telegram_payment_charge_id') or sp.get('provider_payment_charge_id') or '')
                if charge_id:
                    order.payment_charge_id = charge_id[:256]
                    order.save(update_fields=['payment_charge_id', 'updated_at'])
                catalog_payment.mark_order_paid(order)
        return

    sub = get_or_create_subscriber(cfg, from_user, chat)
    text = (msg.get('text') or '').strip()
    platform = cfg.platform

    if text.startswith('/start'):
        need_contact = cfg.collect_contact_on_start and not sub.is_registered
        if need_contact:
            body_contact = (cfg.start_message_contact or '').strip()
            messenger_api.send_message(
                platform,
                sub.chat_id,
                body_contact,
                settings=cfg,
                reply_markup=build_contact_keyboard(cfg),
            )
        else:
            _send_start_with_flow(cfg, sub)
        return

    if cfg.enable_help_command and text.startswith('/help'):
        hm = (cfg.help_message or '').strip()
        if hm:
            messenger_api.send_message(platform, sub.chat_id, hm, settings=cfg)
        return

    if text.startswith('/stop'):
        if not cfg.enable_stop_command:
            return
        sub.is_active = False
        sub.save(update_fields=['is_active', 'updated_at'])
        messenger_api.send_message(
            platform,
            sub.chat_id,
            (cfg.unsubscribe_message or '').strip(),
            settings=cfg,
            reply_markup=remove_keyboard(),
        )
        return

    state = sub.flow_state or {}
    if state.get('awaiting'):
        from balebot.services.flow_engine import resume_flow
        if resume_flow(cfg, sub, msg, state):
            return

    support_button_label = (cfg.support_button_label or '').strip()
    if (
        cfg.enable_support
        and support_button_label
        and text
        and text == support_button_label
    ):
        state = dict(sub.flow_state or {})
        state.pop('support_ticket_id', None)
        sub.flow_state = state
        sub.awaiting_support_message = True
        sub.save(update_fields=['awaiting_support_message', 'flow_state', 'updated_at'])
        prompt = (cfg.support_start_prompt_message or '').strip()
        if prompt:
            messenger_api.send_message(platform, sub.chat_id, prompt, settings=cfg)
        return

    if sub.awaiting_support_message:
        state = dict(sub.flow_state or {})
        root_ticket_id = state.get('support_ticket_id')
        root_ticket = None
        if root_ticket_id:
            root_ticket = SupportTicketMessage.objects.filter(
                id=int(root_ticket_id),
                subscriber=sub,
                sender=SupportTicketMessage.Sender.USER,
            ).first()
        inbound = store_inbound_from_message(sub, msg, is_support_request=True)
        SupportTicketMessage.objects.create(
            subscriber=sub,
            sender=SupportTicketMessage.Sender.USER,
            kind=inbound.kind,
            text=inbound.text,
            file_id=inbound.file_id,
            inbound_message=inbound,
            parent_user_message=root_ticket,
        )
        sub.awaiting_support_message = False
        state.pop('support_ticket_id', None)
        sub.flow_state = state
        sub.save(update_fields=['awaiting_support_message', 'flow_state', 'updated_at'])
        wait_msg = (cfg.support_waiting_message or '').strip()
        if wait_msg:
            messenger_api.send_message(platform, sub.chat_id, wait_msg, settings=cfg)
        return

    if msg.get('contact'):
        state = sub.flow_state or {}
        if state.get('awaiting') == 'request_contact':
            from balebot.services.flow_engine import resume_flow
            if resume_flow(cfg, sub, msg, state):
                return
        already_registered = sub.is_registered
        store_inbound_from_message(sub, msg)
        if already_registered:
            messenger_api.send_message(
                platform,
                sub.chat_id,
                'شمارهٔ شما از قبل ثبت شده بود؛ نیازی به ارسال مجدد نیست.',
                settings=cfg,
                reply_markup=remove_keyboard(),
            )
            return
        messenger_api.send_message(
            platform,
            sub.chat_id,
            (cfg.registration_success_message or '').strip(),
            settings=cfg,
            reply_markup=remove_keyboard(),
        )
        if _flow_has_content(cfg):
            render_root_flow(cfg, sub.chat_id, sub=sub)
        return

    if msg.get('location'):
        state = sub.flow_state or {}
        if state.get('awaiting') == 'request_location':
            from balebot.services.flow_engine import resume_flow
            if resume_flow(cfg, sub, msg, state):
                return

    store_inbound_from_message(sub, msg)


def handle_pre_checkout_query(cfg: BotSettings, query: dict[str, Any]) -> None:
    """Validate wallet checkout before final payment confirmation."""
    query_id = str(query.get('id') or '').strip()
    if not query_id:
        return
    payload = str(query.get('invoice_payload') or '').strip()
    if not payload.startswith('order:'):
        messenger_api.answer_pre_checkout_query(
            cfg.platform,
            query_id,
            ok=False,
            error_message='صورتحساب نامعتبر است. دوباره تلاش کنید.',
            settings=cfg,
        )
        return

    from balebot.models import CatalogOrder

    token = payload.split(':', 1)[1]
    order = CatalogOrder.objects.filter(
        public_token=token,
        workspace=cfg.workspace,
        platform=cfg.platform,
    ).first()
    if not order:
        messenger_api.answer_pre_checkout_query(
            cfg.platform,
            query_id,
            ok=False,
            error_message='سفارش پیدا نشد. از مینی‌اپ دوباره خرید را انجام دهید.',
            settings=cfg,
        )
        return
    if order.status != CatalogOrder.Status.PENDING:
        messenger_api.answer_pre_checkout_query(
            cfg.platform,
            query_id,
            ok=False,
            error_message='این سفارش دیگر قابل پرداخت نیست.',
            settings=cfg,
        )
        return

    expected_amount = int(order.total_amount or 0)
    if int(query.get('total_amount') or 0) != expected_amount:
        messenger_api.answer_pre_checkout_query(
            cfg.platform,
            query_id,
            ok=False,
            error_message='مبلغ صورت‌حساب تغییر کرده است. دوباره تلاش کنید.',
            settings=cfg,
        )
        return

    messenger_api.answer_pre_checkout_query(
        cfg.platform,
        query_id,
        ok=True,
        settings=cfg,
    )


def handle_callback(cfg: BotSettings, cb: dict[str, Any]) -> None:
    platform = cfg.platform
    from_user = cb.get('from') or {}
    if not from_user:
        return
    cid_raw = cb.get('id') or ''
    data = (cb.get('data') or '')[:256]
    msg = cb.get('message') or {}
    chat = msg.get('chat') or {}
    if not chat.get('id'):
        chat = {'id': from_user.get('id')}
    sub = get_or_create_subscriber(cfg, from_user, chat)
    data_stripped = (data or '').strip()
    chat_id = int(chat.get('id') or from_user.get('id') or 0)
    mid = msg.get('message_id')

    if data_stripped.startswith('f') or data_stripped == 'bsup':
        flow_kind = ''
        flow_label = ''
        fk_store: str | None = None
        fv_store: str | None = None

        if data_stripped == 'bsup':
            sub.awaiting_support_message = True
            sub.save(update_fields=['awaiting_support_message', 'updated_at'])
            prompt = (cfg.support_start_prompt_message or '').strip()
            if prompt and chat_id:
                try:
                    messenger_api.send_message(platform, chat_id, prompt, settings=cfg)
                except messenger_api.MessengerAPIError:
                    pass
            flow_kind = 'support'
        elif parse_flow_callback(data_stripped) or parse_flow_back_callback(data_stripped):
            flow_kind, flow_label = handle_flow_callback(
                cfg, sub, data_stripped, chat_id, mid,
            )
            ref_slug = flow_label
            if ref_slug:
                fk_store = 'flow_button'
                fv_store = ref_slug
        else:
            flow_kind = 'invalid_flow'

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
                messenger_api.answer_callback_query(
                    platform, str(cid_raw), settings=cfg, text=ack[:200],
                )
            else:
                messenger_api.answer_callback_query(platform, str(cid_raw), settings=cfg)
        except messenger_api.MessengerAPIError:
            pass
        return

    support_ticket_id = parse_support_continue_callback(data_stripped)
    if support_ticket_id is not None:
        root_ticket = SupportTicketMessage.objects.filter(
            id=support_ticket_id,
            subscriber=sub,
            sender=SupportTicketMessage.Sender.USER,
        ).first()
        if root_ticket:
            state = dict(sub.flow_state or {})
            state['support_ticket_id'] = root_ticket.id
            sub.flow_state = state
            sub.awaiting_support_message = True
            sub.save(update_fields=['flow_state', 'awaiting_support_message', 'updated_at'])
            prompt = 'ادامه گفت‌وگو فعال شد. پیام بعدی‌ات در همین تیکت ثبت می‌شود.'
            try:
                messenger_api.send_message(platform, chat_id, prompt, settings=cfg)
            except messenger_api.MessengerAPIError:
                pass
            label = 'ادامه گفت‌وگو'
        else:
            label = 'ادامه گفت‌وگو نامعتبر'

        _append_menu_flow(
            sub,
            kind='support_continue',
            data=data_stripped,
            label=label,
            flow_key='support_ticket',
            flow_value=str(support_ticket_id),
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
                messenger_api.answer_callback_query(
                    platform, str(cid_raw), settings=cfg, text=ack[:200],
                )
            else:
                messenger_api.answer_callback_query(platform, str(cid_raw), settings=cfg)
        except messenger_api.MessengerAPIError:
            pass
        return

    camp = parse_campaign_callback(data, cfg)

    CallbackLog.objects.create(
        subscriber=sub,
        callback_query_id=str(cid_raw),
        data=data,
        campaign=camp,
    )

    try:
        ack = (cfg.callback_ack_message or '').strip()
        if ack:
            messenger_api.answer_callback_query(
                platform, str(cid_raw), settings=cfg, text=ack[:200],
            )
        else:
            messenger_api.answer_callback_query(platform, str(cid_raw), settings=cfg)
    except messenger_api.MessengerAPIError:
        pass
