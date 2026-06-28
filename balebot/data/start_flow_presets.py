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


def _walk_buttons(node: dict[str, Any], state: dict[str, bool], marketing: dict[str, Any] | None) -> None:
    if node.get('type') != 'buttons':
        return
    welcome = (marketing or {}).get('welcome_discount') or {}
    welcome_code = (welcome.get('code') or '').strip().upper()
    for row in node.get('rows') or []:
        if not isinstance(row, list):
            continue
        for btn in row:
            if not isinstance(btn, dict):
                continue
            label_slug = (btn.get('label_slug') or '').strip().lower()
            action = btn.get('action')
            if not isinstance(action, dict):
                continue
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


def upgrade_start_flow(
    start_flow: dict[str, Any],
    *,
    slug: str,
    industry: str,
    marketing: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """دکمهٔ فروشگاه → webapp، پشتیبانی → handoff، و دکمه‌های پیگیری/FAQ در صورت نبود."""
    flow = copy.deepcopy(start_flow or {})
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
        if isinstance(item, dict):
            _walk_buttons(item, state, marketing)

    buttons_node: dict[str, Any] | None = None
    for item in items:
        if isinstance(item, dict) and item.get('type') == 'buttons':
            buttons_node = item
            break

    if buttons_node is None:
        buttons_node = {'type': 'buttons', 'rows': []}
        items.append(buttons_node)

    rows = buttons_node.setdefault('rows', [])
    prefix = (slug or 'tpl')[:8].replace('-', '')

    extra_row: list[dict[str, Any]] = []
    if not state['has_order_status']:
        extra_row.append({
            'id': f'n_{prefix}_ord',
            'label': '📦 پیگیری سفارش',
            'text': '📦 پیگیری سفارش',
            'action': {'type': 'order_status'},
        })
    if not state['has_my_orders']:
        extra_row.append({
            'id': f'n_{prefix}_myo',
            'label': '🧾 سفارش‌های من',
            'text': '🧾 سفارش‌های من',
            'action': {'type': 'my_orders', 'limit': 5},
        })
    if extra_row:
        rows.append(extra_row)

    if not state['has_faq']:
        faq_items = _faq_items(slug, industry)
        if faq_items:
            rows.append([{
                'id': f'n_{prefix}_faq',
                'label': '❓ سوالات متداول',
                'text': '❓ سوالات متداول',
                'action': {
                    'type': 'faq',
                    'title': 'سوالات متداول',
                    'items': faq_items,
                },
            }])

    flow['version'] = 2
    return flow
