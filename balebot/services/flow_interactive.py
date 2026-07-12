"""نودها و اکشن‌های تعاملی موتور جریان /start."""

from __future__ import annotations

import html
import logging
import re
import uuid
from typing import Any
from urllib.parse import quote

from django.db import IntegrityError

from balebot.models import (
    BotSettings,
    CatalogItem,
    CatalogOrder,
    CatalogSettings,
    Platform,
    Subscriber,
    SubscriberTag,
    Tag,
)
from balebot.services import messenger_api
from balebot.services.flow_engine import (
    _ButtonRef,
    _send_inline_keyboard_message,
    _send_message_with_inline_markup,
    build_markup_for_buttons_node,
    encode_flow_callback,
    get_flow,
    get_or_create_tag_for_slug,
    normalize_inline_url,
    send_default_text,
    send_sequence_items,
)

logger = logging.getLogger(__name__)

_GOTO_VISITS = 32
_PHONE_RE = re.compile(r'^(\+98|0)?9\d{9}$')
_FLOW_RECHECK_CB = re.compile(r'^fr(n_[a-zA-Z0-9_]{1,48})$')


def encode_flow_recheck_callback(node_id: str) -> str:
    return f'fr{node_id}'[:64]


def parse_flow_recheck_callback(data: str) -> str | None:
    m = _FLOW_RECHECK_CB.match((data or '').strip())
    if m:
        return m.group(1)
    return None


def _clip(text: Any, limit: int) -> str:
    return str(text or '').strip()[:limit]


def _save_flow_answer(sub: Subscriber, key: str, value: Any) -> None:
    answers = dict(sub.menu_flow_answers or {})
    if isinstance(value, dict):
        answers[key] = value
    else:
        answers[key] = str(value)[:500]
    sub.menu_flow_answers = answers
    sub.save(update_fields=['menu_flow_answers', 'updated_at'])


def _clear_flow_state(sub: Subscriber) -> None:
    sub.flow_state = {}
    sub.save(update_fields=['flow_state', 'updated_at'])


def _set_flow_state(sub: Subscriber, state: dict[str, Any]) -> None:
    sub.flow_state = state
    sub.save(update_fields=['flow_state', 'updated_at'])


def _subscriber_has_tag(sub: Subscriber, slug: str) -> bool:
    return sub.tags.filter(slug=slug).exists()


def _assign_tags(sub: Subscriber, add: list[str], remove: list[str]) -> None:
    for slug in remove:
        slug = slug.strip()
        if not slug:
            continue
        sub.tags.filter(slug=slug).delete()
    for slug in add:
        slug = slug.strip()
        if not slug:
            continue
        tag = get_or_create_tag_for_slug(slug, sub.platform, sub.workspace)
        if tag:
            try:
                SubscriberTag.objects.get_or_create(subscriber=sub, tag=tag)
            except IntegrityError:
                pass


def find_flow_node_by_id(cfg: BotSettings, node_id: str) -> dict[str, Any] | None:
    """جستجوی بازگشتی نود با id در کل جریان."""
    flow = get_flow(cfg)
    root = flow.get('root') or {}

    def walk(node: Any) -> dict[str, Any] | None:
        if not isinstance(node, dict):
            return None
        if node.get('id') == node_id:
            return node
        ntype = str(node.get('type', '')).lower()
        if ntype == 'sequence':
            for item in node.get('items') or []:
                found = walk(item)
                if found:
                    return found
        elif ntype == 'buttons':
            for row in node.get('rows') or []:
                if not isinstance(row, list):
                    continue
                for btn in row:
                    if not isinstance(btn, dict):
                        continue
                    if btn.get('id') == node_id:
                        return btn
                    action = btn.get('action')
                    if isinstance(action, dict):
                        found = walk(action)
                        if found:
                            return found
        else:
            for key in ('then', 'else', 'next', 'on_complete', 'resume'):
                child = node.get(key)
                if isinstance(child, dict):
                    found = walk(child)
                    if found:
                        return found
                elif key == 'steps' and isinstance(child, list):
                    for step in child:
                        found = walk(step)
                        if found:
                            return found
        return None

    return walk(root)


def _webapp_path_segment(value: str) -> str:
    return quote((value or '').strip(), safe='-._~')


