"""خلاصهٔ جریان /start برای پیش‌نمایش داشبورد."""

from __future__ import annotations

from typing import Any

from balebot.services.flow_sanitize import sanitize_start_flow

_MEDIA_LABELS = {
    'image': 'عکس',
    'video': 'ویدیو',
    'voice': 'صدا',
    'document': 'فایل',
}


def _action_hint(action: dict[str, Any] | None) -> str:
    if not action or not isinstance(action, dict):
        return ''
    atype = str(action.get('type', '') or '').strip().lower()
    if atype == 'text':
        body = str(action.get('body', '') or '').strip()
        return body[:48] + ('…' if len(body) > 48 else '') if body else 'پاسخ متنی'
    if atype == 'url':
        return 'باز کردن لینک'
    if atype == 'sequence':
        count = len(action.get('items') or [])
        return f'ارسال {count} پیام' if count else 'چند رسانه'
    if atype == 'buttons':
        count = sum(len(row or []) for row in (action.get('rows') or []))
        return f'منوی {count} دکمه‌ای' if count else 'زیرمنو'
    if atype in _MEDIA_LABELS:
        return _MEDIA_LABELS[atype]
    return ''


def _button_preview(btn: dict[str, Any]) -> dict[str, str]:
    text = str(btn.get('text', '') or '').strip() or '…'
    return {
        'text': text[:64],
        'hint': _action_hint(btn.get('action')),
    }


def _buttons_preview(node: dict[str, Any]) -> dict[str, Any]:
    rows_out: list[list[dict[str, str]]] = []
    for row in node.get('rows') or []:
        if not isinstance(row, list):
            continue
        row_out = [_button_preview(btn) for btn in row if isinstance(btn, dict)]
        if row_out:
            rows_out.append(row_out)
    return {'type': 'buttons', 'rows': rows_out}


def _sequence_steps(node: dict[str, Any], *, depth: int = 0, limit: int = 14) -> list[dict[str, Any]]:
    if depth > 3 or not isinstance(node, dict):
        return []
    if str(node.get('type', '')).lower() != 'sequence':
        return []
    steps: list[dict[str, Any]] = []
    for item in node.get('items') or []:
        if len(steps) >= limit or not isinstance(item, dict):
            break
        itype = str(item.get('type', '') or '').strip().lower()
        if itype == 'text':
            body = str(item.get('body', '') or '').strip()
            if body:
                steps.append({'type': 'text', 'body': body[:500]})
        elif itype in _MEDIA_LABELS:
            steps.append({
                'type': 'media',
                'media_type': itype,
                'label': _MEDIA_LABELS[itype],
                'caption': str(item.get('caption', '') or '').strip()[:120],
            })
        elif itype == 'buttons':
            preview = _buttons_preview(item)
            if preview['rows']:
                steps.append(preview)
    return steps


def summarize_start_flow(raw: Any) -> dict[str, Any]:
    flow = sanitize_start_flow(raw)
    root = flow.get('root') or {}
    steps = _sequence_steps(root)
    button_count = sum(
        len(row)
        for step in steps
        if step.get('type') == 'buttons'
        for row in (step.get('rows') or [])
    )
    return {
        'has_content': bool(steps),
        'step_count': len(steps),
        'button_count': button_count,
        'steps': steps,
    }
