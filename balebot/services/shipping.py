"""محاسبه هزینه ارسال فروشگاه."""

from __future__ import annotations

from balebot.models import CatalogSettings


def calculate_shipping(
    catalog: CatalogSettings,
    subtotal: int,
    *,
    province: str = '',
) -> int:
    subtotal = max(0, int(subtotal or 0))
    mode = catalog.shipping_mode or CatalogSettings.ShippingMode.FLAT

    threshold = catalog.free_shipping_threshold
    if threshold is not None and subtotal >= int(threshold):
        return 0

    if mode == CatalogSettings.ShippingMode.FREE:
        return 0

    if mode == CatalogSettings.ShippingMode.FLAT:
        return max(0, int(catalog.shipping_flat_cost or 0))

    if mode == CatalogSettings.ShippingMode.BY_PROVINCE:
        mapping = catalog.shipping_by_province or {}
        if not isinstance(mapping, dict):
            return max(0, int(catalog.shipping_flat_cost or 0))
        province = (province or '').strip()
        if province and province in mapping:
            return max(0, int(mapping[province] or 0))
        if 'default' in mapping:
            return max(0, int(mapping['default'] or 0))
        return max(0, int(catalog.shipping_flat_cost or 0))

    return 0
