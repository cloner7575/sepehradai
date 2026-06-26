"""REST API عمومی مینی‌اپ فروشگاه."""

from __future__ import annotations

import json
import logging

from django.db.models import Q
from django.http import FileResponse, Http404, JsonResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from balebot.models import (
    BotSettings,
    CatalogCategory,
    CatalogItem,
    CatalogItemMedia,
    CatalogOrder,
    CatalogSettings,
    Platform,
    Subscriber,
)
from balebot.services import catalog_payment, miniapp_auth
from balebot.services.checkout_form import public_checkout_form, validate_customer_data
from balebot.services.catalog_media import (
    absolute_media_url,
    absolutize_home_blocks,
    guess_content_type,
    request_public_base_url,
    resolve_media_file,
)
from balebot.services.catalog_page_layout import get_home_blocks
from balebot.services.public_url import resolve_public_base_url
from balebot.services.channel_membership import is_channel_member
from balebot.services.webhook_logic import get_or_create_subscriber
from balebot.services.workspace_subscription import workspace_block_reason

logger = logging.getLogger(__name__)


def _resolve_catalog(
    public_id: str,
    *,
    require_enabled: bool = False,
) -> tuple[CatalogSettings | None, JsonResponse | None]:
    """یافتن فروشگاه؛ برای خواندن کاتالوگ نیازی به is_enabled نیست."""
    try:
        catalog = CatalogSettings.objects.select_related('workspace').get(public_id=public_id)
    except CatalogSettings.DoesNotExist:
        return None, _json_error('مینی‌اپ یافت نشد', 404)
    if not catalog.workspace.is_active:
        return None, _json_error('حساب مینی‌اپ غیرفعال است', 403)
    block_reason = workspace_block_reason(catalog.workspace)
    if block_reason:
        return None, _json_error(block_reason, 403)
    if require_enabled and not catalog.is_enabled:
        return None, _json_error('مینی‌اپ هنوز فعال نشده است. از پنل مدیریت فعال کنید.', 403)
    return catalog, None


def _json_error(message: str, status: int = 400) -> JsonResponse:
    return JsonResponse({'ok': False, 'error': message}, status=status)


def _media_dict(media: CatalogItemMedia, request=None, catalog=None) -> dict:
    url = media.file.url if media.file else ''
    if request:
        url = absolute_media_url(request, url, catalog=catalog)
    return {
        'id': media.pk,
        'type': media.media_type,
        'url': url,
        'title': media.title or '',
    }


def _item_dict(item: CatalogItem, request=None, catalog=None) -> dict:
    media_list = [_media_dict(m, request, catalog) for m in item.media.all()]
    images = [m['url'] for m in media_list if m['type'] == CatalogItemMedia.MediaType.IMAGE]
    cover_url = ''
    if item.cover:
        cover_url = absolute_media_url(request, item.cover.url, catalog=catalog)
        if cover_url and cover_url not in images:
            images.insert(0, cover_url)
    download_url = item.resolve_download_url(request, catalog) if item.is_downloadable() else ''
    flash_active = item.is_flash_sale_active()
    return {
        'id': item.pk,
        'slug': item.slug,
        'title': item.title,
        'short_description': item.short_description,
        'description': item.description,
        'item_type': item.normalized_item_type(),
        'price': item.price,
        'compare_at_price': item.compare_at_price,
        'sales_count': item.sales_count or 0,
        'sale_mode': item.sale_mode,
        'is_buyable': item.is_buyable(),
        'is_requestable': item.is_requestable(),
        'is_downloadable': item.is_downloadable(),
        'is_featured': item.is_featured,
        'is_flash_sale': item.is_flash_sale,
        'is_flash_sale_active': flash_active,
        'flash_sale_ends_at': (
            item.flash_sale_ends_at.isoformat() if item.flash_sale_ends_at else None
        ),
        'metadata': item.metadata or {},
        'media': media_list,
        'images': images,
        'cover_url': cover_url,
        'download_url': download_url,
        'category_id': item.category_id,
        'category_slug': item.category.slug if item.category else None,
    }


def _first_item_image_url(item: CatalogItem, request=None, catalog=None) -> str:
    if item.cover:
        return absolute_media_url(request, item.cover.url, catalog=catalog) if request else item.cover.url
    media = item.media.filter(media_type=CatalogItemMedia.MediaType.IMAGE).first()
    if not media or not media.file:
        return ''
    return absolute_media_url(request, media.file.url, catalog=catalog) if request else media.file.url


