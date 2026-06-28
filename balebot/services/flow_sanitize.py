"""اعتبارسنجی و نرمال‌سازی JSON جریان /start (نسخه ۲)."""

from __future__ import annotations

import re
import uuid
from typing import Any

from balebot.models import FlowMedia

_MAX_DEPTH = 20
_SLUG_RE = re.compile(r'^[a-z0-9]+(?:-[a-z0-9]+)*$')
_NODE_ID_RE = re.compile(r'^n_[a-f0-9]{8}$')
_MEDIA_NODE_TYPES = frozenset({'image', 'video', 'voice', 'document'})
_SEQUENCE_ITEM_TYPES = frozenset({'text', 'image', 'video', 'voice', 'document'})
_INTERACTIVE_TYPES = frozenset({
    'webapp', 'order_status', 'my_orders', 'invoice', 'location_card', 'contact_card',
    'input', 'form', 'request_contact', 'request_location',
    'condition', 'goto', 'join_gate', 'tag', 'faq', 'coupon', 'handoff',
})


def _new_node_id() -> str:
    return f'n_{uuid.uuid4().hex[:8]}'


def _ensure_node_id(node_id: str | None) -> str:
    if node_id and _NODE_ID_RE.match(str(node_id).strip()):
        return str(node_id).strip()
    return _new_node_id()


def _slugify_label(raw: str) -> str:
    from django.utils.text import slugify

    s = (raw or '').strip()[:140]
    if not s:
        return ''
    out = slugify(s, allow_unicode=False)
    if out and _SLUG_RE.match(out):
        return out
    cleaned = re.sub(r'[^a-z0-9]+', '-', s.lower()).strip('-')
    return cleaned[:140] if cleaned else ''


def _sanitize_text_node(item: dict[str, Any]) -> dict[str, Any] | None:
    body = str(item.get('body', '') or '').strip()[:4096]
    if not body:
        return None
    return {'type': 'text', 'body': body}


def _sanitize_media_node(item: dict[str, Any], media_type: str) -> dict[str, Any] | None:
    if media_type not in _MEDIA_NODE_TYPES:
        return None
    media_id = str(item.get('media_id', '') or '').strip()
    if not media_id:
        return None
    try:
        uuid.UUID(media_id)
    except ValueError:
        return None
    if not FlowMedia.objects.filter(pk=media_id).exists():
        return None
    caption = str(item.get('caption', '') or '').strip()[:1024]
    return {'type': media_type, 'media_id': media_id, 'caption': caption}


def _sanitize_image_node(item: dict[str, Any]) -> dict[str, Any] | None:
    return _sanitize_media_node(item, 'image')


def _sanitize_sequence_items(items: Any, depth: int) -> list[dict[str, Any]]:
    if depth > _MAX_DEPTH or not isinstance(items, list):
        return []
    items_out: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        itype = str(item.get('type', '') or '').strip().lower()
        sanitized: dict[str, Any] | None = None
        if itype == 'text':
            sanitized = _sanitize_text_node(item)
        elif itype in _MEDIA_NODE_TYPES:
            sanitized = _sanitize_media_node(item, itype)
        elif itype in _INTERACTIVE_TYPES:
            sanitized = _sanitize_interactive_node(item, depth)
        if sanitized:
            items_out.append(sanitized)
    return items_out


def _sanitize_sequence_node(node: dict[str, Any], depth: int) -> dict[str, Any] | None:
    if depth > _MAX_DEPTH:
        return None
    items_out = _sanitize_sequence_items(node.get('items'), depth)
    if not items_out:
        return None
    return {'type': 'sequence', 'items': items_out}


def _sanitize_target(raw: Any) -> dict[str, str] | None:
    if not isinstance(raw, dict):
        return None
    kind = str(raw.get('kind', '') or '').strip().lower()[:16]
    value = str(raw.get('value', '') or '').strip()[:256]
    if kind not in ('home', 'category', 'item', 'tag', 'url') or not value:
        if kind == 'home':
            return {'kind': 'home', 'value': ''}
        return None
    return {'kind': kind, 'value': value}


def _sanitize_faq_items(raw: Any) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    if not isinstance(raw, list):
        return out
    for item in raw:
        if not isinstance(item, dict):
            continue
        q = str(item.get('q', '') or '').strip()[:200]
        a = str(item.get('a', '') or '').strip()[:2000]
        if q and a:
            out.append({'q': q, 'a': a})
    return out


