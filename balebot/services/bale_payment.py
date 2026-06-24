"""پرداخت درون‌چتی بله با sendInvoice."""

from __future__ import annotations

import logging

from balebot.models import BotSettings, CatalogOrder, CatalogSettings, Platform
from balebot.services import messenger_api
from balebot.services.catalog_media import media_relative_path
from balebot.services.public_url import resolve_public_base_url

logger = logging.getLogger(__name__)


def _normalize_card_number(card: str) -> str:
    return ''.join(ch for ch in (card or '') if ch.isdigit())


def _line_image_url(order: CatalogOrder, catalog: CatalogSettings, cfg: BotSettings) -> str | None:
    line = order.lines.select_related('item').prefetch_related('item__media').first()
    if not line or not line.item_id:
        return None
    item = line.item
    if not item:
        return None
    base = resolve_public_base_url(cfg).rstrip('/')
    if not base:
        return None
    if item.cover:
        rel = media_relative_path(item.cover.url)
        if rel:
            return f'{base}/api/shop/{catalog.public_id}/media/{rel}'
    media = item.first_image()
    if media and media.file:
        rel = media_relative_path(media.file.url)
        if rel:
            return f'{base}/api/shop/{catalog.public_id}/media/{rel}'
    return None


def build_invoice_prices(order: CatalogOrder) -> list[dict[str, int | str]]:
    prices: list[dict[str, int | str]] = []
    for line in order.lines.all():
        prices.append({
            'label': line.title_snapshot[:128],
            'amount': int(line.price_snapshot * line.quantity),
        })
    shipping = getattr(order, 'shipping_cost', 0) or 0
    if shipping > 0:
        prices.append({'label': 'هزینه ارسال', 'amount': int(shipping)})
    discount = getattr(order, 'discount_amount', 0) or 0
    if discount > 0:
        prices.append({'label': 'تخفیف', 'amount': -int(discount)})
    return prices


def send_bale_invoice(
    order: CatalogOrder,
    catalog: CatalogSettings,
    cfg: BotSettings,
) -> dict:
    """
    سفارش pending را با sendInvoice به چت مشتری می‌فرستد.
    provider_token در بله همان شماره کارت فروشنده است.
    """
    if catalog.platform != Platform.BALE:
        raise ValueError('پرداخت بله فقط برای پلتفرم بله پشتیبانی می‌شود.')
    if not catalog.payment_bale_ready():
        raise ValueError('پرداخت بله در تنظیمات فعال یا کامل نیست.')

    sub = order.subscriber
    if not sub:
        raise ValueError('مشترک سفارش یافت نشد.')

    card = _normalize_card_number(catalog.bale_payment_card_number)
    prices = build_invoice_prices(order)
    if not prices:
        raise ValueError('سفارش بدون ردیف قیمت است.')

    photo_url = _line_image_url(order, catalog, cfg)
    holder = (catalog.bale_payment_card_holder or '').strip()
    title = (catalog.hero_title or 'سفارش شما')[:32]
    desc = f'سفارش #{order.pk}'
    if holder:
        desc = f'{desc} — {holder}'
    desc = desc[:255]

    return messenger_api.send_invoice(
        cfg.platform,
        sub.chat_id,
        title=title,
        description=desc,
        payload=f'order:{order.public_token}',
        provider_token=card,
        prices=prices,
        settings=cfg,
        photo_url=photo_url,
    )


def start_bale_checkout(
    order: CatalogOrder,
    catalog: CatalogSettings,
    cfg: BotSettings,
) -> None:
    """ارسال صورت‌حساب و ثبت روش پرداخت روی سفارش."""
    send_bale_invoice(order, catalog, cfg)
    order.payment_method = CatalogSettings.PaymentMethod.BALE
    order.save(update_fields=['payment_method', 'updated_at'])