def _resolve_subscriber(catalog: CatalogSettings, init_data: str) -> Subscriber | None:
    cfg = BotSettings.get_for_platform(catalog.workspace, catalog.platform)
    parsed = miniapp_auth.validate_for_bot_settings(init_data, cfg)
    if not parsed or not parsed.get('user'):
        return None
    user = parsed['user']
    uid = int(user['id'])
    chat_id = uid
    from_user = {
        'id': uid,
        'first_name': user.get('first_name') or '',
        'last_name': user.get('last_name') or '',
        'username': user.get('username') or '',
    }
    chat = {'id': chat_id, 'type': 'private'}
    return get_or_create_subscriber(cfg, from_user, chat)


def _mark_miniapp_seen(sub: Subscriber) -> None:
    if sub.miniapp_first_seen_at:
        return
    sub.miniapp_first_seen_at = timezone.now()
    sub.save(update_fields=['miniapp_first_seen_at', 'updated_at'])


def _channel_auth_payload(catalog: CatalogSettings, user_id: int) -> dict:
    if not catalog.require_channel_membership:
        return {
            'channel_required': False,
            'is_channel_member': True,
            'channel_message': '',
            'channel_invite_link': '',
        }
    is_member = is_channel_member(catalog, user_id)
    return {
        'channel_required': True,
        'is_channel_member': is_member,
        'channel_message': (catalog.channel_membership_message or '').strip()
        or 'برای استفاده از مینی‌اپ ابتدا در کانال ما عضو شوید.',
        'channel_invite_link': (catalog.channel_invite_link or '').strip(),
    }


@require_http_methods(['GET'])
def catalog_config(request, public_id):
    catalog, err = _resolve_catalog(public_id)
    if err:
        return err
    cfg = BotSettings.get_for_platform(catalog.workspace, catalog.platform)
    logo_url = ''
    if catalog.logo:
        logo_url = absolute_media_url(request, catalog.logo.url, catalog=catalog)
    hero_background_url = ''
    if catalog.hero_background:
        hero_background_url = absolute_media_url(request, catalog.hero_background.url, catalog=catalog)
    public_base_url = request_public_base_url(request) or resolve_public_base_url(cfg).rstrip('/')
    methods = []
    for value, label in catalog.enabled_payment_methods():
        methods.append({'id': value, 'label': label})
    can_purchase = catalog.can_accept_orders()
    theme = catalog.theme_config or {}
    home_blocks = absolutize_home_blocks(get_home_blocks(theme), request, catalog=catalog)
    return JsonResponse({
        'ok': True,
        'is_enabled': catalog.is_enabled,
        'can_purchase': can_purchase,
        'platform': catalog.platform,
        'hero_title': catalog.hero_title,
        'hero_subtitle': catalog.hero_subtitle,
        'theme': theme,
        'home_blocks': home_blocks,
        'labels': catalog.labels or {},
        'logo_url': logo_url,
        'hero_background_url': hero_background_url,
        'public_base_url': public_base_url,
        'mini_app_url': catalog.build_mini_app_url(cfg),
        'payment_methods': methods if can_purchase else [],
        'payment_default': catalog.resolve_payment_method(None) if can_purchase else None,
        'checkout_form': public_checkout_form(catalog.checkout_form),
        'shipping': {
            'mode': catalog.shipping_mode,
            'flat_cost': int(catalog.shipping_flat_cost or 0),
            'free_threshold': (
                int(catalog.free_shipping_threshold)
                if catalog.free_shipping_threshold is not None
                else None
            ),
            'provinces': list((catalog.shipping_by_province or {}).keys()),
        },
    })


@require_http_methods(['GET'])
def catalog_media_file(request, public_id, file_path):
    """سرو امن فایل‌های media برای مینی‌اپ (مستقل از nginx /media/)."""
    catalog, err = _resolve_catalog(public_id)
    if err:
        return err
    full = resolve_media_file(file_path)
    if full is None:
        raise Http404('فایل یافت نشد')
    response = FileResponse(full.open('rb'), content_type=guess_content_type(full))
    response['Access-Control-Allow-Origin'] = '*'
    response['Cross-Origin-Resource-Policy'] = 'cross-origin'
    response['Cache-Control'] = 'public, max-age=86400'
    return response