def _sanitize_form_steps(raw: Any) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    if not isinstance(raw, list):
        return out
    for step in raw:
        if not isinstance(step, dict):
            continue
        prompt = str(step.get('prompt', '') or '').strip()[:500]
        save_key = str(step.get('save_key', '') or '').strip()[:64]
        validate = str(step.get('validate', '') or 'text').strip().lower()
        if validate not in ('text', 'number', 'phone'):
            validate = 'text'
        if prompt and save_key:
            out.append({'prompt': prompt, 'save_key': save_key, 'validate': validate})
    return out


def _sanitize_interactive_node(node: dict[str, Any], depth: int) -> dict[str, Any] | None:
    if depth > _MAX_DEPTH:
        return None
    ntype = str(node.get('type', '') or '').strip().lower()
    if ntype not in _INTERACTIVE_TYPES:
        return None

    if ntype == 'webapp':
        label = str(node.get('label', '') or '').strip()[:64] or 'ورود به فروشگاه'
        out: dict[str, Any] = {'type': 'webapp', 'label': label}
        target = _sanitize_target(node.get('target'))
        if target:
            out['target'] = target
        return out

    if ntype == 'order_status':
        return {'type': 'order_status', 'prompt': str(node.get('prompt', '') or '').strip()[:500] or 'شماره سفارشت رو بفرست:'}

    if ntype == 'my_orders':
        limit = int(node.get('limit') or 5)
        return {'type': 'my_orders', 'limit': max(1, min(limit, 20))}

    if ntype == 'invoice':
        try:
            amount = max(0, int(node.get('amount') or 0))
        except (TypeError, ValueError):
            amount = 0
        return {
            'type': 'invoice',
            'title': str(node.get('title', '') or '').strip()[:32] or 'پرداخت',
            'amount': amount,
            'description': str(node.get('description', '') or '').strip()[:255],
            'item_slug': str(node.get('item_slug', '') or '').strip()[:120],
        }

    if ntype == 'location_card':
        try:
            lat = float(node.get('lat'))
            lng = float(node.get('lng'))
        except (TypeError, ValueError):
            return None
        return {
            'type': 'location_card',
            'lat': lat,
            'lng': lng,
            'address': str(node.get('address', '') or '').strip()[:500],
            'hours': str(node.get('hours', '') or '').strip()[:200],
        }

    if ntype == 'contact_card':
        phone = str(node.get('phone', '') or '').strip()[:20]
        if not phone:
            return None
        return {
            'type': 'contact_card',
            'phone': phone,
            'name': str(node.get('name', '') or '').strip()[:64] or 'پشتیبانی',
        }

    if ntype == 'input':
        save_key = str(node.get('save_key', '') or '').strip()[:64]
        if not save_key:
            return None
        validate = str(node.get('validate', '') or 'text').strip().lower()
        if validate not in ('text', 'number', 'phone'):
            validate = 'text'
        out = {
            'type': 'input',
            'prompt': str(node.get('prompt', '') or '').strip()[:500],
            'save_key': save_key,
            'validate': validate,
        }
        nxt = _sanitize_action(node.get('next'), depth + 1)
        if nxt:
            out['next'] = nxt
        return out

    if ntype == 'form':
        steps = _sanitize_form_steps(node.get('steps'))
        if not steps:
            return None
        out = {'type': 'form', 'title': str(node.get('title', '') or '').strip()[:120], 'steps': steps}
        oc = node.get('on_complete')
        if isinstance(oc, dict):
            out['on_complete'] = {
                'notify_admin': bool(oc.get('notify_admin')),
                'thank_you': str(oc.get('thank_you', '') or '').strip()[:500],
                'assign_tag': _slugify_label(str(oc.get('assign_tag', '') or '')),
            }
        return out

    if ntype == 'request_contact':
        out = {
            'type': 'request_contact',
            'prompt': str(node.get('prompt', '') or '').strip()[:500],
        }
        tag = _slugify_label(str(node.get('assign_tag', '') or ''))
        if tag:
            out['assign_tag'] = tag
        resume = _sanitize_action(node.get('resume'), depth + 1)
        if resume:
            out['resume'] = resume
        return out

    if ntype == 'request_location':
        save_key = str(node.get('save_key', '') or '').strip()[:64] or 'loc'
        out = {
            'type': 'request_location',
            'prompt': str(node.get('prompt', '') or '').strip()[:500],
            'save_key': save_key,
        }
        resume = _sanitize_action(node.get('resume'), depth + 1)
        if resume:
            out['resume'] = resume
        return out

    if ntype == 'condition':
        cond = node.get('if')
        if not isinstance(cond, dict):
            return None
        kind = str(cond.get('kind', '') or '').strip().lower()
        if kind not in ('has_tag', 'answer_equals', 'is_registered'):
            return None
        cond_out: dict[str, Any] = {'kind': kind}
        if kind == 'has_tag':
            cond_out['value'] = str(cond.get('value', '') or '').strip()[:140]
        elif kind == 'answer_equals':
            cond_out['key'] = str(cond.get('key', '') or '').strip()[:64]
            cond_out['value'] = str(cond.get('value', '') or '').strip()[:500]
        then = _sanitize_action(node.get('then'), depth + 1)
        else_b = _sanitize_action(node.get('else'), depth + 1)
        if not then and not else_b:
            return None
        out = {'type': 'condition', 'if': cond_out}
        if then:
            out['then'] = then
        if else_b:
            out['else'] = else_b
        return out

    if ntype == 'goto':
        target_id = str(node.get('target_id', '') or '').strip()
        if not _NODE_ID_RE.match(target_id):
            return None
        return {'type': 'goto', 'target_id': target_id}

    if ntype == 'join_gate':
        channel = str(node.get('channel', '') or '').strip()[:120]
        if not channel:
            return None
        out = {
            'type': 'join_gate',
            'channel': channel,
            'prompt': str(node.get('prompt', '') or '').strip()[:500],
        }
        then = _sanitize_action(node.get('then'), depth + 1)
        if then:
            out['then'] = then
        return out

    if ntype == 'tag':
        add = [str(s).strip()[:140] for s in (node.get('add') or []) if str(s).strip()]
        remove = [str(s).strip()[:140] for s in (node.get('remove') or []) if str(s).strip()]
        return {'type': 'tag', 'add': add, 'remove': remove}

    if ntype == 'faq':
        items = _sanitize_faq_items(node.get('items'))
        if not items:
            return None
        return {'type': 'faq', 'title': str(node.get('title', '') or '').strip()[:120], 'items': items}

    if ntype == 'coupon':
        code = str(node.get('code', '') or '').strip()[:40]
        if not code:
            return None
        return {
            'type': 'coupon',
            'code': code,
            'message': str(node.get('message', '') or '').strip()[:500],
            'once_per_user': bool(node.get('once_per_user')),
        }

    if ntype == 'handoff':
        return {
            'type': 'handoff',
            'message': str(node.get('message', '') or '').strip()[:500],
        }

    return None


