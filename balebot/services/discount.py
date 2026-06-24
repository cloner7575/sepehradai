"""اعتبارسنجی و اعمال کد تخفیف."""

from __future__ import annotations

from django.utils import timezone

from balebot.models import CatalogSettings, DiscountCode


class DiscountError(ValueError):
    pass


def validate_discount_code(
    catalog: CatalogSettings,
    code: str,
    *,
    subtotal: int,
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

    return dc


def calculate_discount_amount(dc: DiscountCode, subtotal: int) -> int:
    subtotal = max(0, int(subtotal or 0))
    if dc.kind == DiscountCode.Kind.PERCENT:
        amount = subtotal * int(dc.value) // 100
    else:
        amount = int(dc.value)
    return min(subtotal, max(0, amount))


def apply_discount_to_order(dc: DiscountCode, subtotal: int) -> tuple[str, int]:
    amount = calculate_discount_amount(dc, subtotal)
    return dc.code, amount