@require_http_methods(['GET'])
def catalog_categories(request, public_id):
    catalog, err = _resolve_catalog(public_id)
    if err:
        return err
    cats = CatalogCategory.objects.filter(
        workspace=catalog.workspace,
        platform=catalog.platform,
        is_active=True,
    ).order_by('sort_order', 'name')
    data = []
    for c in cats:
        image_url = ''
        if c.image:
            image_url = absolute_media_url(request, c.image.url, catalog=catalog)
        data.append({
            'id': c.pk,
            'slug': c.slug,
            'name': c.name,
            'icon': c.icon,
            'image_url': image_url,
            'parent_id': c.parent_id,
        })
    return JsonResponse({'ok': True, 'categories': data})


@require_http_methods(['GET'])
def catalog_items(request, public_id):
    catalog, err = _resolve_catalog(public_id)
    if err:
        return err
    qs = CatalogItem.objects.filter(
        workspace=catalog.workspace,
        platform=catalog.platform,
        is_active=True,
    ).select_related('category').prefetch_related('media')
    cat = (request.GET.get('category') or '').strip()
    if cat:
        qs = qs.filter(category__slug=cat)
    q = (request.GET.get('q') or '').strip()
    if q:
        qs = qs.filter(title__icontains=q)
    featured = (request.GET.get('featured') or '').strip().lower()
    if featured in ('1', 'true', 'yes'):
        qs = qs.filter(is_featured=True)
    source = (request.GET.get('source') or '').strip().lower()
    tag_slug = (request.GET.get('tag') or '').strip()
    if source == 'newest':
        qs = qs.order_by('-created_at')
    elif source == 'bestselling':
        qs = qs.order_by('-sales_count', 'sort_order')
    elif source == 'discounted':
        qs = qs.filter(compare_at_price__isnull=False).filter(compare_at_price__gt=0)
        qs = qs.order_by('sort_order', '-created_at')
    elif source == 'flash_sale':
        now = timezone.now()
        qs = qs.filter(is_flash_sale=True).filter(
            Q(flash_sale_starts_at__isnull=True) | Q(flash_sale_starts_at__lte=now),
        ).filter(
            Q(flash_sale_ends_at__isnull=True) | Q(flash_sale_ends_at__gte=now),
        )
        qs = qs.order_by('sort_order', '-created_at')
    elif source == 'category' and cat:
        qs = qs.filter(category__slug=cat)
    elif source == 'tag' and tag_slug:
        qs = qs.filter(metadata__tags__contains=[tag_slug])
    elif source == 'featured':
        qs = qs.filter(is_featured=True)
    sort = (request.GET.get('sort') or '').strip()
    if sort == 'price_asc':
        qs = qs.order_by('price', 'sort_order')
    elif sort == 'price_desc':
        qs = qs.order_by('-price', 'sort_order')
    elif not source:
        qs = qs.order_by('sort_order', '-created_at')
    limit_raw = (request.GET.get('limit') or '').strip()
    if limit_raw.isdigit():
        limit = max(1, min(int(limit_raw), 48))
        qs = qs[:limit]
    return JsonResponse({
        'ok': True,
        'items': [_item_dict(i, request, catalog) for i in qs],
    })


@require_http_methods(['GET'])
def catalog_item_detail(request, public_id, slug):
    catalog, err = _resolve_catalog(public_id)
    if err:
        return err
    item = get_object_or_404(
        CatalogItem.objects.prefetch_related('media'),
        workspace=catalog.workspace,
        platform=catalog.platform,
        slug=slug,
        is_active=True,
    )
    return JsonResponse({'ok': True, 'item': _item_dict(item, request, catalog)})


@csrf_exempt
@require_http_methods(['POST'])
def catalog_auth_validate(request, public_id):
    catalog, err = _resolve_catalog(public_id)
    if err:
        return err
    try:
        body = json.loads(request.body.decode('utf-8'))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return _json_error('بدنه نامعتبر')
    init_data = (body.get('initData') or body.get('init_data') or '').strip()
    sub = _resolve_subscriber(catalog, init_data)
    if not sub:
        return _json_error('احراز هویت ناموفق', 401)
    _mark_miniapp_seen(sub)
    channel = _channel_auth_payload(catalog, sub.messenger_user_id)
    return JsonResponse({
        'ok': True,
        'subscriber_id': sub.pk,
        'user': {
            'id': sub.messenger_user_id,
            'first_name': sub.first_name,
            'username': sub.username,
        },
        **channel,
    })


def _parse_body(request) -> dict:
    try:
        return json.loads(request.body.decode('utf-8'))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return {}