def _sanitize_action(action: Any, depth: int) -> dict[str, Any] | None:
    if depth > _MAX_DEPTH or not isinstance(action, dict):
        return None
    atype = str(action.get('type', '') or '').strip().lower()
    if atype == 'text':
        body = str(action.get('body', '') or '').strip()[:4096]
        if not body:
            return None
        return {'type': 'text', 'body': body}
    if atype == 'image':
        return _sanitize_media_node(action, 'image')
    if atype == 'sequence':
        return _sanitize_sequence_node(action, depth)
    if atype == 'buttons':
        inner = _sanitize_buttons_node({'type': 'buttons', 'rows': action.get('rows')}, depth + 1)
        if not inner:
            return None
        return inner
    if atype == 'url':
        url = str(action.get('url', '') or '').strip()[:512]
        if not url:
            return None
        return {'type': 'url', 'url': url}
    if atype in _INTERACTIVE_TYPES:
        return _sanitize_interactive_node(action, depth)
    return None


def _sanitize_button(btn: Any, depth: int) -> dict[str, Any] | None:
    if depth > _MAX_DEPTH or not isinstance(btn, dict):
        return None
    text = str(btn.get('text', '') or '').strip()[:64]
    action_raw = btn.get('action')
    action = _sanitize_action(action_raw, depth) if action_raw else None
    atype = ''
    if isinstance(action_raw, dict):
        atype = str(action_raw.get('type', '') or '').strip().lower()
    if atype == 'text':
        body = str((action_raw or {}).get('body', '') or '').strip()[:4096]
        if body:
            action = {'type': 'text', 'body': body}
        elif action and action.get('type') == 'text':
            action = None
    if not text and not action:
        return None
    if not text and action:
        if action.get('type') == 'text':
            text = str(action.get('body', ''))[:64] or '…'
        else:
            text = '…'
    out: dict[str, Any] = {
        'id': _ensure_node_id(btn.get('id')),
        'text': text,
    }
    category_slug = _slugify_label(str(btn.get('category_slug', '') or ''))
    if category_slug:
        out['category_slug'] = category_slug
    if action:
        out['action'] = action
    return out


