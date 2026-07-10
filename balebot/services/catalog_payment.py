"""پرداخت و سفارش فروشگاه مینی‌اپ."""

from __future__ import annotations

import json
import logging
from typing import Any

from django.db import transaction
from django.db.models import F

from balebot.models import (
    BotSettings,
    CatalogCart,
    CatalogItem,
    CatalogOrder,
    CatalogOrderLine,
    CatalogSettings,
    DiscountCode,
    Subscriber,
)
from balebot.services.catalog_entitlements import grant_order_entitlements
from balebot.services import messenger_api
from balebot.services.card_to_card import build_card_to_card_payload
from balebot.services.catalog_currency import format_toman_label
from balebot.services.checkout_form import format_customer_data_for_message
from balebot.services.discount import DiscountError, apply_discount_to_order, validate_discount_code
from balebot.services.shipping import calculate_shipping
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


def extract_recipient_fields(
    customer_data: dict | None = None,
    *,
    extra: dict | None = None,
) -> dict[str, str]:
    data = customer_data or {}
    extra = extra or {}
    return {
        'recipient_name': (
            (extra.get('recipient_name') or data.get('full_name') or '')[:120]
        ),
        'recipient_phone': (
            (extra.get('recipient_phone') or data.get('phone') or '')[:20]
        ),
        'recipient_address': (
            (extra.get('recipient_address') or data.get('address') or '')
        )[:2000],
        'recipient_postal_code': (
            (extra.get('recipient_postal_code') or data.get('postal_code') or '')[:20]
        ),
        'customer_note': (
            (extra.get('customer_note') or data.get('note') or '')[:2000]
        ),
    }


def compute_cart_summary(
    catalog: CatalogSettings,
    subtotal: int,
    *,
    province: str = '',
    discount_code: str = '',
    subscriber: Subscriber | None = None,
) -> dict[str, int | bool]:
    subtotal = max(0, int(subtotal or 0))
    shipping = calculate_shipping(catalog, subtotal, province=province)
    discount_amount = 0
    if discount_code:
        try:
            dc = validate_discount_code(
                catalog,
                discount_code,
                subtotal=subtotal,
                subscriber=subscriber,
            )
            _, discount_amount = apply_discount_to_order(dc, subtotal)
        except DiscountError:
            discount_amount = 0
    total = max(0, subtotal + shipping - discount_amount)
    threshold = catalog.free_shipping_threshold
    free_shipping = (
        catalog.shipping_mode == CatalogSettings.ShippingMode.FREE
        or (threshold is not None and subtotal >= int(threshold))
    )
    return {
        'subtotal': subtotal,
        'shipping_cost': shipping,
        'discount_amount': discount_amount,
        'total': total,
        'free_shipping': free_shipping,
    }


def _apply_checkout_totals(
    order: CatalogOrder,
    catalog: CatalogSettings,
    subtotal: int,
    *,
    province: str = '',
    discount_code: str = '',
) -> None:
    summary = compute_cart_summary(
        catalog,
        subtotal,
        province=province,
        discount_code=discount_code,
        subscriber=order.subscriber,
    )
    order.shipping_cost = int(summary['shipping_cost'])
    order.discount_amount = int(summary['discount_amount'])
    order.discount_code = (discount_code or '').strip()[:40] if summary['discount_amount'] else ''
    order.total_amount = int(summary['total'])
    order.save(
        update_fields=[
            'shipping_cost',
            'discount_amount',
            'discount_code',
            'total_amount',
            'updated_at',
        ],
    )


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
    recipient_extra: dict | None = None,
) -> CatalogOrder | None:
    if not lines:
        return None
    total = 0
    recipient = extract_recipient_fields(customer_data, extra=recipient_extra)
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
            **recipient,
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
    province: str = '',
    discount_code: str = '',
    recipient_extra: dict | None = None,
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
    order = create_order_from_lines(
        workspace=catalog.workspace,
        platform=catalog.platform,
        subscriber=subscriber,
        lines=lines,
        status=status,
        payment_method=payment_method,
        customer_data=customer_data,
        recipient_extra=recipient_extra,
    )
    if not order:
        return None
    subtotal = sum((ln.price_snapshot * ln.quantity) for ln in order.lines.all())
    if discount_code:
        validate_discount_code(
            catalog,
            discount_code,
            subtotal=subtotal,
            subscriber=subscriber,
        )
    try:
        _apply_checkout_totals(
            order,
            catalog,
            subtotal,
            province=province,
            discount_code=discount_code,
        )
    except Exception:
        order.delete()
        raise
    return order