def _cart_line_dict(entry, request=None, catalog=None) -> dict:
    item = entry.catalog_item
    line_total = (item.price or 0) * entry.quantity
    return {
        'item_id': item.pk,
        'slug': item.slug,
        'title': item.title,
        'price': item.price,
        'quantity': entry.quantity,
        'line_total': line_total,
        'image': _first_item_image_url(item, request, catalog),
    }


@csrf_exempt
@require_http_methods(['GET', 'POST'])
def catalog_cart(request, public_id):
    catalog, err = _resolve_catalog(public_id, require_enabled=True)
    if err:
        return err
    if request.method == 'GET':
        init_data = (request.GET.get('initData') or '').strip()
        sub = _resolve_subscriber(catalog, init_data)
        if not sub:
            return _json_error('احراز هویت لازم است', 401)
        cart = catalog_payment.get_or_create_cart(catalog.workspace, catalog.platform, sub)
        items = []
        total = 0
        for entry in cart.items.select_related('catalog_item').prefetch_related('catalog_item__media').all():
            item = entry.catalog_item
            if not item.is_active:
                continue
            line = _cart_line_dict(entry, request, catalog)
            total += line['line_total']
            items.append(line)
        province = (request.GET.get('province') or '').strip()
        discount_code = (request.GET.get('discount_code') or '').strip()
        summary = catalog_payment.compute_cart_summary(
            catalog, total, province=province, discount_code=discount_code,
        )
        return JsonResponse({
            'ok': True,
            'items': items,
            'subtotal': summary['subtotal'],
            'shipping_cost': summary['shipping_cost'],
            'discount_amount': summary['discount_amount'],
            'total': summary['total'],
            'free_shipping': summary['free_shipping'],
        })

    body = _parse_body(request)
    init_data = (body.get('initData') or '').strip()
    sub = _resolve_subscriber(catalog, init_data)
    if not sub:
        return _json_error('احراز هویت لازم است', 401)
    cart = catalog_payment.get_or_create_cart(catalog.workspace, catalog.platform, sub)
    action = (body.get('action') or 'set').strip()
    if action == 'clear':
        cart.items.all().delete()
        return JsonResponse({'ok': True, 'items': [], 'total': 0})
    item_id = body.get('item_id')
    if 'quantity' not in body:
        quantity = 1
    else:
        quantity = int(body['quantity'])
    if not item_id:
        return _json_error('item_id الزامی است')
    item = get_object_or_404(
        CatalogItem,
        pk=item_id,
        workspace=catalog.workspace,
        platform=catalog.platform,
        is_active=True,
    )
    from balebot.models import CatalogCartItem
    if quantity <= 0:
        CatalogCartItem.objects.filter(cart=cart, catalog_item=item).delete()
    else:
        entry, _ = CatalogCartItem.objects.get_or_create(cart=cart, catalog_item=item)
        entry.quantity = quantity
        entry.save(update_fields=['quantity'])
    items = []
    total = 0
    for entry in cart.items.select_related('catalog_item').prefetch_related('catalog_item__media').all():
        ci = entry.catalog_item
        if not ci.is_active:
            continue
        line = _cart_line_dict(entry, request, catalog)
        total += line['line_total']
        items.append(line)
    province = (body.get('province') or '').strip()
    discount_code = (body.get('discount_code') or '').strip()
    summary = catalog_payment.compute_cart_summary(
        catalog, total, province=province, discount_code=discount_code,
    )
    return JsonResponse({
        'ok': True,
        'items': items,
        'subtotal': summary['subtotal'],
        'shipping_cost': summary['shipping_cost'],
        'discount_amount': summary['discount_amount'],
        'total': summary['total'],
        'free_shipping': summary['free_shipping'],
    })


