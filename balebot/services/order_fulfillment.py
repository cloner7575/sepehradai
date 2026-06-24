"""اعلان خودکار تغییر وضعیت سفارش به مشتری."""

from __future__ import annotations

import logging

from balebot.models import BotSettings, CatalogOrder, CatalogSettings
from balebot.services import messenger_api

logger = logging.getLogger(__name__)


def _format_template(template: str, **kwargs) -> str:
    try:
        return (template or '').format(**kwargs)
    except (KeyError, ValueError):
        return template or ''


def notify_fulfillment_status_change(
    order: CatalogOrder,
    catalog: CatalogSettings,
    *,
    old_status: str,
    new_status: str,
) -> None:
    if old_status == new_status or not order.subscriber_id:
        return

    sub = order.subscriber
    if not sub:
        return

    message = ''
    if new_status == CatalogOrder.FulfillmentStatus.SHIPPED:
        template = (
            catalog.order_notify_shipped_template
            or 'سفارش شما ارسال شد 📦 کد رهگیری: {tracking_code}'
        )
        tracking = (order.tracking_code or '—').strip()
        message = _format_template(template, tracking_code=tracking, order_id=order.pk)
    elif new_status == CatalogOrder.FulfillmentStatus.DELIVERED:
        template = (
            catalog.order_notify_delivered_template
            or 'سفارش شما تحویل داده شد. ممنون از خریدتان 🌹'
        )
        message = _format_template(template, order_id=order.pk)
    elif new_status == CatalogOrder.FulfillmentStatus.PREPARING:
        message = f'سفارش #{order.pk} در حال آماده‌سازی است.'
    elif new_status == CatalogOrder.FulfillmentStatus.CANCELLED:
        message = f'سفارش #{order.pk} لغو شد. در صورت نیاز با پشتیبانی تماس بگیرید.'
    elif new_status == CatalogOrder.FulfillmentStatus.RETURNED:
        message = f'مرجوعی سفارش #{order.pk} ثبت شد.'

    if not message:
        return

    try:
        cfg = BotSettings.get_for_platform(order.workspace, order.platform)
        messenger_api.send_message(order.platform, sub.chat_id, message, settings=cfg)
    except messenger_api.MessengerAPIError:
        logger.exception('Failed to notify customer about order %s status', order.pk)