def _evaluate_condition(cfg: BotSettings, sub: Subscriber, cond: dict[str, Any]) -> bool:
    kind = _clip(cond.get('kind'), 32).lower()
    if kind == 'has_tag':
        return _subscriber_has_tag(sub, _clip(cond.get('value'), 140))
    if kind == 'is_registered':
        return sub.is_registered
    if kind == 'answer_equals':
        key = _clip(cond.get('key'), 64)
        expected = _clip(cond.get('value'), 500)
        answers = sub.menu_flow_answers or {}
        return str(answers.get(key, '')).strip() == expected
    return False


def _build_webapp_url(cfg: BotSettings, target: dict[str, Any] | None) -> str:
    catalog = CatalogSettings.objects.filter(
        workspace=cfg.workspace,
        platform=cfg.platform,
    ).first()
    if not catalog:
        return ''
    base = catalog.build_mini_app_url(cfg).rstrip('/')
    if not base:
        return ''
    if not isinstance(target, dict):
        return base + '/'
    kind = _clip(target.get('kind'), 16).lower()
    value = _clip(target.get('value'), 512)
    if kind == 'category' and value:
        return f'{base}/category/{_webapp_path_segment(value)}'
    if kind == 'item' and value:
        return f'{base}/item/{_webapp_path_segment(value)}'
    if kind in ('flash_sale', 'sale'):
        return f'{base}/sale'
    if kind == 'library':
        return f'{base}/library'
    if kind == 'cart':
        return f'{base}/cart'
    if kind == 'tag' and value:
        return f'{base}/?tag={_webapp_path_segment(value)}'
    if kind == 'path' and value:
        path = value if value.startswith('/') else f'/{value}'
        return f'{base}{path}'
    if kind == 'url' and value:
        if value.startswith('http://') or value.startswith('https://'):
            return value
        return f'{base}/{value.lstrip("/")}'
    return base + '/'


def _fulfillment_label(status: str) -> str:
    labels = {
        'pending': 'در انتظار پرداخت',
        'c2c_pending': 'در انتظار تأیید کارت به کارت',
        'paid': 'پرداخت‌شده',
        'preparing': 'در حال آماده‌سازی',
        'shipped': 'ارسال‌شده',
        'delivered': 'تحویل‌شده',
        'cancelled': 'لغوشده',
        'returned': 'مرجوعی',
        'failed': 'ناموفق',
        'request': 'درخواست',
    }
    return labels.get(status, status)


def _send_text(cfg: BotSettings, chat_id: int, text: str) -> None:
    body = (text or '').strip()
    if not body:
        return
    try:
        messenger_api.send_message(cfg.platform, chat_id, body[:4096], settings=cfg)
    except messenger_api.MessengerAPIError:
        pass


def _remove_reply_keyboard(cfg: BotSettings, chat_id: int, text: str) -> None:
    body = (text or '').strip() or ' '
    markup = {'remove_keyboard': True, 'selective': False}
    try:
        messenger_api.send_message(
            cfg.platform,
            chat_id,
            body[:4096],
            settings=cfg,
            reply_markup=markup,
        )
    except messenger_api.MessengerAPIError:
        pass