@csrf_exempt
@require_http_methods(['POST'])
def catalog_checkout(request, public_id):
    catalog, err = _resolve_catalog(public_id, require_enabled=True)
    if err:
        return err
    body = _parse_body(request)
    init_data = (body.get('initData') or '').strip()
    sub = _resolve_subscriber(catalog, init_data)
    if not sub:
        return _json_error('احراز هویت لازم است', 401)
    cfg = BotSettings.get_for_platform(catalog.workspace, catalog.platform)
    payment_method = catalog.resolve_payment_method((body.get('payment_method') or '').strip())
    if not payment_method:
        return _json_error('هیچ روش پرداختی فعال نیست', 400)

    customer_data, form_errors = validate_customer_data(
        catalog.checkout_form,
        body.get('customer_data'),
    )
    if form_errors:
        return _json_error(form_errors[0], 400)

    province = (body.get('province') or customer_data.get('city') or '').strip()
    discount_code = (body.get('discount_code') or '').strip()
    recipient_extra = {
        'recipient_name': body.get('recipient_name'),
        'recipient_phone': body.get('recipient_phone'),
        'recipient_address': body.get('recipient_address'),
        'recipient_postal_code': body.get('recipient_postal_code'),
        'customer_note': body.get('customer_note'),
    }

    item_id = body.get('item_id')
    use_cart = body.get('use_cart', True)
    order = None
    checkout_from_cart = False
    checkout_item_id = None
    try:
        if item_id:
            checkout_item_id = int(item_id)
            item = get_object_or_404(
                CatalogItem,
                pk=checkout_item_id,
                workspace=catalog.workspace,
                platform=catalog.platform,
                is_active=True,
            )
            order = catalog_payment.create_checkout_order(
                catalog=catalog,
                subscriber=sub,
                item=item,
                quantity=int(body.get('quantity') or 1),
                payment_method=payment_method,
                customer_data=customer_data,
                province=province,
                discount_code=discount_code,
                recipient_extra=recipient_extra,
            )
        elif use_cart:
            checkout_from_cart = True
            cart = catalog_payment.get_or_create_cart(catalog.workspace, catalog.platform, sub)
            order = catalog_payment.create_checkout_order(
                catalog=catalog,
                subscriber=sub,
                cart=cart,
                payment_method=payment_method,
                customer_data=customer_data,
                province=province,
                discount_code=discount_code,
                recipient_extra=recipient_extra,
            )
    except Exception as e:
        from balebot.services.discount import DiscountError

        if isinstance(e, DiscountError):
            return _json_error(str(e), 400)
        raise
    if not order or order.total_amount <= 0:
        return _json_error('سبد خرید خالی است یا قیمت نامعتبر')

    def _clear_cart_after_checkout() -> None:
        if checkout_from_cart:
            catalog_payment.clear_subscriber_cart(
                workspace=catalog.workspace,
                platform=catalog.platform,
                subscriber=sub,
            )
        elif checkout_item_id:
            catalog_payment.remove_item_from_subscriber_cart(
                workspace=catalog.workspace,
                platform=catalog.platform,
                subscriber=sub,
                item_id=checkout_item_id,
            )

    if payment_method == CatalogSettings.PaymentMethod.ADMIN_CART:
        try:
            catalog_payment.submit_admin_cart_order(order, catalog, cfg, sub)
        except Exception as e:
            logger.exception('admin cart submit failed')
            order.status = CatalogOrder.Status.FAILED
            order.save(update_fields=['status', 'updated_at'])
            return _json_error(str(e) or 'ارسال به ادمین ناموفق بود', 500)
        return JsonResponse({
            'ok': True,
            'order_id': order.pk,
            'payment_method': payment_method,
            'status': 'submitted',
            'message': 'سبد خرید برای ادمین ارسال شد',
        })

    if payment_method == CatalogSettings.PaymentMethod.CARD_TO_CARD:
        card_payload = catalog_payment.start_card_to_card_checkout(order, catalog)
        _clear_cart_after_checkout()
        return JsonResponse({
            'ok': True,
            'order_id': order.pk,
            'payment_method': payment_method,
            'method': 'card_to_card',
            'amount': order.total_amount,
            'card': {
                'number': card_payload['number'],
                'number_display': card_payload['number_display'],
                'sheba': card_payload['sheba'],
                'sheba_display': card_payload['sheba_display'],
                'holder': card_payload['holder'],
            },
            'message': 'لطفاً مبلغ را واریز کنید و رسید را آپلود نمایید.',
        })

    if payment_method == CatalogSettings.PaymentMethod.BALE:
        if catalog.platform != Platform.BALE:
            return _json_error('پرداخت بله فقط در مینی‌اپ بله در دسترس است', 400)
        try:
            from balebot.services.bale_payment import start_bale_checkout

            start_bale_checkout(order, catalog, cfg)
        except Exception as e:
            logger.exception('bale invoice failed')
            order.status = CatalogOrder.Status.FAILED
            order.save(update_fields=['status', 'updated_at'])
            return _json_error(str(e) or 'ارسال صورت‌حساب بله ناموفق بود', 500)
        _clear_cart_after_checkout()
        return JsonResponse({
            'ok': True,
            'order_id': order.pk,
            'payment_method': payment_method,
            'method': 'bale_invoice',
            'message': 'صورت‌حساب به گفت‌وگوی شما در بله ارسال شد؛ برای تکمیل خرید، روی پرداخت بزنید.',
        })

    return _json_error('روش پرداخت نامعتبر', 400)


