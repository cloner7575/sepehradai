"""اعتبارسنجی و اعمال کد تخفیف."""

from __future__ import annotations

import copy
from typing import Any

from django.utils import timezone

from balebot.models import CatalogOrder, CatalogSettings, DiscountCode, Subscriber, Workspace


class DiscountError(ValueError):
    pass


def _subscriber_has_paid_orders(
    catalog: CatalogSettings,
    subscriber: Subscriber | None,
) -> bool:
    if not subscriber or not subscriber.pk:
        return False
    return CatalogOrder.objects.filter(
        workspace=catalog.workspace,
        platform=catalog.platform,
        subscriber=subscriber,
        status=CatalogOrder.Status.PAID,
    ).exists()


def validate_discount_code(
    catalog: CatalogSettings,
    code: str,
    *,
    subtotal: int,
    subscriber: Subscriber | None = None,
) -> DiscountCode:
    raw = (code or '').strip()
    if not raw:
        raise DiscountError('کد تخفیف را وارد کنید.')

    dc = DiscountCode.objects.filter(
        workspace=catalog.workspace,
        platform=catalog.platform,
        code__iexact=raw,
    ).first()
    if not dc or not dc.is_active:
        raise DiscountError('کد تخفیف نامعتبر است.')

    if dc.expires_at and dc.expires_at < timezone.now():
        raise DiscountError('کد تخفیف منقضی شده است.')

    if dc.max_uses is not None and dc.used_count >= dc.max_uses:
        raise DiscountError('سقف استفاده از این کد پر شده است.')

    subtotal = max(0, int(subtotal or 0))
    if subtotal < int(dc.min_order_amount or 0):
        raise DiscountError('مبلغ سفارش برای این کد کافی نیست.')

    if dc.first_purchase_only and _subscriber_has_paid_orders(catalog, subscriber):
        raise DiscountError('این کد فقط برای اولین خرید است.')

    return dc


def calculate_discount_amount(dc: DiscountCode, subtotal: int) -> int:
    subtotal = max(0, int(subtotal or 0))
    if dc.kind == DiscountCode.Kind.PERCENT:
        amount = subtotal * int(dc.value) // 100
    else:
        amount = int(dc.value)
    amount = max(0, amount)
    cap = dc.max_discount_amount
    if cap is not None and int(cap) > 0:
        amount = min(amount, int(cap))
    return min(subtotal, amount)


def apply_discount_to_order(dc: DiscountCode, subtotal: int) -> tuple[str, int]:
    amount = calculate_discount_amount(dc, subtotal)
    return dc.code, amount


def format_discount_editor_label(dc: DiscountCode) -> str:
    if dc.kind == DiscountCode.Kind.PERCENT:
        detail = f'{dc.value}%'
    else:
        detail = f'{dc.value:,} ریال'
    parts = [f'{dc.code} — {detail}']
    if dc.expires_at:
        parts.append('تا ' + timezone.localtime(dc.expires_at).strftime('%Y/%m/%d'))
    if dc.max_uses is not None:
        remaining = max(0, int(dc.max_uses) - int(dc.used_count or 0))
        parts.append(f'{remaining} بار')
    return ' · '.join(parts)


def discount_codes_for_editor(workspace: Workspace, platform: str) -> list[dict[str, Any]]:
    codes = DiscountCode.objects.filter(
        workspace=workspace,
        platform=platform,
        is_active=True,
    ).order_by('-created_at')
    return [
        {
            'id': dc.pk,
            'code': dc.code,
            'kind': dc.kind,
            'value': int(dc.value or 0),
            'label': format_discount_editor_label(dc),
        }
        for dc in codes
    ]


def get_discount_code_for_flow(
    workspace: Workspace,
    platform: str,
    *,
    discount_id: Any = None,
    code: str = '',
) -> DiscountCode | None:
    pk = None
    if discount_id is not None:
        try:
            pk = int(discount_id)
        except (TypeError, ValueError):
            pk = None
    if pk:
        dc = DiscountCode.objects.filter(
            workspace=workspace,
            platform=platform,
            pk=pk,
            is_active=True,
        ).first()
        if dc:
            return dc
    raw = (code or '').strip()
    if raw:
        return DiscountCode.objects.filter(
            workspace=workspace,
            platform=platform,
            code__iexact=raw,
            is_active=True,
        ).first()
    return None