def _format_order_lines(order: CatalogOrder) -> str:
    lines = []
    for ln in order.lines.all():
        lines.append(f'• {ln.title_snapshot} × {ln.quantity} — {format_toman_label(ln.price_snapshot)}')
    return '\n'.join(lines) or '—'


def mark_order_paid(order: CatalogOrder) -> CatalogOrder:
    """پس از پرداخت موفق: وضعیت، موجودی، اعلان‌ها."""
    if order.status == CatalogOrder.Status.PAID:
        return order

    from balebot.models import CatalogItem

    with transaction.atomic():
        order.status = CatalogOrder.Status.PAID
        order.fulfillment_status = CatalogOrder.FulfillmentStatus.PAID
        order.save(update_fields=['status', 'fulfillment_status', 'updated_at'])

        if order.discount_code:
            DiscountCode.objects.filter(
                workspace=order.workspace,
                platform=order.platform,
                code__iexact=order.discount_code,
            ).update(used_count=F('used_count') + 1)

        for line in order.lines.select_related('item').all():
            item = line.item
            if item is None:
                continue
            if item.stock is not None:
                CatalogItem.objects.filter(pk=item.pk, stock__gte=line.quantity).update(
                    stock=F('stock') - line.quantity,
                )
            CatalogItem.objects.filter(pk=item.pk).update(
                sales_count=F('sales_count') + line.quantity,
            )

    try:
        catalog = CatalogSettings.get_for_platform(order.workspace, order.platform)
        cfg = BotSettings.get_for_platform(order.workspace, order.platform)
        sub = order.subscriber
        if sub:
            if order.payment_method == CatalogSettings.PaymentMethod.CARD_TO_CARD:
                customer_text = (
                    f'✅ سفارش شما تأیید شد.\n'
                    f'شماره سفارش: #{order.pk}\n'
                    f'مبلغ: {format_toman_label(order.total_amount)}'
                )
            else:
                customer_text = (
                    f'✅ پرداخت شما با موفقیت انجام شد.\n'
                    f'شماره سفارش: #{order.pk}\n'
                    f'مبلغ: {format_toman_label(order.total_amount)}'
                )
            messenger_api.send_message(
                order.platform,
                sub.chat_id,
                customer_text,
                settings=cfg,
            )
        if catalog.admin_notify_chat_id:
            user_label = '—'
            if sub:
                user_label = sub.first_name or sub.username or str(sub.messenger_user_id)
            text = (
                f'💰 سفارش جدید پرداخت‌شده #{order.pk}\n'
                f'کاربر: {user_label}\n'
                f'مبلغ: {format_toman_label(order.total_amount)}\n\n'
                f'{_format_order_lines(order)}'
            )
            messenger_api.send_message(
                order.platform,
                catalog.admin_notify_chat_id,
                text,
                settings=cfg,
            )
    except messenger_api.MessengerAPIError:
        logger.exception('Failed to notify after order payment')

    try:
        grant_order_entitlements(order)
    except Exception:
        logger.exception('Failed to grant entitlements for order %s', order.pk)

    if order.subscriber_id:
        clear_subscriber_cart(
            workspace=order.workspace,
            platform=order.platform,
            subscriber_id=order.subscriber_id,
        )

    return order


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
        f'جمع کل: {format_toman_label(order.total_amount)}'
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
        f'مبلغ: {format_toman_label(order.total_amount)}'
    )
    messenger_api.send_message(cfg.platform, subscriber.chat_id, ack, settings=cfg)

    clear_subscriber_cart(
        workspace=catalog.workspace,
        platform=catalog.platform,
        subscriber=subscriber,
    )


def submit_request_order(
    order: CatalogOrder,
    catalog: CatalogSettings,
    cfg: BotSettings,
    subscriber: Subscriber,
) -> None:
    """اعلان درخواست تماس/مشاوره به ادمین و تأیید به کاربر."""
    user_label = subscriber.first_name or subscriber.username or str(subscriber.messenger_user_id)
    phone = subscriber.phone_number or '—'
    customer_block = format_customer_data_for_message(catalog.checkout_form, order.customer_data or {})
    note = (order.note or '').strip()
    lines_text = _format_order_lines(order)

    text = (
        f'📩 درخواست جدید #{order.pk}\n'
        f'کاربر: {user_label}\n'
        f'شماره: {phone}\n'
        f'شناسه کاربر: {subscriber.messenger_user_id}\n'
    )
    if note:
        text += f'\n📝 یادداشت: {note}\n'
    if customer_block:
        text += f'\n📋 اطلاعات تماس:\n{customer_block}\n'
    if lines_text and lines_text != '—':
        text += f'\n📦 آیتم:\n{lines_text}\n'

    if catalog.admin_notify_chat_id:
        try:
            messenger_api.send_message(
                cfg.platform,
                catalog.admin_notify_chat_id,
                text,
                settings=cfg,
            )
        except messenger_api.MessengerAPIError:
            logger.exception('Failed to notify admin about request order %s', order.pk)

    ack = (
        f'✅ درخواست شما ثبت شد.\n'
        f'شماره پیگیری: #{order.pk}\n'
        f'به‌زودی با شما تماس گرفته می‌شود.'
    )
    try:
        messenger_api.send_message(cfg.platform, subscriber.chat_id, ack, settings=cfg)
    except messenger_api.MessengerAPIError:
        logger.exception('Failed to ack request order %s to subscriber', order.pk)