@csrf_exempt
@require_http_methods(['POST'])
def catalog_request(request, public_id):
    catalog, err = _resolve_catalog(public_id, require_enabled=True)
    if err:
        return err
    body = _parse_body(request)
    init_data = (body.get('initData') or '').strip()
    sub = _resolve_subscriber(catalog, init_data)
    if not sub:
        return _json_error('احراز هویت لازم است', 401)
    item_id = body.get('item_id')
    item = None
    if item_id:
        item = CatalogItem.objects.filter(
            pk=item_id,
            workspace=catalog.workspace,
            platform=catalog.platform,
            is_active=True,
        ).first()
        if item and not item.is_requestable():
            return _json_error('این آیتم قابل درخواست نیست')
    lines = []
    if item:
        lines = [(item, int(body.get('quantity') or 1))]
    note = (body.get('note') or '')[:2000]
    customer_data, form_errors = validate_customer_data(
        catalog.checkout_form,
        body.get('customer_data'),
    )
    if form_errors:
        return _json_error(form_errors[0], 400)
    order = catalog_payment.create_order_from_lines(
        workspace=catalog.workspace,
        platform=catalog.platform,
        subscriber=sub,
        lines=lines,
        status=CatalogOrder.Status.REQUEST,
        note=note or 'درخواست از مینی‌اپ',
        customer_data=customer_data,
    )
    if not order:
        return _json_error('ثبت درخواست ناموفق')
    return JsonResponse({'ok': True, 'order_id': order.pk, 'status': 'request'})


@require_http_methods(['GET'])
def catalog_order_payment(request, public_id, order_id):
    catalog, err = _resolve_catalog(public_id, require_enabled=True)
    if err:
        return err
    init_data = (request.GET.get('initData') or '').strip()
    sub = _resolve_subscriber(catalog, init_data)
    if not sub:
        return _json_error('احراز هویت لازم است', 401)
    order = get_object_or_404(
        CatalogOrder,
        pk=order_id,
        workspace=catalog.workspace,
        platform=catalog.platform,
        subscriber=sub,
    )
    if order.payment_method != CatalogSettings.PaymentMethod.CARD_TO_CARD:
        return _json_error('این سفارش کارت به کارت نیست', 400)
    from balebot.services.card_to_card import build_card_to_card_payload

    card = build_card_to_card_payload(catalog)
    receipt_url = ''
    if order.payment_receipt:
        receipt_url = absolute_media_url(request, order.payment_receipt.url, catalog=catalog)
    return JsonResponse({
        'ok': True,
        'order_id': order.pk,
        'amount': order.total_amount,
        'status': order.status,
        'receipt_uploaded': bool(order.payment_receipt),
        'receipt_url': receipt_url,
        'card': card,
    })


@csrf_exempt
@require_http_methods(['POST'])
def catalog_order_receipt(request, public_id, order_id):
    catalog, err = _resolve_catalog(public_id, require_enabled=True)
    if err:
        return err
    init_data = (request.POST.get('initData') or '').strip()
    sub = _resolve_subscriber(catalog, init_data)
    if not sub:
        return _json_error('احراز هویت لازم است', 401)
    order = get_object_or_404(
        CatalogOrder,
        pk=order_id,
        workspace=catalog.workspace,
        platform=catalog.platform,
        subscriber=sub,
        payment_method=CatalogSettings.PaymentMethod.CARD_TO_CARD,
    )
    upload = request.FILES.get('receipt')
    if not upload:
        return _json_error('فایل رسید انتخاب نشده است', 400)
    if upload.size > 10 * 1024 * 1024:
        return _json_error('حداکثر حجم فایل ۱۰ مگابایت است', 400)
    content_type = (upload.content_type or '').lower()
    if not content_type.startswith('image/'):
        return _json_error('فقط تصویر رسید قابل قبول است', 400)
    cfg = BotSettings.get_for_platform(catalog.workspace, catalog.platform)
    try:
        catalog_payment.submit_payment_receipt(order, catalog, cfg, receipt_file=upload)
    except ValueError as exc:
        return _json_error(str(exc), 400)
    except Exception:
        logger.exception('receipt upload failed')
        return _json_error('آپلود رسید ناموفق بود', 500)
    return JsonResponse({
        'ok': True,
        'order_id': order.pk,
        'status': 'receipt_submitted',
        'message': 'رسید شما دریافت شد. پس از بررسی، نتیجه اطلاع داده می‌شود.',
    })