def _sanitize_buttons_node(item: dict[str, Any], depth: int) -> dict[str, Any] | None:
    if depth > _MAX_DEPTH:
        return None
    rows_in = item.get('rows')
    if not isinstance(rows_in, list):
        return None
    rows_out: list[list[dict[str, Any]]] = []
    for row in rows_in:
        if not isinstance(row, list):
            continue
        r: list[dict[str, Any]] = []
        for btn in row:
            b = _sanitize_button(btn, depth)
            if b:
                r.append(b)
        if r:
            rows_out.append(r)
    if not rows_out:
        return None
    return {'type': 'buttons', 'rows': rows_out}


def _sanitize_sequence(node: Any, depth: int) -> dict[str, Any] | None:
    if depth > _MAX_DEPTH or not isinstance(node, dict):
        return None
    if str(node.get('type', '')).strip().lower() != 'sequence':
        return None
    items_in = node.get('items')
    if not isinstance(items_in, list):
        return None
    items_out: list[dict[str, Any]] = []
    for item in items_in:
        if not isinstance(item, dict):
            continue
        itype = str(item.get('type', '') or '').strip().lower()
        sanitized: dict[str, Any] | None = None
        if itype == 'text':
            sanitized = _sanitize_text_node(item)
        elif itype in _MEDIA_NODE_TYPES:
            sanitized = _sanitize_media_node(item, itype)
        elif itype == 'buttons':
            sanitized = _sanitize_buttons_node(item, depth)
        elif itype in _INTERACTIVE_TYPES:
            sanitized = _sanitize_interactive_node(item, depth)
        if sanitized:
            items_out.append(sanitized)
    return {'type': 'sequence', 'items': items_out}


def empty_start_flow() -> dict[str, Any]:
    return {'version': 2, 'root': {'type': 'sequence', 'items': []}}


def sanitize_start_flow(data: Any) -> dict[str, Any]:
    if not data or not isinstance(data, dict):
        return empty_start_flow()
    root = data.get('root')
    seq = _sanitize_sequence(root, 0)
    if not seq:
        return empty_start_flow()
    return {'version': 2, 'root': seq}


def migrate_inline_keyboard_to_flow(keyboard_data: Any) -> dict[str, Any]:
    """تبدیل تقریبی start_inline_keyboard قدیمی به start_flow."""
    from balebot.services.keyboard_layout import normalize_to_sections

    norm = normalize_to_sections(keyboard_data)
    items: list[dict[str, Any]] = []

    def convert_btn(btn: dict[str, Any], depth: int) -> dict[str, Any] | None:
        if depth > _MAX_DEPTH:
            return None
        text = str(btn.get('text', '') or '').strip()[:64]
        if not text:
            return None
        act = str(btn.get('action', 'none') or 'none').strip().lower()
        out: dict[str, Any] = {'id': _new_node_id(), 'text': text}
        fk = str(btn.get('flow_key', '') or '').strip()
        if fk:
            out['category_slug'] = _slugify_label(fk) or _slugify_label(text)
        if act == 'url':
            url = str(btn.get('url', '') or '').strip()
            if url:
                out['action'] = {'type': 'url', 'url': url[:512]}
        elif act == 'reply':
            body = str(btn.get('reply_text', '') or '').strip()
            if body:
                out['action'] = {'type': 'text', 'body': body[:4096]}
                out['text'] = body[:64]
        elif act == 'submenu':
            sm = btn.get('submenu') or {}
            rows: list[list[dict[str, Any]]] = []
            for row in sm.get('sections', [{}])[0].get('rows', []) if isinstance(sm, dict) else []:
                if not isinstance(row, list):
                    continue
                r = []
                for b in row:
                    if isinstance(b, dict):
                        cb = convert_btn(b, depth + 1)
                        if cb:
                            r.append(cb)
                if r:
                    rows.append(r)
            for sec in (sm.get('sections') or [])[1:] if isinstance(sm, dict) else []:
                for row in sec.get('rows') or []:
                    if not isinstance(row, list):
                        continue
                    r = []
                    for b in row:
                        if isinstance(b, dict):
                            cb = convert_btn(b, depth + 1)
                            if cb:
                                r.append(cb)
                    if r:
                        rows.append(r)
            if rows:
                out['action'] = {'type': 'buttons', 'rows': rows}
        return out

    for sec in norm.get('sections') or []:
        if not isinstance(sec, dict):
            continue
        for row in sec.get('rows') or []:
            if not isinstance(row, list):
                continue
            buttons = []
            for btn in row:
                if isinstance(btn, dict):
                    cb = convert_btn(btn, 0)
                    if cb:
                        buttons.append(cb)
            if buttons:
                items.append({'type': 'buttons', 'rows': [buttons]})

    if not items:
        return empty_start_flow()
    return {'version': 2, 'root': {'type': 'sequence', 'items': items}}