def resolve_coupon_node(
    node: dict[str, Any],
    workspace: Workspace,
    platform: str,
) -> dict[str, Any] | None:
    if not isinstance(node, dict) or str(node.get('type', '')).lower() != 'coupon':
        return None
    dc = get_discount_code_for_flow(
        workspace,
        platform,
        discount_id=node.get('discount_id'),
        code=str(node.get('code', '') or ''),
    )
    if not dc:
        return None
    return {
        'type': 'coupon',
        'discount_id': dc.pk,
        'code': dc.code,
        'message': str(node.get('message', '') or '').strip()[:500],
        'once_per_user': bool(node.get('once_per_user')),
    }


def coupon_display_message(dc: DiscountCode | None, code: str, custom: str = '') -> str:
    custom = (custom or '').strip()
    if custom:
        return custom[:500]
    if dc:
        if dc.kind == DiscountCode.Kind.PERCENT:
            detail = f'{dc.value}% تخفیف'
        else:
            detail = f'{dc.value:,} ریال تخفیف'
        return f'کد {code} را موقع پرداخت وارد کن ({detail}).'
    if code:
        return f'کد تخفیف: {code}'
    return ''


def _resolve_button_coupon(btn: dict[str, Any], workspace: Workspace, platform: str) -> None:
    action = btn.get('action')
    if not isinstance(action, dict) or str(action.get('type', '')).lower() != 'coupon':
        return
    resolved = resolve_coupon_node(action, workspace, platform)
    btn['action'] = resolved


def _resolve_buttons_node(node: dict[str, Any], workspace: Workspace, platform: str) -> None:
    if str(node.get('type', '')).lower() != 'buttons':
        return
    for row in node.get('rows') or []:
        if not isinstance(row, list):
            continue
        for btn in row:
            if isinstance(btn, dict):
                _resolve_button_coupon(btn, workspace, platform)
                nested = btn.get('action')
                if isinstance(nested, dict) and str(nested.get('type', '')).lower() == 'buttons':
                    _resolve_buttons_node(nested, workspace, platform)


def _resolve_item_coupon(item: dict[str, Any], workspace: Workspace, platform: str) -> dict[str, Any] | None:
    if not isinstance(item, dict):
        return None
    itype = str(item.get('type', '')).lower()
    if itype == 'coupon':
        return resolve_coupon_node(item, workspace, platform)
    if itype == 'button':
        _resolve_button_coupon(item, workspace, platform)
        action = item.get('action')
        if isinstance(action, dict) and str(action.get('type', '')).lower() == 'buttons':
            _resolve_buttons_node(action, workspace, platform)
    elif itype == 'buttons':
        _resolve_buttons_node(item, workspace, platform)
    return item


def apply_coupon_resolution_to_flow(
    flow: dict[str, Any],
    workspace: Workspace,
    platform: str,
) -> dict[str, Any]:
    if not flow or not isinstance(flow, dict):
        return flow
    out = copy.deepcopy(flow)
    root = out.get('root')
    if not isinstance(root, dict):
        return out
    items = root.get('items')
    if not isinstance(items, list):
        return out
    resolved_items: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        itype = str(item.get('type', '')).lower()
        if itype == 'coupon':
            node = resolve_coupon_node(item, workspace, platform)
            if node:
                resolved_items.append(node)
            continue
        fixed = _resolve_item_coupon(item, workspace, platform)
        if fixed:
            resolved_items.append(fixed)
    root['items'] = resolved_items
    return out


def resolve_coupon_home_block(
    block: dict[str, Any],
    workspace: Workspace,
    platform: str,
) -> dict[str, Any] | None:
    if not isinstance(block, dict) or str(block.get('type', '')).lower() != 'coupon':
        return block
    dc = get_discount_code_for_flow(
        workspace,
        platform,
        discount_id=block.get('discount_id'),
        code=str(block.get('code', '') or ''),
    )
    if not dc:
        return None
    out = dict(block)
    out['discount_id'] = dc.pk
    out['code'] = dc.code
    if not str(out.get('title', '') or '').strip():
        out['title'] = 'کد تخفیف'
    return out


def apply_coupon_resolution_to_home_blocks(
    blocks: list[dict[str, Any]],
    workspace: Workspace,
    platform: str,
) -> list[dict[str, Any]]:
    resolved: list[dict[str, Any]] = []
    for block in blocks or []:
        if not isinstance(block, dict):
            continue
        if str(block.get('type', '')).lower() == 'coupon':
            node = resolve_coupon_home_block(block, workspace, platform)
            if node:
                resolved.append(node)
            continue
        resolved.append(block)
    return resolved
