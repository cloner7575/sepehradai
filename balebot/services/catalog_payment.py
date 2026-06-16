"""پرداخت و سفارش فروشگاه مینی‌اپ."""

from __future__ import annotations

import json
import logging
from typing import Any

from django.db import transaction

from balebot.models import (
    BotSettings,
    CatalogCart,
    CatalogItem,
    CatalogOrder,
    CatalogOrderLine,
    CatalogSettings,
    Subscriber,
)
from balebot.services import messenger_api, zarinpal
from balebot.services.checkout_form import format_customer_data_for_message
from balebot.services.webhook_logic import get_or_create_subscriber

logger = logging.getLogger(__name__)


def _line_items_from_cart(cart: CatalogCart) -> list[tuple[CatalogItem, int]]:
    rows: list[tuple[CatalogItem, int]] = []
    for entry in cart.items.select_related('catalog_item').all():
        item = entry.catalog_item
        if item.is_active and item.is_buyable():
            rows.append((item, entry.quantity))
    return rows


def _line_items_from_single(item: CatalogItem, qty: int = 1) -> list[tuple[CatalogItem, int]]:
    if not item.is_active or not item.is_buyable():
        return []
    return [(item, max(1, qty))]


def create_order_from_lines(
    *,
    workspace,
    platform: str,
    subscriber: Subscriber,
    lines: list[tuple[CatalogItem, int]],
    status: str = CatalogOrder.Status.PENDING,
    note: str = '',
    payment_method: str = '',
    customer_data: dict | None = None,
) -> CatalogOrder | None:
    if not lines:
        return None
    total = 0
    with transaction.atomic():
        order = CatalogOrder.objects.create(
            workspace=workspace,
            platform=platform,
            subscriber=subscriber,
            status=status,
            total_amount=0,
            note=note[:2000],
            payment_method=payment_method[:16],
            customer_data=customer_data or {},
        )
        for item, qty in lines:
            price = item.price or 0
            CatalogOrderLine.objects.create(
                order=order,
                item=item,
                title_snapshot=item.title[:200],
                price_snapshot=price,
                quantity=qty,
            )
            total += price * qty
        order.total_amount = total
        order.save(update_fields=['total_amount', 'updated_at'])
    return order


def create_checkout_order(
    *,
    catalog: CatalogSettings,
    subscriber: Subscriber,
    cart: CatalogCart | None = None,
    item: CatalogItem | None = None,
    quantity: int = 1,
    payment_method: str = '',
    customer_data: dict | None = None,
) -> CatalogOrder | None:
    if cart:
        lines = _line_items_from_cart(cart)
    elif item:
        lines = _line_items_from_single(item, quantity)
    else:
        return None
    status = CatalogOrder.Status.PENDING
    if payment_method == CatalogSettings.PaymentMethod.ADMIN_CART:
        status = CatalogOrder.Status.REQUEST
    return create_order_from_lines(
        workspace=catalog.workspace,
        platform=catalog.platform,
        subscriber=subscriber,
        lines=lines,
        status=status,
        payment_method=payment_method,
        customer_data=customer_data,
    )


def _format_order_lines(order: CatalogOrder) -> str:
    lines = []
    for ln in order.lines.all():
        lines.append(f'• {ln.title_snapshot} × {ln.quantity} — {ln.price_snapshot:,} ریال')
    return '\n'.join(lines) or '—'


def _format_price(amount: int) -> str:
    return f'{amount:,} ریال'


def submit_admin_cart_order(
    order: CatalogOrder,
    catalog: CatalogSettings,
    cfg: BotSettings,
    subscriber: Subscriber,
) -> None:
    if not catalog.admin_notify_chat_id:
        raise ValueError('چت‌آیدی ادمین برای دریافت سبد خرید تنظیم نشده است.')

    user_label = subscriber.first_name or subscriber.username or str(subscriber.messenger_user_id)
    phone = subscriber.phone_number or '—'
    customer_block = format_customer_data_for_message(catalog.checkout_form, order.customer_data or {})
    text = (
        f'🛒 سفارش جدید #{order.pk}\n'
        f'کاربر: {user_label}\n'
        f'شماره: {phone}\n'
        f'شناسه کاربر: {subscriber.messenger_user_id}\n'
    )
    if customer_block:
        text += f'\n📋 اطلاعات سفارش:\n{customer_block}\n'
    text += (
        f'\n{_format_order_lines(order)}\n\n'
        f'جمع کل: {_format_price(order.total_amount)}'
    )
    messenger_api.send_message(
        cfg.platform,
        catalog.admin_notify_chat_id,
        text,
        settings=cfg,
    )

    ack = (
        f'سبد خرید شما برای ادمین ارسال شد.\n'
        f'شماره پیگیری: #{order.pk}\n'
        f'مبلغ: {_format_price(order.total_amount)}'
    )
    messenger_api.send_message(cfg.platform, subscriber.chat_id, ack, settings=cfg)

    CatalogCart.objects.filter(
        workspace=catalog.workspace,
        platform=catalog.platform,
        subscriber=subscriber,
    ).delete()