def _execute_node(
    cfg: BotSettings,
    sub: Subscriber,
    chat_id: int,
    node: dict[str, Any],
    *,
    message_id: int | None = None,
    visited: set[str] | None = None,
) -> str:
    """اجرای یک نود/اکشن تعاملی."""
    visited = visited or set()
    ntype = str(node.get('type', '')).lower()
    nid = str(node.get('id') or '')
    if nid and nid in visited:
        send_default_text(cfg, chat_id)
        return 'loop'
    if nid:
        visited.add(nid)

    if ntype == 'text':
        _send_text(cfg, chat_id, node.get('body') or '')
        return 'text'

    if ntype == 'sequence':
        send_sequence_items(cfg, chat_id, node, merge_button_markup=False)
        return 'sequence'

    if ntype == 'condition':
        cond = node.get('if') if isinstance(node.get('if'), dict) else {}
        branch = node.get('then') if _evaluate_condition(cfg, sub, cond) else node.get('else')
        if isinstance(branch, dict):
            return _execute_node(cfg, sub, chat_id, branch, message_id=message_id, visited=visited)
        return 'condition'

    if ntype == 'goto':
        target_id = _clip(node.get('target_id'), 16)
        if not target_id:
            return 'goto_missing'
        if len(visited) >= _GOTO_VISITS:
            send_default_text(cfg, chat_id)
            return 'goto_limit'
        target = find_flow_node_by_id(cfg, target_id)
        if not target:
            send_default_text(cfg, chat_id)
            return 'goto_unknown'
        if 'action' in target and isinstance(target.get('action'), dict):
            return execute_interactive_action(
                cfg, sub, _ButtonRef(target, []), chat_id,
                message_id=message_id, visited=visited,
            )
        return _execute_node(cfg, sub, chat_id, target, message_id=message_id, visited=visited)

    if ntype == 'tag':
        add = node.get('add') if isinstance(node.get('add'), list) else []
        remove = node.get('remove') if isinstance(node.get('remove'), list) else []
        _assign_tags(sub, [str(s) for s in add], [str(s) for s in remove])
        return 'tag'

    if ntype == 'handoff':
        sub.awaiting_support_message = True
        sub.save(update_fields=['awaiting_support_message', 'updated_at'])
        _send_text(cfg, chat_id, node.get('message') or 'پیامت رو بفرست، همکارمون جواب می‌ده.')
        return 'handoff'

    if ntype == 'input':
        prompt = _clip(node.get('prompt'), 500) or 'لطفاً پاسخ بده:'
        save_key = _clip(node.get('save_key'), 64) or 'answer'
        validate = _clip(node.get('validate'), 16) or 'text'
        _set_flow_state(sub, {
            'awaiting': 'input',
            'save_key': save_key,
            'validate': validate,
            'resume': node.get('next'),
        })
        _send_text(cfg, chat_id, prompt)
        return 'input'

    if ntype == 'form':
        steps = node.get('steps') if isinstance(node.get('steps'), list) else []
        if not steps:
            return 'form_empty'
        first = steps[0]
        if not isinstance(first, dict):
            return 'form_empty'
        _set_flow_state(sub, {
            'awaiting': 'form',
            'steps': steps,
            'step_index': 0,
            'on_complete': node.get('on_complete') if isinstance(node.get('on_complete'), dict) else {},
        })
        _send_text(cfg, chat_id, _clip(first.get('prompt'), 500) or 'لطفاً پاسخ بده:')
        return 'form'

    if ntype == 'order_status':
        prompt = _clip(node.get('prompt'), 500) or 'شماره سفارشت رو بفرست:'
        _set_flow_state(sub, {'awaiting': 'order_lookup'})
        _send_text(cfg, chat_id, prompt)
        return 'order_status'

    if ntype == 'my_orders':
        limit = int(node.get('limit') or 5)
        limit = max(1, min(limit, 20))
        orders = CatalogOrder.objects.filter(
            workspace=cfg.workspace,
            platform=cfg.platform,
            subscriber=sub,
        ).order_by('-created_at')[:limit]
        if not orders:
            _send_text(cfg, chat_id, 'هنوز سفارشی ثبت نکردی.')
            return 'my_orders_empty'
        lines = ['📦 سفارش‌های اخیر شما:']
        for o in orders:
            status = _fulfillment_label(o.fulfillment_status or o.status)
            track = f' — کد رهگیری: {o.tracking_code}' if o.tracking_code else ''
            lines.append(f'#{o.pk} — {status}{track}')
        _send_text(cfg, chat_id, '\n'.join(lines))
        return 'my_orders'

    if ntype == 'location_card':
        try:
            lat = float(node.get('lat'))
            lng = float(node.get('lng'))
        except (TypeError, ValueError):
            return 'location_invalid'
        address = _clip(node.get('address'), 500)
        hours = _clip(node.get('hours'), 200)
        try:
            messenger_api.send_location(cfg.platform, chat_id, lat, lng, settings=cfg)
        except messenger_api.MessengerAPIError:
            pass
        body = '\n'.join(x for x in [address, f'ساعت کاری: {hours}' if hours else ''] if x)
        if body:
            _send_text(cfg, chat_id, body)
        return 'location_card'

    if ntype == 'contact_card':
        phone = _clip(node.get('phone'), 20)
        name = _clip(node.get('name'), 64) or 'پشتیبانی'
        if not phone:
            return 'contact_invalid'
        try:
            messenger_api.send_contact(cfg.platform, chat_id, phone, name, settings=cfg)
        except messenger_api.MessengerAPIError:
            _send_text(cfg, chat_id, f'📞 {name}: {phone}')
        return 'contact_card'

    if ntype == 'coupon':
        dc = None
        code = ''
        if cfg and cfg.workspace_id:
            from balebot.services.discount import coupon_display_message, get_discount_code_for_flow

            dc = get_discount_code_for_flow(
                cfg.workspace,
                cfg.platform,
                discount_id=node.get('discount_id'),
                code=str(node.get('code', '') or ''),
            )
            if dc:
                code = dc.code
        if not code:
            code = _clip(node.get('code'), 40)
        message = coupon_display_message(dc, code, _clip(node.get('message'), 500))
        if code:
            _send_text(cfg, chat_id, f'{message}\n\n🎁 `{code}`')
        return 'coupon'

    if ntype == 'faq':
        items = node.get('items') if isinstance(node.get('items'), list) else []
        if not items:
            return 'faq_empty'
        title = _clip(node.get('title'), 120) or 'سوالات متداول'
        rows: list[list[dict[str, str]]] = []
        for idx, item in enumerate(items[:12]):
            if not isinstance(item, dict):
                continue
            q = _clip(item.get('q'), 64)
            if not q:
                continue
            cb_id = f'n_{uuid.uuid4().hex[:8]}'
            if not sub.flow_state:
                sub.flow_state = {}
            faq_map = dict((sub.flow_state or {}).get('faq_answers') or {})
            faq_map[cb_id] = _clip(item.get('a'), 2000)
            state = dict(sub.flow_state or {})
            state['faq_answers'] = faq_map
            sub.flow_state = state
            sub.save(update_fields=['flow_state', 'updated_at'])
            rows.append([{'text': q[:64], 'callback_data': encode_flow_callback(cb_id)}])
        if rows:
            mk = {'inline_keyboard': rows}
            _send_text(cfg, chat_id, title)
            _send_inline_keyboard_message(cfg, chat_id, mk)
        return 'faq'

    if ntype == 'join_gate':
        channel = _clip(node.get('channel'), 120)
        prompt = _clip(node.get('prompt'), 500) or 'اول عضو کانال شو 👇'
        then = node.get('then')
        gate_id = nid or f'n_{uuid.uuid4().hex[:8]}'
        _set_flow_state(sub, {
            'awaiting': 'join_gate',
            'channel': channel,
            'then': then,
            'gate_id': gate_id,
        })
        if _check_channel_member(cfg, sub, channel):
            _clear_flow_state(sub)
            if isinstance(then, dict):
                return _execute_node(cfg, sub, chat_id, then, message_id=message_id, visited=visited)
            return 'join_gate_ok'
        invite = normalize_inline_url(channel if channel.startswith('http') else f'https://t.me/{channel.lstrip("@")}', cfg=cfg)
        rows = []
        if invite:
            rows.append([{'text': 'عضویت در کانال', 'url': invite}])
        rows.append([{'text': 'بررسی مجدد', 'callback_data': encode_flow_recheck_callback(gate_id)}])
        sent_with_markup = _send_message_with_inline_markup(
            cfg,
            chat_id,
            prompt,
            {'inline_keyboard': rows},
        )
        if not sent_with_markup:
            _send_text(cfg, chat_id, prompt)
            _send_inline_keyboard_message(cfg, chat_id, {'inline_keyboard': rows})
        return 'join_gate'

    if ntype == 'request_contact':
        prompt = _clip(node.get('prompt'), 500) or 'شماره‌ت رو به اشتراک بذار'
        assign_tag = _clip(node.get('assign_tag'), 140)
        resume = node.get('resume')
        _set_flow_state(sub, {
            'awaiting': 'request_contact',
            'assign_tag': assign_tag,
            'resume': resume,
        })
        label = (cfg.contact_button_label or 'ارسال شماره تماس').strip()[:64]
        rows: list[list[dict[str, Any]]] = [[{'text': label, 'request_contact': True}]]
        try:
            messenger_api.send_message(
                cfg.platform, chat_id, prompt,
                settings=cfg, reply_markup={'keyboard': rows, 'resize_keyboard': True, 'one_time_keyboard': True},
            )
        except messenger_api.MessengerAPIError:
            pass
        return 'request_contact'

    if ntype == 'request_location':
        prompt = _clip(node.get('prompt'), 500) or 'موقعیتت رو بفرست'
        save_key = _clip(node.get('save_key'), 64) or 'loc'
        resume = node.get('resume')
        _set_flow_state(sub, {
            'awaiting': 'request_location',
            'save_key': save_key,
            'resume': resume,
        })
        label = 'ارسال موقعیت'
        rows = [[{'text': label, 'request_location': True}]]
        try:
            messenger_api.send_message(
                cfg.platform, chat_id, prompt,
                settings=cfg, reply_markup={'keyboard': rows, 'resize_keyboard': True, 'one_time_keyboard': True},
            )
        except messenger_api.MessengerAPIError:
            pass
        return 'request_location'

    if ntype == 'invoice':
        return _send_flow_invoice(cfg, sub, chat_id, node)

    if ntype == 'webapp':
        label = _clip(node.get('label'), 64) or '🛍 ورود به فروشگاه'
        url = _build_webapp_url(cfg, node.get('target') if isinstance(node.get('target'), dict) else None)
        if not url:
            send_default_text(cfg, chat_id)
            return 'webapp_missing'
        mk = {'inline_keyboard': [[{'text': label, 'web_app': {'url': url}}]]}
        _send_inline_keyboard_message(cfg, chat_id, mk)
        return 'webapp'

    if ntype == 'buttons':
        mk = build_markup_for_buttons_node(node, cfg=cfg)
        if mk:
            _send_inline_keyboard_message(cfg, chat_id, mk)
            return 'buttons'
        return 'buttons_empty'

    return 'unknown'


