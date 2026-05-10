"""ساختار صفحه‌کلید اینلاین کمپین (بخش‌ها + ردیف‌ها) و فشرده‌سازی برای API بله."""

from __future__ import annotations

from typing import Any

EMPTY_KEYBOARD: dict[str, Any] = {'sections': []}


def normalize_to_sections(raw: Any) -> dict[str, Any]:
    """برای نمایش در پنل و ذخیرهٔ یکنواخت."""
    if raw is None or raw == []:
        return {'sections': []}
    if isinstance(raw, dict) and 'sections' in raw:
        return raw
    if isinstance(raw, list):
        return {'sections': [{'title': '', 'rows': raw}]}
    return {'sections': []}


def flatten_rows(raw: Any) -> list[list[Any]]:
    """ترتیب ردیف‌ها برای ساخت callback_data و ارسال به بله."""
    raw = normalize_to_sections(raw)
    rows_out: list[list[Any]] = []
    for sec in raw.get('sections') or []:
        if not isinstance(sec, dict):
            continue
        for row in sec.get('rows') or []:
            if isinstance(row, list):
                rows_out.append(row)
    return rows_out


def keyboard_has_any_button(raw: Any) -> bool:
    for row in flatten_rows(raw):
        for btn in row:
            text = ''
            if isinstance(btn, str):
                text = btn.strip()
            elif isinstance(btn, dict):
                text = (btn.get('text') or '').strip()
            if text:
                return True
    return False


def _sanitize_rows(rows: Any) -> list[list[dict[str, str]]]:
    out: list[list[dict[str, str]]] = []
    if not isinstance(rows, list):
        return out
    for row in rows:
        if not isinstance(row, list):
            continue
        r: list[dict[str, str]] = []
        for btn in row:
            if isinstance(btn, str):
                t = btn.strip()[:64]
            elif isinstance(btn, dict):
                t = str(btn.get('text', '')).strip()[:64]
            else:
                continue
            if t:
                r.append({'text': t})
        if r:
            out.append(r)
    return out


_START_ACTIONS = frozenset({'none', 'url', 'reply', 'submenu'})
_MAX_START_DEPTH = 8


def _sanitize_start_button(btn: Any, depth: int) -> dict[str, Any] | None:
    if isinstance(btn, str):
        t = btn.strip()[:64]
        if not t:
            return None
        return {'text': t, 'action': 'none', 'url': '', 'reply_text': ''}
    if not isinstance(btn, dict):
        return None
    t = str(btn.get('text', '')).strip()[:64]
    if not t:
        return None
    act = str(btn.get('action', 'none') or 'none').strip().lower()
    if act not in _START_ACTIONS:
        act = 'none'
    url = str(btn.get('url', '') or '').strip()[:512]
    reply_text = str(btn.get('reply_text', '') or '').strip()[:3500]
    if act == 'url' and not url:
        act = 'none'
    if act == 'reply' and not reply_text:
        act = 'none'
    flow_key = str(btn.get('flow_key', '') or '').strip()[:64]

    out: dict[str, Any] = {
        'text': t,
        'action': act,
        'url': url,
        'reply_text': reply_text,
    }
    if flow_key:
        out['flow_key'] = flow_key

    if act == 'submenu':
        if depth >= _MAX_START_DEPTH:
            out['action'] = 'none'
            return out
        sm = btn.get('submenu')
        if isinstance(sm, dict):
            subs_secs = _sanitize_start_sections(sm.get('sections'), depth + 1)
            out['submenu'] = {'sections': subs_secs}
        else:
            out['action'] = 'none'
    return out


def _sanitize_start_rows(rows: Any, depth: int) -> list[list[dict[str, Any]]]:
    out: list[list[dict[str, Any]]] = []
    if not isinstance(rows, list):
        return out
    for row in rows:
        if not isinstance(row, list):
            continue
        r: list[dict[str, Any]] = []
        for btn in row:
            b = _sanitize_start_button(btn, depth)
            if b:
                r.append(b)
        if r:
            out.append(r)
    return out


def _sanitize_start_sections(sections: Any, depth: int) -> list[dict[str, Any]]:
    secs: list[dict[str, Any]] = []
    if not isinstance(sections, list):
        return secs
    for sec in sections:
        if not isinstance(sec, dict):
            continue
        title = str(sec.get('title', '')).strip()[:120]
        rows = _sanitize_start_rows(sec.get('rows', []), depth)
        if rows or title:
            secs.append({'title': title, 'rows': rows})
    return secs


def sanitize_start_keyboard_for_storage(data: Any) -> dict[str, Any]:
    """ذخیرهٔ صفحه‌کلید /start با فیلدهای اکشن و زیرمنو."""
    if data is None:
        return dict(EMPTY_KEYBOARD)
    if isinstance(data, list):
        return {'sections': [{'title': '', 'rows': _sanitize_start_rows(data, 0)}]}
    if isinstance(data, dict) and 'sections' in data:
        return {'sections': _sanitize_start_sections(data['sections'], 0)}
    return dict(EMPTY_KEYBOARD)


def sanitize_keyboard_for_storage(data: Any) -> dict[str, Any]:
    """ذخیرهٔ یکنواخت در JSON با ساختار sections."""
    if data is None:
        return dict(EMPTY_KEYBOARD)
    if isinstance(data, list):
        return {'sections': [{'title': '', 'rows': _sanitize_rows(data)}]}
    if isinstance(data, dict) and 'sections' in data:
        secs: list[dict[str, Any]] = []
        for sec in data['sections']:
            if not isinstance(sec, dict):
                continue
            title = str(sec.get('title', '')).strip()[:120]
            secs.append(
                {
                    'title': title,
                    'rows': _sanitize_rows(sec.get('rows', [])),
                },
            )
        return {'sections': secs}
    return dict(EMPTY_KEYBOARD)
