"""به‌روزرسانی فلوی /start الگوها با نودهای تعاملی جدید."""

from __future__ import annotations

import copy
from typing import Any

from balebot.data.home_blocks_presets import _INDUSTRY_COPY, _SLUG_INDUSTRY_GROUP


def _industry_group(slug: str, industry: str) -> str:
    group = _SLUG_INDUSTRY_GROUP.get(slug) or industry or 'general'
    return group if group in _INDUSTRY_COPY else 'general'


def _faq_items(slug: str, industry: str) -> list[dict[str, str]]:
    copy_cfg = _INDUSTRY_COPY[_industry_group(slug, industry)]
    return list(copy_cfg.get('faq') or [])[:6]


def _walk_button(btn: dict[str, Any], state: dict[str, bool], marketing: dict[str, Any] | None) -> None:
    if not isinstance(btn, dict):
        return
    welcome = (marketing or {}).get('welcome_discount') or {}
    welcome_code = (welcome.get('code') or '').strip().upper()
    label_slug = (btn.get('label_slug') or '').strip().lower()
    action = btn.get('action')
    if not isinstance(action, dict):
        return
    atype = (action.get('type') or '').strip().lower()

    if atype == 'webapp':
        state['has_webapp'] = True
    elif atype == 'url' and (
        label_slug == 'shop'
        or '{shop_url}' in str(action.get('url') or '')
    ):
        label = (btn.get('label') or btn.get('text') or '🛍 ورود به فروشگاه').strip()
        btn['action'] = {'type': 'webapp', 'label': label[:64]}
        state['has_webapp'] = True

    if atype == 'order_status' or label_slug == 'order_status':
        state['has_order_status'] = True
    if atype == 'my_orders' or label_slug == 'my_orders':
        state['has_my_orders'] = True
    if atype == 'faq' or label_slug == 'faq':
        state['has_faq'] = True
    if atype == 'handoff' or label_slug == 'support':
        state['has_handoff'] = True

    if label_slug == 'offer' and welcome_code and atype == 'text':
        btn['action'] = {
            'type': 'coupon',
            'code': welcome_code[:40],
            'message': f'کد {welcome_code} را موقع پرداخت وارد کن.',
        }

    if label_slug == 'support' and atype == 'text':
        btn['action'] = {
            'type': 'handoff',
            'message': 'سوالت را همینجا بنویس؛ پشتیبانی به‌زودی پاسخ می‌دهد.',
        }
        state['has_handoff'] = True


def _walk_buttons(node: dict[str, Any], state: dict[str, bool], marketing: dict[str, Any] | None) -> None:
    if node.get('type') != 'buttons':
        return
    for row in node.get('rows') or []:
        if not isinstance(row, list):
            continue
        for btn in row:
            _walk_button(btn, state, marketing)


def _walk_item(item: dict[str, Any], state: dict[str, bool], marketing: dict[str, Any] | None) -> None:
    if not isinstance(item, dict):
        return
    itype = (item.get('type') or '').strip().lower()
    if itype == 'buttons':
        _walk_buttons(item, state, marketing)
    elif itype == 'button':
        _walk_button(item, state, marketing)


def _btn_to_item(btn: dict[str, Any], *, row: int | None = None) -> dict[str, Any]:
    out: dict[str, Any] = {
        'type': 'button',
        'id': (btn.get('id') or f"n_{(btn.get('text') or 'btn')[:8]}").strip(),
        'text': (btn.get('text') or btn.get('label') or '…').strip()[:64],
    }
    if btn.get('category_slug'):
        out['category_slug'] = btn['category_slug']
    action = btn.get('action')
    if isinstance(action, dict):
        out['action'] = copy.deepcopy(action)
    if row is not None:
        out['row'] = row
    elif btn.get('row') is not None:
        out['row'] = int(btn['row'])
    return out


def flatten_buttons_to_items(flow: dict[str, Any]) -> dict[str, Any]:
    """همه دکمه‌ها را به آیتم‌های مستقل type=button تبدیل می‌کند."""
    out = copy.deepcopy(flow or {})
    root = out.get('root')
    if not isinstance(root, dict) or root.get('type') != 'sequence':
        return out
    items_in = root.get('items')
    if not isinstance(items_in, list):
        return out

    items_out: list[dict[str, Any]] = []
    for item in items_in:
        if not isinstance(item, dict):
            continue
        itype = (item.get('type') or '').strip().lower()
        if itype == 'buttons':
            for row_idx, row in enumerate(item.get('rows') or []):
                if not isinstance(row, list):
                    continue
                for btn in row:
                    if isinstance(btn, dict):
                        items_out.append(_btn_to_item(btn, row=row_idx))
        elif itype == 'button':
            items_out.append(_btn_to_item(item))
        else:
            items_out.append(copy.deepcopy(item))

    root['items'] = items_out
    out['version'] = 2
    return out


def split_buttons_blocks(flow: dict[str, Any]) -> dict[str, Any]:
    """سازگاری با نام قبلی — همه دکمه‌ها مستقل می‌شوند."""
    return flatten_buttons_to_items(flow)


def upgrade_start_flow(
    start_flow: dict[str, Any],
    *,
    slug: str,
    industry: str,
    marketing: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """دکمهٔ فروشگاه → webapp، پشتیبانی → handoff، و دکمه‌های پیگیری/FAQ در صورت نبود."""
    flow = flatten_buttons_to_items(copy.deepcopy(start_flow or {}))
    root = flow.get('root')
    if not isinstance(root, dict) or root.get('type') != 'sequence':
        return flow

    items = root.get('items')
    if not isinstance(items, list):
        return flow

    state = {
        'has_webapp': False,
        'has_order_status': False,
        'has_my_orders': False,
        'has_faq': False,
        'has_handoff': False,
    }
    for item in items:
        _walk_item(item, state, marketing)

    prefix = (slug or 'tpl')[:8].replace('-', '')

    insert_at = len(items)
    for idx, item in enumerate(items):
        if isinstance(item, dict) and (item.get('type') or '').strip().lower() == 'button':
            insert_at = idx + 1

    max_row = -1
    for item in items:
        if not isinstance(item, dict):
            continue
        if (item.get('type') or '').strip().lower() != 'button':
            continue
        row_val = item.get('row')
        if row_val is not None:
            max_row = max(max_row, int(row_val))

    tracking_row = max_row + 1
    faq_row = max_row + 2

    extra: list[dict[str, Any]] = []
    if not state['has_order_status']:
        extra.append({
            'type': 'button',
            'id': f'n_{prefix}_ord',
            'text': '📦 پیگیری سفارش',
            'row': tracking_row,
            'action': {'type': 'order_status'},
        })
    if not state['has_my_orders']:
        extra.append({
            'type': 'button',
            'id': f'n_{prefix}_myo',
            'text': '🧾 سفارش‌های من',
            'row': tracking_row,
            'action': {'type': 'my_orders', 'limit': 5},
        })

    if not state['has_faq']:
        faq_items = _faq_items(slug, industry)
        if faq_items:
            extra.append({
                'type': 'button',
                'id': f'n_{prefix}_faq',
                'text': '❓ سوالات متداول',
                'row': faq_row,
                'action': {
                    'type': 'faq',
                    'title': 'سوالات متداول',
                    'items': faq_items,
                },
            })

    for offset, btn in enumerate(extra):
        items.insert(insert_at + offset, btn)

    flow['version'] = 2
    return flow