def _check_channel_member(cfg: BotSettings, sub: Subscriber, channel: str) -> bool:
    channel = (channel or '').strip()
    if not channel:
        return True
    try:
        result = messenger_api.get_chat_member(
            cfg.platform, channel, sub.messenger_user_id, settings=cfg,
        )
        member = result.get('result') or {}
        status = (member.get('status') or '').strip().lower()
        return status in {'member', 'administrator', 'creator'}
    except messenger_api.MessengerAPIError:
        return False


def _send_flow_invoice(cfg: BotSettings, sub: Subscriber, chat_id: int, node: dict[str, Any]) -> str:
    catalog = CatalogSettings.objects.filter(
        workspace=cfg.workspace, platform=cfg.platform,
    ).first()
    if not catalog or not catalog.payment_bale_ready():
        _send_text(cfg, chat_id, 'پرداخت درون‌رباتی فعلاً فعال نیست.')
        return 'invoice_disabled'

    amount = int(node.get('amount') or 0)
    item_slug = _clip(node.get('item_slug'), 120)
    if item_slug:
        item = CatalogItem.objects.filter(
            workspace=cfg.workspace, platform=cfg.platform, slug=item_slug, is_active=True,
        ).first()
        if item and item.price:
            amount = int(item.price)
    if amount <= 0:
        _send_text(cfg, chat_id, 'مبلغ پرداخت معتبر نیست.')
        return 'invoice_invalid'

    title = _clip(node.get('title'), 32) or 'پرداخت'
    description = _clip(node.get('description'), 255) or title
    card = ''.join(ch for ch in (catalog.bale_payment_card_number or '') if ch.isdigit())
    payload = f'flowinv:{sub.pk}:{uuid.uuid4().hex[:16]}'
    try:
        messenger_api.send_invoice(
            cfg.platform,
            chat_id,
            title=title,
            description=description,
            payload=payload[:128],
            provider_token=card,
            prices=[{'label': title, 'amount': amount}],
            settings=cfg,
        )
    except messenger_api.MessengerAPIError:
        _send_text(cfg, chat_id, 'ارسال صورت‌حساب ناموفق بود.')
        return 'invoice_failed'
    return 'invoice'