def start_zarinpal_checkout(
    order: CatalogOrder,
    catalog: CatalogSettings,
    callback_url: str,
) -> str:
    description = f'سفارش #{order.pk}'
    authority = zarinpal.request_payment(
        merchant_id=catalog.zarinpal_merchant_id,
        amount_rials=order.total_amount,
        callback_url=callback_url,
        description=description,
        sandbox=catalog.zarinpal_sandbox,
        metadata={'order_id': order.pk},
    )
    order.zarinpal_authority = authority
    order.payment_method = CatalogSettings.PaymentMethod.ZARINPAL
    order.save(update_fields=['zarinpal_authority', 'payment_method', 'updated_at'])
    return zarinpal.build_payment_url(authority, sandbox=catalog.zarinpal_sandbox)


def verify_zarinpal_order(
    *,
    order: CatalogOrder,
    catalog: CatalogSettings,
    authority: str,
) -> CatalogOrder:
    if order.status == CatalogOrder.Status.PAID:
        return order
    if order.zarinpal_authority and order.zarinpal_authority != authority:
        raise zarinpal.ZarinpalError('شناسه پرداخت با سفارش مطابقت ندارد.')

    data = zarinpal.verify_payment(
        merchant_id=catalog.zarinpal_merchant_id,
        authority=authority,
        amount_rials=order.total_amount,
        sandbox=catalog.zarinpal_sandbox,
    )
    ref_id = str(data.get('ref_id') or data.get('refId') or '')
    order.status = CatalogOrder.Status.PAID
    order.payment_charge_id = ref_id[:256]
    order.zarinpal_authority = authority[:64]
    order.save(update_fields=['status', 'payment_charge_id', 'zarinpal_authority', 'updated_at'])

    if order.subscriber_id:
        CatalogCart.objects.filter(
            workspace=order.workspace,
            platform=order.platform,
            subscriber_id=order.subscriber_id,
        ).delete()
        try:
            cfg = BotSettings.get_for_platform(order.workspace, order.platform)
            sub = order.subscriber
            if sub:
                messenger_api.send_message(
                    order.platform,
                    sub.chat_id,
                    f'پرداخت شما با موفقیت انجام شد. سفارش #{order.pk}',
                    settings=cfg,
                )
        except messenger_api.MessengerAPIError:
            logger.exception('Failed to notify user after Zarinpal payment')
    return order


def handle_web_app_data(cfg: BotSettings, msg: dict[str, Any]) -> None:
    wad = msg.get('web_app_data') or {}
    raw = (wad.get('data') or '').strip()
    if not raw:
        return
    from_user = msg.get('from') or {}
    chat = msg.get('chat') or {}
    if not from_user:
        return
    sub = get_or_create_subscriber(cfg, from_user, chat)
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        data = {'note': raw[:500]}

    item_id = data.get('item_id')
    item = None
    if item_id:
        item = CatalogItem.objects.filter(
            pk=item_id,
            workspace=cfg.workspace,
            platform=cfg.platform,
            is_active=True,
        ).first()

    note = (data.get('note') or data.get('message') or 'درخواست از مینی‌اپ')[:2000]
    lines: list[tuple[CatalogItem, int]] = []
    if item and item.is_requestable():
        lines = [(item, int(data.get('quantity') or 1))]

    order = create_order_from_lines(
        workspace=cfg.workspace,
        platform=cfg.platform,
        subscriber=sub,
        lines=lines,
        status=CatalogOrder.Status.REQUEST,
        note=note,
    )
    if order:
        ack = 'درخواست شما ثبت شد. شماره پیگیری: #%s' % order.pk
        try:
            messenger_api.send_message(cfg.platform, sub.chat_id, ack, settings=cfg)
        except messenger_api.MessengerAPIError:
            pass


def get_or_create_cart(workspace, platform: str, subscriber: Subscriber) -> CatalogCart:
    cart, _ = CatalogCart.objects.get_or_create(
        workspace=workspace,
        platform=platform,
        subscriber=subscriber,
    )
    return cart