def start_card_to_card_checkout(
    order: CatalogOrder,
    catalog: CatalogSettings,
) -> dict[str, str | int]:
    order.payment_method = CatalogSettings.PaymentMethod.CARD_TO_CARD
    order.save(update_fields=['payment_method', 'updated_at'])
    card = build_card_to_card_payload(catalog)
    return {
        'order_id': order.pk,
        'amount': order.total_amount,
        **card,
    }


def submit_payment_receipt(
    order: CatalogOrder,
    catalog: CatalogSettings,
    cfg: BotSettings,
    *,
    receipt_file,
) -> CatalogOrder:
    if order.payment_method != CatalogSettings.PaymentMethod.CARD_TO_CARD:
        raise ValueError('این سفارش با روش کارت به کارت ثبت نشده است.')
    if order.status != CatalogOrder.Status.PENDING:
        raise ValueError('این سفارش دیگر در انتظار پرداخت نیست.')
    if order.payment_receipt:
        raise ValueError('رسید قبلاً ارسال شده است.')

    from django.utils import timezone

    order.payment_receipt = receipt_file
    order.receipt_uploaded_at = timezone.now()
    order.save(update_fields=['payment_receipt', 'receipt_uploaded_at', 'updated_at'])

    sub = order.subscriber
    if sub:
        messenger_api.send_message(
            cfg.platform,
            sub.chat_id,
            (
                f'📎 رسید واریز شما دریافت شد.\n'
                f'شماره سفارش: #{order.pk}\n'
                f'پس از بررسی، نتیجه به شما اطلاع داده می‌شود.'
            ),
            settings=cfg,
        )

    if catalog.admin_notify_chat_id:
        user_label = '—'
        if sub:
            user_label = sub.first_name or sub.username or str(sub.messenger_user_id)
        caption = (
            f'📎 رسید واریز جدید — سفارش #{order.pk}\n'
            f'کاربر: {user_label}\n'
            f'مبلغ: {format_toman_label(order.total_amount)}\n'
            f'برای تأیید به پنل مدیریت بروید.'
        )
        try:
            receipt_file.seek(0)
            messenger_api.send_photo(
                cfg.platform,
                catalog.admin_notify_chat_id,
                photo_file=receipt_file,
                photo_filename=getattr(receipt_file, 'name', 'receipt.jpg'),
                caption=caption,
                settings=cfg,
            )
        except messenger_api.MessengerAPIError:
            logger.exception('Failed to send receipt photo to admin')
            messenger_api.send_message(
                cfg.platform,
                catalog.admin_notify_chat_id,
                caption,
                settings=cfg,
            )

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
        try:
            catalog = CatalogSettings.get_for_platform(cfg.workspace, cfg.platform)
            submit_request_order(order, catalog, cfg, sub)
        except Exception:
            logger.exception('Failed to process web_app request order %s', order.pk)


def get_or_create_cart(workspace, platform: str, subscriber: Subscriber) -> CatalogCart:
    cart, _ = CatalogCart.objects.get_or_create(
        workspace=workspace,
        platform=platform,
        subscriber=subscriber,
    )
    return cart


def clear_subscriber_cart(
    *,
    workspace,
    platform: str,
    subscriber: Subscriber | None = None,
    subscriber_id: int | None = None,
) -> None:
    """خالی کردن سبد پس از ثبت سفارش موفق."""
    sid = subscriber.pk if subscriber is not None else subscriber_id
    if not sid:
        return
    CatalogCart.objects.filter(
        workspace=workspace,
        platform=platform,
        subscriber_id=sid,
    ).delete()


def remove_item_from_subscriber_cart(
    *,
    workspace,
    platform: str,
    subscriber: Subscriber,
    item_id: int,
) -> None:
    from balebot.models import CatalogCartItem

    CatalogCartItem.objects.filter(
        cart__workspace=workspace,
        cart__platform=platform,
        cart__subscriber=subscriber,
        catalog_item_id=item_id,
    ).delete()