def _validate_input(value: str, validate: str) -> bool:
    v = (value or '').strip()
    if not v:
        return False
    if validate == 'number':
        return v.replace(',', '').replace('.', '').isdigit()
    if validate == 'phone':
        digits = re.sub(r'\D', '', v)
        return bool(_PHONE_RE.match(digits) or len(digits) >= 10)
    return len(v) >= 1


def _resume_after_state(cfg: BotSettings, sub: Subscriber, chat_id: int, resume: Any) -> None:
    if isinstance(resume, dict):
        _execute_node(cfg, sub, chat_id, resume)
    messenger_api.send_message(
        cfg.platform, chat_id, '',
        settings=cfg,
        reply_markup={'remove_keyboard': True},
    ) if False else None


def handle_faq_answer_callback(cfg: BotSettings, sub: Subscriber, node_id: str, chat_id: int) -> bool:
    state = sub.flow_state or {}
    faq_map = state.get('faq_answers') or {}
    answer = faq_map.get(node_id)
    if not answer:
        return False
    _send_text(cfg, chat_id, answer)
    return True


def handle_join_gate_recheck(
    cfg: BotSettings,
    sub: Subscriber,
    gate_id: str,
    chat_id: int,
) -> tuple[str, str]:
    state = sub.flow_state or {}
    channel = state.get('channel') or ''
    then = state.get('then')
    if _check_channel_member(cfg, sub, channel):
        _clear_flow_state(sub)
        if isinstance(then, dict):
            _execute_node(cfg, sub, chat_id, then)
        else:
            _send_text(cfg, chat_id, '✅ عضویت تأیید شد.')
        return 'join_gate_ok', 'بررسی مجدد'
    _send_text(cfg, chat_id, 'هنوز عضو کانال نشدی. لطفاً عضو شو و دوباره بررسی کن.')
    return 'join_gate_pending', 'بررسی مجدد'


