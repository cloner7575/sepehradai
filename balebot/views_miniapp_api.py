"""REST API عمومی مینی‌اپ فروشگاه."""

from __future__ import annotations

import json
import logging

from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from balebot.models import (
    BotSettings,
    CatalogCategory,
    CatalogItem,
    CatalogItemMedia,
    CatalogOrder,
    CatalogSettings,
    Subscriber,
)
from balebot.services import catalog_payment, miniapp_auth
from balebot.services.catalog_media import absolute_media_url
from balebot.services.webhook_logic import get_or_create_subscriber

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
        return None, _json_error('فروشگاه یافت نشد', 404)
    if not catalog.workspace.is_active:
        return None, _json_error('حساب فروشگاه غیرفعال است', 403)
    if require_enabled and not catalog.is_enabled:
        return None, _json_error('فروشگاه هنوز فعال نشده است. از پنل مدیریت فعال کنید.', 403)
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
    download_url = ''
    if item.download_file:
        download_url = absolute_media_url(request, item.download_file.url, catalog=catalog)
    return {
        'id': item.pk,
        'slug': item.slug,
        'title': item.title,
        'short_description': item.short_description,
        'description': item.description,
        'item_type': item.item_type,
        'price': item.price,
        'sale_mode': item.sale_mode,
        'is_buyable': item.is_buyable(),
        'is_requestable': item.is_requestable(),
        'is_downloadable': item.is_downloadable(),
        'is_featured': item.is_featured,
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


@require_http_methods(['GET'])
def catalog_config(request, public_id):
    catalog, err = _resolve_catalog(public_id)
    if err:
        return err
    cfg = BotSettings.get_for_platform(catalog.workspace, catalog.platform)
    logo_url = ''
    if catalog.logo:
        logo_url = absolute_media_url(request, catalog.logo.url, catalog=catalog)
    methods = []
    for value, label in catalog.enabled_payment_methods():
        methods.append({'id': value, 'label': label})
    return JsonResponse({
        'ok': True,
        'is_enabled': catalog.is_enabled,
        'platform': catalog.platform,
        'hero_title': catalog.hero_title,
        'hero_subtitle': catalog.hero_subtitle,
        'theme': catalog.theme_config or {},
        'labels': catalog.labels or {},
        'logo_url': logo_url,
        'mini_app_url': catalog.build_mini_app_url(cfg),
        'payment_methods': methods if catalog.is_enabled else [],
        'payment_default': catalog.resolve_payment_method(None) if catalog.is_enabled else None,
    })


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
    sort = (request.GET.get('sort') or '').strip()
    if sort == 'price_asc':
        qs = qs.order_by('price', 'sort_order')
    elif sort == 'price_desc':
        qs = qs.order_by('-price', 'sort_order')
    else:
        qs = qs.order_by('sort_order', '-created_at')
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
    return JsonResponse({
        'ok': True,
        'subscriber_id': sub.pk,
        'user': {
            'id': sub.messenger_user_id,
            'first_name': sub.first_name,
            'username': sub.username,
        },
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
        return JsonResponse({'ok': True, 'items': items, 'total': total})

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
    quantity = int(body.get('quantity') or 1)
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
    return JsonResponse({'ok': True, 'items': items, 'total': total})


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

    item_id = body.get('item_id')
    use_cart = body.get('use_cart', True)
    order = None
    if item_id:
        item = get_object_or_404(
            CatalogItem,
            pk=item_id,
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
        )
    elif use_cart:
        cart = catalog_payment.get_or_create_cart(catalog.workspace, catalog.platform, sub)
        order = catalog_payment.create_checkout_order(
            catalog=catalog,
            subscriber=sub,
            cart=cart,
            payment_method=payment_method,
        )
    if not order or order.total_amount <= 0:
        return _json_error('سبد خرید خالی است یا قیمت نامعتبر')

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

    if payment_method == CatalogSettings.PaymentMethod.ZARINPAL:
        base = (cfg.webhook_public_url or '').strip().rstrip('/')
        if not base:
            return _json_error('آدرس عمومی سرور در تنظیمات ربات تنظیم نشده است', 500)
        callback_url = f'{base}/shop/{catalog.public_id}/payment/zarinpal/callback/?order_id={order.pk}'
        try:
            payment_url = catalog_payment.start_zarinpal_checkout(order, catalog, callback_url)
        except Exception as e:
            logger.exception('zarinpal request failed')
            order.status = CatalogOrder.Status.FAILED
            order.save(update_fields=['status', 'updated_at'])
            return _json_error(str(e) or 'خطا در اتصال به زرین‌پال', 500)
        return JsonResponse({
            'ok': True,
            'order_id': order.pk,
            'payment_method': payment_method,
            'payment_url': payment_url,
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
    order = catalog_payment.create_order_from_lines(
        workspace=catalog.workspace,
        platform=catalog.platform,
        subscriber=sub,
        lines=lines,
        status=CatalogOrder.Status.REQUEST,
        note=note or 'درخواست از مینی‌اپ',
    )
    if not order:
        return _json_error('ثبت درخواست ناموفق')
    return JsonResponse({'ok': True, 'order_id': order.pk, 'status': 'request'})
