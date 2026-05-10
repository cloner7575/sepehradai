"""اینلاین کیبورد /start، مسیرهای چندسطحی callback و زیرمنو."""

from __future__ import annotations

import re
from typing import Any

from balebot.models import BotSettings
from balebot.services.keyboard_layout import normalize_to_sections

_BOT_NAV = re.compile(r'^b((?:\d+:\d+:\d+)(?:\|\d+:\d+:\d+)*)$')
_BOT_LEGACY = re.compile(r'^b(\d+)_(\d+)_(\d+)$')
_MAX_CB_LEN = 64


def parse_nav_callback(data: str) -> list[tuple[int, int, int]] | None:
    """مسیر کلیک مثل b0:0:0|1:2:3"""
    m = _BOT_NAV.match((data or '').strip())
    if not m:
        return None
    inner = m.group(1)
    if not inner:
        return []
    out: list[tuple[int, int, int]] = []
    try:
        for part in inner.split('|'):
            bits = part.split(':')
            if len(bits) != 3:
                return None
            a, b, c = bits
            out.append((int(a), int(b), int(c)))
    except ValueError:
        return None
    return out


def parse_nav_callback_legacy(data: str) -> list[tuple[int, int, int]] | None:
    m = _BOT_LEGACY.match((data or '').strip())
    if not m:
        return None
    return [(int(m.group(1)), int(m.group(2)), int(m.group(3)))]


def parse_start_nav_segments(data: str) -> list[tuple[int, int, int]] | None:
    """مسیر دکمهٔ استارت؛ فرمت جدید b… یا قدیمی bSi_Ri_Ci."""
    p = parse_nav_callback(data)
    if p is not None:
        return p
    return parse_nav_callback_legacy(data)


def parse_back_callback(data: str) -> list[tuple[int, int, int]] | None:
    """بازگشت: bb0:0:0|1:2 → مسیر منوی والد"""
    s = (data or '').strip()
    if not s.startswith('bb'):
        return None
    inner = s[2:].strip()
    if not inner:
        return None
    out: list[tuple[int, int, int]] = []
    try:
        for part in inner.split('|'):
            bits = part.split(':')
            if len(bits) != 3:
                return None
            a, b, c = bits
            out.append((int(a), int(b), int(c)))
    except ValueError:
        return None
    return out


def encode_nav_path(segments: list[tuple[int, int, int]]) -> str:
    body = '|'.join(f'{a}:{b}:{c}' for a, b, c in segments)
    return 'b' + body


def encode_back_path(parent_segments: list[tuple[int, int, int]]) -> str:
    if not parent_segments:
        return 'bz'
    body = '|'.join(f'{a}:{b}:{c}' for a, b, c in parent_segments)
    return 'bb' + body


def _get_button_at_sections(
    sections: list[Any],
    si: int,
    ri: int,
    ci: int,
) -> dict[str, Any] | None:
    if si < 0 or si >= len(sections):
        return None
    sec = sections[si]
    if not isinstance(sec, dict):
        return None
    rows = sec.get('rows') or []
    if ri < 0 or ri >= len(rows):
        return None
    row = rows[ri]
    if not isinstance(row, list) or ci < 0 or ci >= len(row):
        return None
    b = row[ci]
    return b if isinstance(b, dict) else None


def get_sections_root(settings_obj: BotSettings) -> list[Any]:
    raw = normalize_to_sections(settings_obj.start_inline_keyboard)
    return list(raw.get('sections') or [])


def get_sections_for_view(
    settings_obj: BotSettings,
    view_path: list[tuple[int, int, int]],
) -> list[Any]:
    """منویی که باید در این لایه نشان داده شود (ریشه یا زیرمنوی تو در تو)."""
    secs = get_sections_root(settings_obj)
    if not view_path:
        return secs
    for triple in view_path:
        btn = _get_button_at_sections(secs, *triple)
        if not btn:
            return []
        sm = btn.get('submenu') or {}
        secs = list(sm.get('sections') or [])
    return secs


def resolve_button_by_path(
    settings_obj: BotSettings,
    segments: list[tuple[int, int, int]],
) -> dict[str, Any] | None:
    """دکمهٔ انتهای مسیر (درخت ریشه یا زیرمنو)."""
    if not segments:
        return None
    secs = get_sections_root(settings_obj)
    btn: dict[str, Any] | None = None
    for i, triple in enumerate(segments):
        btn = _get_button_at_sections(secs, *triple)
        if not btn:
            return None
        if i < len(segments) - 1:
            sm = btn.get('submenu') or {}
            secs = list(sm.get('sections') or [])
    return btn


def build_markup_for_sections(
    sections: list[Any],
    path_prefix: list[tuple[int, int, int]],
) -> dict[str, Any] | None:
    """ساخت inline_keyboard برای یک لایه؛ callback_data = مسیر کامل تا این دکمه."""
    rows_api: list[list[dict[str, str]]] = []
    for si, sec in enumerate(sections or []):
        if not isinstance(sec, dict):
            continue
        for ri, row in enumerate(sec.get('rows') or []):
            if not isinstance(row, list):
                continue
            out_row: list[dict[str, str]] = []
            for ci, btn in enumerate(row):
                if not isinstance(btn, dict):
                    continue
                text = (btn.get('text') or '').strip()[:64]
                if not text:
                    continue
                action = (btn.get('action') or 'none').strip().lower()
                if action == 'url':
                    url = (btn.get('url') or '').strip()
                    if url:
                        out_row.append({'text': text, 'url': url[:512]})
                    continue
                seg_path = path_prefix + [(si, ri, ci)]
                cid = encode_nav_path(seg_path)
                if len(cid) > _MAX_CB_LEN:
                    continue
                out_row.append({'text': text, 'callback_data': cid[:_MAX_CB_LEN]})
            if out_row:
                rows_api.append(out_row)
    if not rows_api:
        return None
    return {'inline_keyboard': rows_api}


def build_view_markup(
    settings_obj: BotSettings,
    view_path: list[tuple[int, int, int]],
) -> dict[str, Any] | None:
    """کیبورد یک لایه + ردیف بازگشت در صورت نیاز."""
    secs = get_sections_for_view(settings_obj, view_path)
    mk = build_markup_for_sections(secs, view_path)
    rows: list[list[dict[str, str]]] = []
    if mk:
        rows = list(mk.get('inline_keyboard') or [])
    if view_path:
        bk = encode_back_path(view_path[:-1])
        if len(bk) <= _MAX_CB_LEN:
            rows.insert(0, [{'text': '« بازگشت', 'callback_data': bk[:_MAX_CB_LEN]}])
    if not rows:
        return None
    return {'inline_keyboard': rows}


def build_start_inline_markup(settings_obj: BotSettings) -> dict[str, Any] | None:
    """اولین پیام /start — فقط ریشه، بدون ردیف بازگشت."""
    secs = get_sections_root(settings_obj)
    return build_markup_for_sections(secs, [])
