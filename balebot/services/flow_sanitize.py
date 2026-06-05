"""اعتبارسنجی و نرمال‌سازی JSON جریان /start (نسخه ۲)."""

from __future__ import annotations

import re
import uuid
from typing import Any

from balebot.models import FlowMedia

_MAX_DEPTH = 20
_SLUG_RE = re.compile(r'^[a-z0-9]+(?:-[a-z0-9]+)*$')
_NODE_ID_RE = re.compile(r'^n_[a-f0-9]{8}$')


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


def _sanitize_image_node(item: dict[str, Any]) -> dict[str, Any] | None:
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
    return {'type': 'image', 'media_id': media_id, 'caption': caption}


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
        media_id = str(action.get('media_id', '') or '').strip()
        if not media_id:
            return None
        try:
            uuid.UUID(media_id)
        except ValueError:
            return None
        if not FlowMedia.objects.filter(pk=media_id).exists():
            return None
        caption = str(action.get('caption', '') or '').strip()[:1024]
        return {'type': 'image', 'media_id': media_id, 'caption': caption}
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
    if atype == 'web_app':
        url = str(action.get('url', '') or '').strip()[:512]
        if not url:
            return None
        return {'type': 'web_app', 'url': url}
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
    label_slug = _slugify_label(str(btn.get('label_slug', '') or ''))
    if label_slug:
        out['label_slug'] = label_slug
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
        elif itype == 'image':
            sanitized = _sanitize_image_node(item)
        elif itype == 'buttons':
            sanitized = _sanitize_buttons_node(item, depth)
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
            out['label_slug'] = _slugify_label(fk) or _slugify_label(text)
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