def resume_flow(cfg: BotSettings, sub: Subscriber, msg: dict[str, Any], state: dict[str, Any]) -> bool:
    """پردازش ورودی کاربر در حالت انتظار جریان."""
    awaiting = _clip(state.get('awaiting'), 32)
    chat_id = sub.chat_id
    platform = cfg.platform

    if awaiting == 'order_lookup':
        query = (msg.get('text') or '').strip()
        if not query:
            return True
        order = None
        if query.isdigit():
            order = CatalogOrder.objects.filter(
                pk=int(query),
                workspace=cfg.workspace,
                platform=cfg.platform,
                subscriber=sub,
            ).first()
        if order is None:
            order = CatalogOrder.objects.filter(
                public_token=query,
                workspace=cfg.workspace,
                platform=cfg.platform,
                subscriber=sub,
            ).first()
        _clear_flow_state(sub)
        if not order:
            _send_text(cfg, chat_id, 'سفارشی با این شماره پیدا نشد.')
            return True
        if order.status == CatalogOrder.Status.PAID:
            status = _fulfillment_label(order.fulfillment_status or order.status)
        else:
            status = _fulfillment_label(order.status)
        track = f'\nکد رهگیری: {order.tracking_code}' if order.tracking_code else ''
        _send_text(cfg, chat_id, f'سفارش #{order.pk}\nوضعیت: {status}{track}')
        return True

    if awaiting == 'input':
        value = (msg.get('text') or '').strip()
        validate = _clip(state.get('validate'), 16) or 'text'
        save_key = _clip(state.get('save_key'), 64) or 'answer'
        if not _validate_input(value, validate):
            _send_text(cfg, chat_id, 'ورودی نامعتبره. دوباره بفرست.')
            return True
        _save_flow_answer(sub, save_key, value)
        resume = state.get('resume')
        _clear_flow_state(sub)
        if isinstance(resume, dict):
            _execute_node(cfg, sub, chat_id, resume)
        return True

    if awaiting == 'form':
        value = (msg.get('text') or '').strip()
        steps = state.get('steps') if isinstance(state.get('steps'), list) else []
        step_index = int(state.get('step_index') or 0)
        if step_index >= len(steps):
            _clear_flow_state(sub)
            return True
        step = steps[step_index]
        if not isinstance(step, dict):
            _clear_flow_state(sub)
            return True
        validate = _clip(step.get('validate'), 16) or 'text'
        save_key = _clip(step.get('save_key'), 64) or f'field_{step_index}'
        if not _validate_input(value, validate):
            _send_text(cfg, chat_id, 'ورودی نامعتبره. دوباره بفرست.')
            return True
        _save_flow_answer(sub, save_key, value)
        next_index = step_index + 1
        if next_index < len(steps):
            next_step = steps[next_index]
            _set_flow_state(sub, {
                'awaiting': 'form',
                'steps': steps,
                'step_index': next_index,
                'on_complete': state.get('on_complete'),
            })
            if isinstance(next_step, dict):
                _send_text(cfg, chat_id, _clip(next_step.get('prompt'), 500) or 'ادامه بده:')
            return True
        on_complete = state.get('on_complete') if isinstance(state.get('on_complete'), dict) else {}
        _clear_flow_state(sub)
        thank = _clip(on_complete.get('thank_you'), 500) or 'ثبت شد. ممنون!'
        assign_tag = _clip(on_complete.get('assign_tag'), 140)
        if assign_tag:
            _assign_tags(sub, [assign_tag], [])
        if on_complete.get('notify_admin'):
            catalog = CatalogSettings.objects.filter(
                workspace=cfg.workspace, platform=cfg.platform,
            ).first()
            if catalog and catalog.admin_notify_chat_id:
                summary_lines = ['📝 فرم جدید از ربات']
                for s in steps:
                    if not isinstance(s, dict):
                        continue
                    k = _clip(s.get('save_key'), 64)
                    if k:
                        val = html.escape(str((sub.menu_flow_answers or {}).get(k, '—')))
                        summary_lines.append(f'{html.escape(k)}: {val}')
                try:
                    messenger_api.send_message(
                        platform, catalog.admin_notify_chat_id,
                        '\n'.join(summary_lines)[:4000],
                        settings=cfg,
                    )
                except messenger_api.MessengerAPIError:
                    pass
        _send_text(cfg, chat_id, thank)
        return True

    if awaiting == 'request_contact':
        contact = msg.get('contact')
        if not contact:
            return False
        phone = (contact.get('phone_number') or '').strip()
        if phone:
            sub.phone_number = phone[:32]
            sub.is_registered = True
            sub.save(update_fields=['phone_number', 'is_registered', 'updated_at'])
        assign_tag = _clip(state.get('assign_tag'), 140)
        resume = state.get('resume')
        _clear_flow_state(sub)
        if assign_tag:
            _assign_tags(sub, [assign_tag], [])
        _remove_reply_keyboard(cfg, chat_id, cfg.registration_success_message or 'شماره ثبت شد.')
        if isinstance(resume, dict):
            _execute_node(cfg, sub, chat_id, resume)
        return True

    if awaiting == 'request_location':
        loc = msg.get('location')
        if not loc:
            return False
        save_key = _clip(state.get('save_key'), 64) or 'loc'
        _save_flow_answer(sub, save_key, {
            'lat': loc.get('latitude'),
            'lng': loc.get('longitude'),
        })
        resume = state.get('resume')
        _clear_flow_state(sub)
        _remove_reply_keyboard(cfg, chat_id, 'موقعیت ثبت شد.')
        if isinstance(resume, dict):
            _execute_node(cfg, sub, chat_id, resume)
        return True

    return False


def execute_interactive_action(
    cfg: BotSettings,
    sub: Subscriber,
    ref: _ButtonRef,
    chat_id: int,
    *,
    message_id: int | None = None,
    visited: set[str] | None = None,
) -> str:
    """اجرای اکشن دکمه — شامل انواع تعاملی جدید."""
    btn = ref.button
    action = btn.get('action')
    if not action or not isinstance(action, dict):
        send_default_text(cfg, chat_id)
        return 'default'

    atype = str(action.get('type', '')).lower()
    interactive_types = {
        'webapp', 'order_status', 'my_orders', 'invoice', 'location_card', 'contact_card',
        'input', 'form', 'request_contact', 'request_location',
        'condition', 'goto', 'join_gate', 'tag', 'faq', 'coupon', 'handoff',
    }
    return _execute_node(
        cfg, sub, chat_id, action,
        message_id=message_id, visited=visited,
    )
