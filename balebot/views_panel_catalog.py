"""ویوهای پنل مدیریت فروشگاه مینی‌اپ."""

from __future__ import annotations

import json

from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.db.models import Count, Q, Sum
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.views import View
from django.views.generic import CreateView, DetailView, ListView, TemplateView, UpdateView

from balebot.forms_catalog import (
    CatalogCategoryForm,
    CatalogItemForm,
    CatalogOrderUpdateForm,
    CatalogSettingsForm,
    DiscountCodeForm,
    MiniAppFlowForm,
)
from balebot.models import (
    BotSettings,
    CatalogCategory,
    CatalogItem,
    CatalogItemMedia,
    CatalogItemMember,
    CatalogOrder,
    CatalogSettings,
    DiscountCode,
    StoreTemplate,
    Tag,
)
from balebot.platform import get_bot_settings_for_request, require_miniapp_access_for_request
from balebot.services.catalog_currency import format_toman_label
from balebot.services.catalog_item_types import ITEM_TYPE_GUIDES, get_item_type_guide
from balebot.services.catalog_media import detect_media_type
from balebot.services.catalog_page_layout import get_home_blocks, sanitize_home_blocks
from balebot.services.checkout_form import get_checkout_form
from balebot.services.public_url import resolve_public_base_url
from balebot.mixins import SuperuserRequiredMixin
from balebot.services.discount import discount_codes_for_editor
from balebot.services.store_template_io import (
    StoreTemplateImportError,
    build_export_bundle,
    build_single_export,
    delete_store_template,
    delete_all_store_templates,
    import_store_templates,
    parse_import_file as parse_store_template_import_file,
)
from balebot.services.store_template import apply_template
from balebot.services.catalog_bulk_import import (
    build_sample_workbook,
    import_rows,
    parse_import_file,
    preview_import_rows,
)
from balebot.views_panel import PanelAccessMixin, WorkspaceScopedMixin

STORE_TEMPLATE_INDUSTRY_LABELS = {
    'fashion': 'پوشاک',
    'digital': 'دیجیتال',
    'decor': 'دکوراسیون',
    'service': 'خدمات',
    'kids': 'کودک',
    'pet': 'پت‌شاپ',
    'clothing': 'پوشاک',
    'cosmetics': 'آرایشی و بهداشتی',
    'food': 'خوراکی',
    'bakery': 'شیرینی و نان',
    'coffee': 'کافه',
    'nuts': 'آجیل و خشکبار',
    'plants': 'گل و گیاه',
    'home-decor': 'دکوراسیون',
    'jewelry': 'جواهر و اکسسوری',
    'bags-shoes': 'کیف و کفش',
    'mobile-acc': 'موبایل و لوازم جانبی',
    'books': 'کتاب',
    'sports': 'ورزشی',
    'toys': 'اسباب‌بازی',
    'handicraft': 'صنایع دستی',
    'organic': 'ارگانیک',
    'petshop': 'پت‌شاپ',
    'salon': 'سالن زیبایی',
    'education': 'آموزش',
    'restaurant': 'رستوران',
    'digital-products': 'محصولات دیجیتال',
    'perfume': 'عطر و ادکلن',
    'general': 'عمومی',
}


def _attach_item_preview_image(item: CatalogItem) -> None:
    img = next(
        (m for m in item.media.all() if m.media_type == CatalogItemMedia.MediaType.IMAGE),
        None,
    )
    item.preview_image = img.file if img else None


def _catalog_item_status(item: CatalogItem | None, form=None) -> dict:
    inst = item
    if form is not None:
        inst = form.instance
    if inst is None:
        inst = CatalogItem()
    item_type = inst.normalized_item_type() if hasattr(inst, 'normalized_item_type') else (
        CatalogItem.ItemType.SHOWCASE if inst.item_type == 'portfolio' else (inst.item_type or CatalogItem.ItemType.PRODUCT)
    )
    price = inst.price
    sale_mode = inst.sale_mode or CatalogItem.SaleMode.BOTH
    guide = get_item_type_guide(item_type)
    sale_labels = dict(CatalogItem.SaleMode.choices)
    if item_type == CatalogItem.ItemType.DOWNLOAD:
        sale_label = 'دانلود رایگان'
    elif item_type == CatalogItem.ItemType.SHOWCASE:
        sale_label = 'فقط درخواست تماس'
    else:
        sale_label = sale_labels.get(sale_mode, 'خرید و درخواست')
    return {
        'type_label': str(guide.get('label', 'محصول')),
        'is_active': bool(inst.is_active),
        'sale_mode_label': sale_label,
        'price_label': (
            'رایگان' if item_type == CatalogItem.ItemType.DOWNLOAD
            else (format_toman_label(price) if price else '—')
        ),
        'is_download': item_type == CatalogItem.ItemType.DOWNLOAD,
    }


def _order_status_counts(scope: dict) -> dict[str, int]:
    qs = CatalogOrder.objects.filter(**scope)
    by_status = {
        row['status']: row['c']
        for row in qs.values('status').annotate(c=Count('id'))
    }
    return {
        'all': qs.count(),
        'paid': by_status.get(CatalogOrder.Status.PAID, 0),
        'pending': by_status.get(CatalogOrder.Status.PENDING, 0),
        'c2c_pending': by_status.get(CatalogOrder.Status.C2C_PENDING, 0),
        'request': by_status.get(CatalogOrder.Status.REQUEST, 0),
        'failed': by_status.get(CatalogOrder.Status.FAILED, 0),
        'cancelled': by_status.get(CatalogOrder.Status.CANCELLED, 0),
    }


def _order_payment_label(method: str) -> str:
    labels = dict(CatalogSettings.PaymentMethod.choices)
    return labels.get(method, method or '—')


def _order_customer_rows(catalog: CatalogSettings, order: CatalogOrder) -> list[dict[str, str]]:
    data = order.customer_data or {}
    if not data:
        return []
    form = get_checkout_form(catalog.checkout_form)
    labels = {f['key']: f['label'] for f in (form.get('fields') or [])}
    rows: list[dict[str, str]] = []
    for key, value in data.items():
        text = str(value or '').strip()
        if text:
            rows.append({'label': labels.get(key, key), 'value': text})
    return rows


def _order_list_querystring(request, *, exclude_page: bool = True, exclude_keys: list[str] | None = None) -> str:
    params = request.GET.copy()
    if exclude_page and 'page' in params:
        params.pop('page')
    for key in exclude_keys or []:
        params.pop(key, None)
    return params.urlencode()


def _item_list_querystring(request, *, exclude_page: bool = True, exclude_keys: list[str] | None = None) -> str:
    params = request.GET.copy()
    if exclude_page and 'page' in params:
        params.pop('page')
    for key in exclude_keys or []:
        params.pop(key, None)
    return params.urlencode()


def _build_item_filter_url(request, **changes) -> str:
    params = request.GET.copy()
    params.pop('page', None)
    for key, value in changes.items():
        if value is None or value == '':
            params.pop(key, None)
        else:
            params[key] = str(value)
    qs = params.urlencode()
    return f'?{qs}' if qs else '?'


def _apply_item_filters(qs, request, *, skip: set[str] | None = None):
    skip = skip or set()
    q = (request.GET.get('q') or '').strip()
    if q and 'q' not in skip:
        qs = qs.filter(Q(title__icontains=q) | Q(short_description__icontains=q))

    item_type = (request.GET.get('type') or '').strip()
    valid_types = {choice[0] for choice in CatalogItem.ItemType.choices}
    if 'type' not in skip and 'featured' not in skip and 'flash_sale' not in skip:
        if item_type in valid_types:
            qs = qs.filter(item_type=item_type)
        elif item_type == 'showcase':
            qs = qs.filter(item_type__in=[CatalogItem.ItemType.SHOWCASE, 'portfolio'])
        elif (request.GET.get('featured') or '').strip() == '1':
            qs = qs.filter(is_featured=True)
        elif (request.GET.get('flash_sale') or '').strip() == '1':
            qs = qs.filter(is_flash_sale=True)

    status = (request.GET.get('status') or '').strip()
    if status == 'active' and 'status' not in skip:
        qs = qs.filter(is_active=True)
    elif status == 'inactive' and 'status' not in skip:
        qs = qs.filter(is_active=False)

    category_id = (request.GET.get('category') or '').strip()
    if 'category' not in skip:
        if category_id == 'none':
            qs = qs.filter(category__isnull=True)
        elif category_id.isdigit():
            qs = qs.filter(category_id=int(category_id))

    return qs


def _item_filter_context(request, scope: dict) -> dict:
    base_qs = _apply_item_filters(CatalogItem.objects.filter(**scope), request, skip={'category'})
    category_count_map = {
        row['category_id']: row['c']
        for row in base_qs.values('category_id').annotate(c=Count('id'))
    }
    uncategorized_count = base_qs.filter(category__isnull=True).count()

    current_type = (request.GET.get('type') or '').strip()
    current_status = (request.GET.get('status') or '').strip()
    current_featured = (request.GET.get('featured') or '').strip() == '1'
    current_flash_sale = (request.GET.get('flash_sale') or '').strip() == '1'
    current_category = (request.GET.get('category') or '').strip()
    current_q = (request.GET.get('q') or '').strip()

    type_base_qs = _apply_item_filters(CatalogItem.objects.filter(**scope), request, skip={'type', 'featured', 'flash_sale'})
    type_count_map = {
        row['item_type']: row['c']
        for row in type_base_qs.values('item_type').annotate(c=Count('id'))
    }
    type_showcase_count = type_count_map.get(CatalogItem.ItemType.SHOWCASE, 0) + type_count_map.get('portfolio', 0)

    type_filters = [
        {
            'key': 'all',
            'label': 'همه انواع',
            'icon': 'grid',
            'count': type_base_qs.count(),
            'url': _build_item_filter_url(request, type=None),
            'is_active': not current_type,
        },
        {
            'key': 'product',
            'label': 'محصول',
            'icon': 'bag',
            'count': type_count_map.get(CatalogItem.ItemType.PRODUCT, 0),
            'url': _build_item_filter_url(request, type='product'),
            'is_active': current_type == 'product',
        },
        {
            'key': 'download',
            'label': 'دانلود',
            'icon': 'download',
            'count': type_count_map.get(CatalogItem.ItemType.DOWNLOAD, 0),
            'url': _build_item_filter_url(request, type='download'),
            'is_active': current_type == 'download',
        },
        {
            'key': 'video',
            'label': 'ویدیو',
            'icon': 'play-btn',
            'count': type_count_map.get(CatalogItem.ItemType.VIDEO, 0),
            'url': _build_item_filter_url(request, type='video'),
            'is_active': current_type == 'video',
        },
        {
            'key': 'showcase',
            'label': 'معرفی',
            'icon': 'images',
            'count': type_showcase_count,
            'url': _build_item_filter_url(request, type='showcase'),
            'is_active': current_type == 'showcase',
        },
    ]

    featured_filter = {
        'label': 'ویژه',
        'count': type_base_qs.filter(is_featured=True).count(),
        'url_on': _build_item_filter_url(request, featured='1'),
        'url_off': _build_item_filter_url(request, featured=None),
        'is_active': current_featured,
    }

    flash_sale_filter = {
        'label': 'حراج',
        'count': type_base_qs.filter(is_flash_sale=True).count(),
        'url_on': _build_item_filter_url(request, flash_sale='1'),
        'url_off': _build_item_filter_url(request, flash_sale=None),
        'is_active': current_flash_sale,
    }

    status_base_qs = _apply_item_filters(CatalogItem.objects.filter(**scope), request, skip={'status'})
    status_filters = [
        {
            'key': 'all',
            'label': 'همه',
            'count': status_base_qs.count(),
            'url': _build_item_filter_url(request, status=None),
            'is_active': not current_status,
        },
        {
            'key': 'active',
            'label': 'فعال',
            'count': status_base_qs.filter(is_active=True).count(),
            'url': _build_item_filter_url(request, status='active'),
            'is_active': current_status == 'active',
        },
        {
            'key': 'inactive',
            'label': 'غیرفعال',
            'count': status_base_qs.filter(is_active=False).count(),
            'url': _build_item_filter_url(request, status='inactive'),
            'is_active': current_status == 'inactive',
        },
    ]

    categories = list(
        CatalogCategory.objects.filter(**scope).order_by('sort_order', 'name')
    )
    category_filters = [
        {
            'key': 'all',
            'label': 'همه دسته‌ها',
            'count': base_qs.count(),
            'image_url': '',
            'url': _build_item_filter_url(request, category=None),
            'is_active': not current_category,
        },
        {
            'key': 'none',
            'label': 'بدون دسته',
            'count': uncategorized_count,
            'image_url': '',
            'url': _build_item_filter_url(request, category='none'),
            'is_active': current_category == 'none',
        },
    ]
    for category in categories:
        category_filters.append({
            'key': str(category.pk),
            'label': category.name,
            'count': category_count_map.get(category.pk, 0),
            'image_url': category.image.url if category.image else '',
            'url': _build_item_filter_url(request, category=category.pk),
            'is_active': current_category == str(category.pk),
        })

    categories_by_id = {str(c.pk): c for c in categories}
    active_filters = []
    if current_q:
        active_filters.append({
            'label': f'جستجو: {current_q}',
            'url': _build_item_filter_url(request, q=None),
        })
    if current_type:
        type_labels = {f['key']: f['label'] for f in type_filters}
        active_filters.append({
            'label': type_labels.get(current_type, current_type),
            'url': _build_item_filter_url(request, type=None),
        })
    if current_featured:
        active_filters.append({
            'label': 'ویژه',
            'url': _build_item_filter_url(request, featured=None),
        })
    if current_flash_sale:
        active_filters.append({
            'label': 'حراج',
            'url': _build_item_filter_url(request, flash_sale=None),
        })
    if current_status == 'active':
        active_filters.append({'label': 'فعال', 'url': _build_item_filter_url(request, status=None)})
    elif current_status == 'inactive':
        active_filters.append({'label': 'غیرفعال', 'url': _build_item_filter_url(request, status=None)})
    if current_category == 'none':
        active_filters.append({'label': 'بدون دسته', 'url': _build_item_filter_url(request, category=None)})
    elif current_category and current_category in categories_by_id:
        active_filters.append({
            'label': categories_by_id[current_category].name,
            'url': _build_item_filter_url(request, category=None),
        })

    has_filters = bool(active_filters)
    active_category_label = next(
        (f['label'] for f in category_filters if f['is_active']),
        'همه دسته‌ها',
    )

    return {
        'type_filters': type_filters,
        'featured_filter': featured_filter,
        'flash_sale_filter': flash_sale_filter,
        'status_filters': status_filters,
        'category_filters': category_filters,
        'active_filters': active_filters,
        'has_item_filters': has_filters,
        'active_category_label': active_category_label,
        'current_type': current_type,
        'current_status': current_status,
        'current_featured': current_featured,
        'current_flash_sale': current_flash_sale,
        'current_category': current_category,
        'list_qs': _item_list_querystring(request),
    }


def _build_onboarding_steps(
    *,
    catalog: CatalogSettings,
    bot: BotSettings,
    scope: dict,
) -> list[dict]:
    item_count = CatalogItem.objects.filter(**scope, is_active=True).count()
    category_count = CatalogCategory.objects.filter(**scope, is_active=True).count()
    bot_ready = bool((bot.bot_token or '').strip()) and bool(resolve_public_base_url(bot).strip())
    payment_ready = catalog.is_payment_ready()

    return [
        {
            'key': 'bot',
            'done': bot_ready,
            'label': 'اتصال ربات و وب‌هوک',
            'hint': 'توکن ربات و آدرس عمومی سرور',
            'url_name': 'bot_settings',
            'url_hash': '',
        },
        {
            'key': 'template',
            'done': category_count > 0 and item_count >= 3,
            'label': 'انتخاب الگو',
            'hint': 'دسته‌ها و محصولات نمونه',
            'url_name': 'catalog_templates',
            'url_hash': '',
        },
        {
            'key': 'payment',
            'done': payment_ready,
            'label': 'ثبت روش پرداخت',
            'hint': 'بله، زرین‌پال یا ارسال به ادمین',
            'url_name': 'catalog_settings',
            'url_hash': 'sec-payment',
        },
        {
            'key': 'products',
            'done': item_count >= 3,
            'label': 'حداقل ۳ محصول',
            'hint': 'ویرایش یا افزودن محصولات',
            'url_name': 'catalog_item_list',
            'url_hash': '',
        },
        {
            'key': 'publish',
            'done': catalog.is_enabled and payment_ready,
            'label': 'انتشار فروشگاه',
            'hint': 'فعال‌سازی مینی‌اپ برای مشتریان',
            'url_name': 'catalog_settings',
            'url_hash': 'sec-status',
        },
    ]


class MiniAppPanelMixin(WorkspaceScopedMixin, PanelAccessMixin):
    """دسترسی پنل + اسکوپ workspace/platform + دسترسی مینی‌اپ."""

    def dispatch(self, request, *args, **kwargs):
        try:
            require_miniapp_access_for_request(request)
        except PermissionDenied:
            messages.error(request, 'دسترسی مینی‌اپ برای پلتفرم فعال ندارید.')
            return redirect('panel_dashboard')
        return super().dispatch(request, *args, **kwargs)

    def get_catalog_settings(self) -> CatalogSettings:
        return CatalogSettings.get_for_platform(self.get_workspace(), self.get_active_platform())


def resolve_store_template_scope(request) -> str:
    """bot | miniapp — از نام URL یا پارامتر apply_scope."""
    name = (request.resolver_match.url_name or '') if request.resolver_match else ''
    if name in ('bot_templates', 'bot_template_apply'):
        return 'bot'
    if name in ('catalog_templates', 'catalog_template_apply'):
        return 'miniapp'
    raw = (request.GET.get('scope') or request.POST.get('apply_scope') or 'miniapp').strip()
    return raw if raw in ('bot', 'miniapp') else 'miniapp'


def store_templates_list_url(scope: str) -> str:
    return reverse('bot_templates' if scope == 'bot' else 'catalog_templates')


def store_template_apply_url(scope: str, slug: str) -> str:
    if scope == 'bot':
        return reverse('bot_template_apply', kwargs={'slug': slug})
    return reverse('catalog_template_apply', kwargs={'slug': slug})


def _enrich_store_template(tpl: StoreTemplate, *, scope: str) -> None:
    tpl.industry_label = STORE_TEMPLATE_INDUSTRY_LABELS.get(tpl.industry, tpl.industry)
    data = tpl.data if isinstance(tpl.data, dict) else {}
    settings_data = data.get('settings') if isinstance(data.get('settings'), dict) else {}
    theme = settings_data.get('theme') if isinstance(settings_data.get('theme'), dict) else {}
    tpl.template_accent = (
        (theme.get('primary') or theme.get('primary_color') or '#2563eb').strip()
    )
    tpl.sample_category_count = len(data.get('categories') or [])
    tpl.sample_item_count = len(data.get('items') or [])
    hero = settings_data.get('hero_subtitle') if isinstance(settings_data, dict) else ''
    tpl.template_tagline = (hero or tpl.description or '')[:120]

    marketing = data.get('marketing') if isinstance(data.get('marketing'), dict) else {}
    campaign_count = len(marketing.get('campaigns') or [])
    if not campaign_count and isinstance(data.get('sample_campaign'), dict):
        if (data['sample_campaign'].get('title') or '').strip():
            campaign_count = 1
    tpl.sample_campaign_count = campaign_count
    tpl.has_start_flow = bool(
        isinstance(data.get('start_flow'), dict) and data.get('start_flow', {}).get('root')
    )
    tpl.has_bot_settings = bool(data.get('bot_settings'))
    tpl.has_welcome_discount = bool((marketing.get('welcome_discount') or {}).get('code'))
    tpl.has_bot_content = tpl.has_start_flow or tpl.has_bot_settings or tpl.has_welcome_discount or campaign_count > 0
    tpl.has_miniapp_content = tpl.sample_category_count > 0 or tpl.sample_item_count > 0 or bool(settings_data)
    tpl.scope_has_content = tpl.has_bot_content if scope == 'bot' else tpl.has_miniapp_content


class StoreTemplatePanelMixin(WorkspaceScopedMixin, PanelAccessMixin):
    """دسترسی پنل برای صفحهٔ قالب‌ها — مینی‌اپ فقط در scope=miniapp."""

    def dispatch(self, request, *args, **kwargs):
        if resolve_store_template_scope(request) == 'miniapp':
            try:
                require_miniapp_access_for_request(request)
            except PermissionDenied:
                messages.error(request, 'دسترسی مینی‌اپ برای پلتفرم فعال ندارید.')
                return redirect('panel_dashboard')
        return super().dispatch(request, *args, **kwargs)

    def get_template_scope(self) -> str:
        return resolve_store_template_scope(self.request)


class MiniAppFlowEngineView(MiniAppPanelMixin, TemplateView):
    template_name = 'balebot/miniapp_flow_engine.html'

    def _context(self, catalog_form=None):
        scope = self.scope_filter()
        catalog = self.get_catalog_settings()
        bot = get_bot_settings_for_request(self.request)
        items = list(
            CatalogItem.objects.filter(**scope, is_active=True)
            .prefetch_related('media')
            .order_by('-is_featured', '-updated_at')[:8]
        )
        featured = list(
            CatalogItem.objects.filter(**scope, is_active=True, is_featured=True)
            .prefetch_related('media')
            .order_by('sort_order', '-updated_at')[:8]
        )
        for item in items + featured:
            _attach_item_preview_image(item)

        categories = list(
            CatalogCategory.objects.filter(**scope, is_active=True, parent__isnull=True)
            .order_by('sort_order', 'name')[:12]
        )
        picker_categories = list(
            CatalogCategory.objects.filter(**scope, is_active=True)
            .select_related('parent')
            .order_by('sort_order', 'name')[:300]
        )
        picker_items = list(
            CatalogItem.objects.filter(**scope, is_active=True)
            .select_related('category')
            .order_by('sort_order', 'title')[:500]
        )
        picker_tags = list(
            Tag.objects.filter(**scope, is_active=True).order_by('name')[:200]
        )
        cat_json = [
            {
                'name': c.name,
                'slug': c.slug,
                'image_url': c.image.url if c.image else '',
            }
            for c in categories
        ]
        items_json = [
            {
                'title': i.title,
                'slug': i.slug,
                'price': int(i.price or 0),
                'compare_at_price': int(i.compare_at_price) if i.compare_at_price else None,
                'sales_count': int(i.sales_count or 0),
                'category_slug': i.category.slug if i.category_id else '',
                'image_url': i.preview_image.url if getattr(i, 'preview_image', None) else '',
                'is_featured': i.is_featured,
            }
            for i in items
        ]
        picker_cat_json = [
            {
                'name': (
                    f'{c.parent.name} › {c.name}' if c.parent_id and c.parent else c.name
                ),
                'slug': c.slug,
            }
            for c in picker_categories
        ]
        picker_items_json = [
            {
                'title': i.title,
                'slug': i.slug,
            }
            for i in picker_items
        ]
        picker_tags_json = [
            {
                'name': t.name,
                'slug': t.slug,
            }
            for t in picker_tags
        ]

        blocks = get_home_blocks(catalog.theme_config)
        if catalog_form and catalog_form.is_bound and not catalog_form.is_valid():
            raw = catalog_form.data.get('page_layout', '')
            blocks = sanitize_home_blocks(raw)
        elif catalog_form and catalog_form.is_bound and catalog_form.is_valid():
            blocks = catalog_form.cleaned_data.get('page_layout') or blocks

        return {
            'catalog': catalog,
            'catalog_form': catalog_form or MiniAppFlowForm(instance=catalog),
            'catalog_theme': catalog.theme_config or {},
            'catalog_labels': catalog.labels or {},
            'catalog_item_count': CatalogItem.objects.filter(**scope).count(),
            'catalog_sample_items': items,
            'catalog_featured_items': featured,
            'catalog_categories': categories,
            'catalog_categories_json': json.dumps(cat_json, ensure_ascii=False),
            'catalog_items_json': json.dumps(items_json, ensure_ascii=False),
            'catalog_picker_categories_json': json.dumps(picker_cat_json, ensure_ascii=False),
            'catalog_picker_items_json': json.dumps(picker_items_json, ensure_ascii=False),
            'catalog_picker_tags_json': json.dumps(picker_tags_json, ensure_ascii=False),
            'discount_codes_json': json.dumps(
                discount_codes_for_editor(scope['workspace'], scope['platform']),
                ensure_ascii=False,
            ),
            'home_blocks_json': json.dumps(blocks, ensure_ascii=False),
            'mini_app_url': catalog.build_mini_app_url(bot),
        }

    def get_context_data(self, **kwargs):
        return {**super().get_context_data(**kwargs), **self._context()}

    def post(self, request, *args, **kwargs):
        catalog = self.get_catalog_settings()
        form = MiniAppFlowForm(request.POST, request.FILES, instance=catalog)
        if form.is_valid():
            form.save()
            messages.success(request, 'طراحی صفحهٔ مینی‌اپ ذخیره شد.')
            return HttpResponseRedirect(reverse_lazy('catalog_flow_engine'))
        messages.error(request, 'ذخیره نشد. خطاهای فرم را برطرف کنید.')
        return self.render_to_response(self._context(catalog_form=form))


class CatalogDashboardView(MiniAppPanelMixin, TemplateView):
    template_name = 'balebot/catalog_dashboard.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        scope = self.scope_filter()
        catalog = self.get_catalog_settings()
        bot = get_bot_settings_for_request(self.request)
        theme = catalog.theme_config or {}
        payment_methods = catalog.enabled_payment_methods()

        item_count = CatalogItem.objects.filter(**scope).count()
        active_item_count = CatalogItem.objects.filter(**scope, is_active=True).count()
        category_count = CatalogCategory.objects.filter(**scope, is_active=True).count()
        order_count = CatalogOrder.objects.filter(**scope).count()
        order_pending = CatalogOrder.objects.filter(**scope, status=CatalogOrder.Status.PENDING).count()
        order_c2c_pending = CatalogOrder.objects.filter(
            **scope,
            status=CatalogOrder.Status.C2C_PENDING,
        ).count()

        setup_steps = [
            {
                'key': 'hero',
                'done': bool((catalog.hero_title or '').strip()),
                'label': 'عنوان ویترین',
                'hint': 'نام کسب‌وکار در هدر مینی‌اپ',
                'url_name': 'catalog_settings',
                'url_hash': 'sec-branding',
            },
            {
                'key': 'logo',
                'done': bool(catalog.logo),
                'label': 'لوگو',
                'hint': 'تصویر برند در هدر',
                'url_name': 'catalog_settings',
                'url_hash': 'sec-branding',
            },
            {
                'key': 'categories',
                'done': category_count > 0,
                'label': 'دسته‌بندی',
                'hint': 'حداقل یک دسته با تصویر',
                'url_name': 'catalog_category_create',
                'url_hash': '',
            },
            {
                'key': 'items',
                'done': item_count > 0,
                'label': 'آیتم',
                'hint': 'محصول، ویدیو یا فایل',
                'url_name': 'catalog_item_create',
                'url_hash': '',
            },
            {
                'key': 'payment',
                'done': catalog.is_payment_ready(),
                'label': 'روش پرداخت',
                'hint': 'زرین‌پال، پرداخت بله یا ارسال به ادمین',
                'url_name': 'catalog_settings',
                'url_hash': 'sec-payment',
            },
        ]
        setup_done = sum(1 for s in setup_steps if s['done'])
        setup_total = len(setup_steps)

        ctx.update({
            'catalog': catalog,
            'theme': theme,
            'mini_app_url': catalog.build_mini_app_url(bot),
            'catalog_public_id': catalog.public_id,
            'webhook_public_url': resolve_public_base_url(bot).rstrip('/'),
            'item_count': item_count,
            'active_item_count': active_item_count,
            'featured_count': CatalogItem.objects.filter(**scope, is_featured=True, is_active=True).count(),
            'category_count': category_count,
            'order_count': order_count,
            'order_pending': order_pending,
            'order_c2c_pending': order_c2c_pending,
            'payment_methods': payment_methods,
            'has_payment': catalog.is_payment_ready(),
            'setup_steps': setup_steps,
            'setup_done': setup_done,
            'setup_total': setup_total,
            'setup_percent': int((setup_done / setup_total) * 100) if setup_total else 0,
            'recent_orders': CatalogOrder.objects.filter(**scope).select_related('subscriber')[:8],
            'recent_items': (
                CatalogItem.objects.filter(**scope)
                .select_related('category')
                .prefetch_related('media')
                .order_by('-updated_at')[:6]
            ),
            'recent_categories': (
                CatalogCategory.objects.filter(**scope, is_active=True)
                .order_by('-updated_at')[:6]
            ),
        })
        return ctx


class CatalogSettingsView(MiniAppPanelMixin, UpdateView):
    model = CatalogSettings
    form_class = CatalogSettingsForm
    template_name = 'balebot/catalog_settings.html'

    def get_object(self, queryset=None):
        return self.get_catalog_settings()

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        bot = get_bot_settings_for_request(self.request)
        catalog = self.object
        mini_app_url = catalog.build_mini_app_url(bot)
        payment_methods = catalog.enabled_payment_methods()
        ctx['mini_app_url'] = mini_app_url
        ctx['catalog_public_id'] = catalog.public_id
        ctx['webhook_public_url'] = resolve_public_base_url(bot).rstrip('/')
        ctx['bot_username'] = ''
        if bot.has_bot_token():
            try:
                from balebot.services import messenger_api
                me = messenger_api.get_me(bot.platform, settings=bot)
                ctx['bot_username'] = (me.get('result') or {}).get('username') or ''
            except Exception:
                pass
        ctx['setup_status'] = {
            'is_enabled': catalog.is_enabled,
            'payment_ready': catalog.is_payment_ready(),
            'payment_summary': '، '.join(label for _, label in payment_methods) or 'تنظیم نشده',
            'can_purchase': catalog.can_accept_orders(),
            'has_public_url': bool(mini_app_url),
            'has_hero': bool((catalog.hero_title or '').strip()),
        }
        return ctx

    def form_valid(self, form):
        messages.success(self.request, 'تنظیمات مینی‌اپ ذخیره شد.')
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, 'ذخیره نشد. لطفاً خطاهای فرم را برطرف کنید.')
        return super().form_invalid(form)

    def get_success_url(self):
        return reverse('catalog_settings')


class CatalogCategoryListView(MiniAppPanelMixin, ListView):
    model = CatalogCategory
    template_name = 'balebot/catalog_category_list.html'
    context_object_name = 'categories'
    paginate_by = 50

    def get_queryset(self):
        return CatalogCategory.objects.filter(**self.scope_filter()).annotate(
            item_count=Count('items'),
        ).order_by('sort_order', 'name')


class CatalogCategoryCreateView(MiniAppPanelMixin, CreateView):
    model = CatalogCategory
    form_class = CatalogCategoryForm
    template_name = 'balebot/catalog_category_form.html'

    def get_form_kwargs(self):
        kw = super().get_form_kwargs()
        kw['workspace'] = self.get_workspace()
        kw['platform'] = self.get_active_platform()
        return kw

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['category_item_count'] = 0
        return ctx

    def form_valid(self, form):
        form.instance.workspace = self.get_workspace()
        form.instance.platform = self.get_active_platform()
        messages.success(self.request, 'دسته‌بندی ذخیره شد.')
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('catalog_category_list')


class CatalogCategoryUpdateView(MiniAppPanelMixin, UpdateView):
    model = CatalogCategory
    form_class = CatalogCategoryForm
    template_name = 'balebot/catalog_category_form.html'

    def get_queryset(self):
        return CatalogCategory.objects.filter(**self.scope_filter())

    def get_form_kwargs(self):
        kw = super().get_form_kwargs()
        kw['workspace'] = self.get_workspace()
        kw['platform'] = self.get_active_platform()
        return kw

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        obj = self.object
        ctx['category_item_count'] = obj.items.count() if obj and obj.pk else 0
        return ctx

    def form_valid(self, form):
        messages.success(self.request, 'دسته‌بندی به‌روزرسانی شد.')
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('catalog_category_list')


class CatalogCategoryDeleteView(MiniAppPanelMixin, View):
    http_method_names = ['post']

    def post(self, request, pk, *args, **kwargs):
        category = get_object_or_404(CatalogCategory.objects.filter(**self.scope_filter()), pk=pk)
        name = category.name
        category.delete()
        messages.success(request, f'دسته «{name}» حذف شد.')
        return redirect('catalog_category_list')


class DiscountCodeListView(MiniAppPanelMixin, ListView):
    model = DiscountCode
    template_name = 'balebot/catalog_discount_list.html'
    context_object_name = 'discount_codes'
    paginate_by = 50

    def get_queryset(self):
        return DiscountCode.objects.filter(**self.scope_filter()).order_by('-created_at')


class DiscountCodeCreateView(MiniAppPanelMixin, CreateView):
    model = DiscountCode
    form_class = DiscountCodeForm
    template_name = 'balebot/catalog_discount_form.html'

    def get_form_kwargs(self):
        kw = super().get_form_kwargs()
        kw['workspace'] = self.get_workspace()
        kw['platform'] = self.get_active_platform()
        return kw

    def form_valid(self, form):
        form.instance.workspace = self.get_workspace()
        form.instance.platform = self.get_active_platform()
        messages.success(self.request, 'کد تخفیف ذخیره شد.')
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('catalog_discount_list')


class DiscountCodeUpdateView(MiniAppPanelMixin, UpdateView):
    model = DiscountCode
    form_class = DiscountCodeForm
    template_name = 'balebot/catalog_discount_form.html'

    def get_queryset(self):
        return DiscountCode.objects.filter(**self.scope_filter())

    def get_form_kwargs(self):
        kw = super().get_form_kwargs()
        kw['workspace'] = self.get_workspace()
        kw['platform'] = self.get_active_platform()
        return kw

    def form_valid(self, form):
        messages.success(self.request, 'کد تخفیف به‌روزرسانی شد.')
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('catalog_discount_list')


class DiscountCodeDeleteView(MiniAppPanelMixin, View):
    http_method_names = ['post']

    def post(self, request, pk, *args, **kwargs):
        dc = get_object_or_404(DiscountCode.objects.filter(**self.scope_filter()), pk=pk)
        code = dc.code
        dc.delete()
        messages.success(request, f'کد «{code}» حذف شد.')
        return redirect('catalog_discount_list')


class CatalogItemListView(MiniAppPanelMixin, ListView):
    model = CatalogItem
    template_name = 'balebot/catalog_item_list.html'
    context_object_name = 'items'
    paginate_by = 24

    def get_queryset(self):
        qs = CatalogItem.objects.filter(**self.scope_filter()).select_related('category').prefetch_related('media')
        return _apply_item_filters(qs, self.request).order_by('sort_order', '-created_at')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update(_item_filter_context(self.request, self.scope_filter()))
        return ctx


class CatalogItemCreateView(MiniAppPanelMixin, CreateView):
    model = CatalogItem
    form_class = CatalogItemForm
    template_name = 'balebot/catalog_item_form.html'

    def get_form_kwargs(self):
        kw = super().get_form_kwargs()
        kw['workspace'] = self.get_workspace()
        kw['platform'] = self.get_active_platform()
        return kw

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['item_media'] = []
        ctx['item_status'] = _catalog_item_status(None, ctx.get('form'))
        ctx['item_type_guides_json'] = json.dumps(ITEM_TYPE_GUIDES, ensure_ascii=False)
        ctx['item_wizard_mode'] = True
        return ctx

    def form_valid(self, form):
        form.instance.workspace = self.get_workspace()
        form.instance.platform = self.get_active_platform()
        self.object = form.save()
        self._save_media()
        messages.success(self.request, 'آیتم ذخیره شد.')
        return redirect(self.get_success_url())

    def _save_media(self):
        files = self.request.FILES.getlist('media')
        for idx, f in enumerate(files):
            CatalogItemMedia.objects.create(
                item=self.object,
                file=f,
                media_type=detect_media_type(f.name),
                sort_order=idx,
            )

    def get_success_url(self):
        return reverse('catalog_item_list')


class CatalogItemUpdateView(MiniAppPanelMixin, UpdateView):
    model = CatalogItem
    form_class = CatalogItemForm
    template_name = 'balebot/catalog_item_form.html'

    def get_queryset(self):
        return CatalogItem.objects.filter(**self.scope_filter())

    def get_form_kwargs(self):
        kw = super().get_form_kwargs()
        kw['workspace'] = self.get_workspace()
        kw['platform'] = self.get_active_platform()
        return kw

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['item_media'] = self.object.media.all()
        ctx['item_status'] = _catalog_item_status(self.object, ctx.get('form'))
        ctx['item_type_guides_json'] = json.dumps(ITEM_TYPE_GUIDES, ensure_ascii=False)
        ctx['item_wizard_mode'] = False
        if self.object.is_group_parent():
            ctx['group_members'] = (
                self.object.group_members.select_related('child')
                .prefetch_related('child__media')
                .order_by('sort_order', 'id')
            )
            child_type = (
                CatalogItem.ItemType.VIDEO
                if self.object.item_type == CatalogItem.ItemType.COURSE
                else CatalogItem.ItemType.DOWNLOAD
            )
            member_ids = self.object.group_members.values_list('child_id', flat=True)
            ctx['available_group_children'] = CatalogItem.objects.filter(
                workspace=self.object.workspace,
                platform=self.object.platform,
                item_type=child_type,
                is_active=True,
            ).exclude(pk__in=member_ids).exclude(pk=self.object.pk).order_by('title')
        else:
            ctx['group_members'] = []
            ctx['available_group_children'] = []
        return ctx

    def form_valid(self, form):
        self.object = form.save()
        files = self.request.FILES.getlist('media')
        base = self.object.media.count()
        for idx, f in enumerate(files):
            CatalogItemMedia.objects.create(
                item=self.object,
                file=f,
                media_type=detect_media_type(f.name),
                sort_order=base + idx,
            )
        messages.success(self.request, 'آیتم به‌روزرسانی شد.')
        return redirect(self.get_success_url())

    def get_success_url(self):
        if self.object and self.object.pk:
            return reverse('catalog_item_edit', kwargs={'pk': self.object.pk})
        return reverse('catalog_item_list')


class CatalogItemDeleteView(MiniAppPanelMixin, View):
    http_method_names = ['post']

    def post(self, request, pk, *args, **kwargs):
        item = get_object_or_404(CatalogItem.objects.filter(**self.scope_filter()), pk=pk)
        title = item.title
        item.delete()
        messages.success(request, f'آیتم «{title}» حذف شد.')
        return redirect('catalog_item_list')


def _maybe_delete_orphan_group_child(child: CatalogItem) -> None:
    """اگر آیتم فقط برای یک دوره/پکیج ساخته شده و دیگر عضوی ندارد، حذفش کن."""
    if child.member_of_groups.exists():
        return
    if child.item_type not in (
        CatalogItem.ItemType.VIDEO,
        CatalogItem.ItemType.DOWNLOAD,
    ):
        return
    if child.sale_mode != CatalogItem.SaleMode.REQUEST_ONLY:
        return
    child.delete()


def _update_child_video_media(child: CatalogItem, *, title: str, video_file=None, external_url: str = '') -> None:
    media = child.media.filter(media_type=CatalogItemMedia.MediaType.VIDEO).first()
    if video_file:
        if media:
            if media.file:
                media.file.delete(save=False)
            media.file = video_file
            media.external_url = ''
            media.title = title or media.title
            media.save()
        else:
            CatalogItemMedia.objects.create(
                item=child,
                file=video_file,
                media_type=detect_media_type(video_file.name),
                title=title,
            )
    elif external_url:
        if media:
            if media.file:
                media.file.delete(save=False)
            media.file = None
            media.external_url = external_url
            media.title = title or media.title
            media.save()
        else:
            CatalogItemMedia.objects.create(
                item=child,
                external_url=external_url,
                media_type=CatalogItemMedia.MediaType.VIDEO,
                title=title,
            )


def _update_child_download_media(child: CatalogItem, *, lesson_file=None, external_url: str = '') -> None:
    if lesson_file:
        if child.download_file:
            child.download_file.delete(save=False)
        child.download_file = lesson_file
        child.download_link = ''
        child.save(update_fields=['download_file', 'download_link'])
    elif external_url:
        if child.download_file:
            child.download_file.delete(save=False)
        child.download_file = None
        child.download_link = external_url
        child.save(update_fields=['download_file', 'download_link'])


class CatalogItemMediaDeleteView(MiniAppPanelMixin, View):
    def post(self, request, pk, media_pk):
        item = get_object_or_404(CatalogItem, pk=pk, **self.scope_filter())
        media = get_object_or_404(CatalogItemMedia, pk=media_pk, item=item)
        media.delete()
        messages.success(request, 'رسانه حذف شد.')
        return redirect('catalog_item_edit', pk=pk)


class CatalogItemMemberAddView(MiniAppPanelMixin, View):
    http_method_names = ['post']

    def post(self, request, pk):
        item = get_object_or_404(CatalogItem.objects.filter(**self.scope_filter()), pk=pk)
        if not item.is_group_parent():
            messages.error(request, 'فقط دوره یا پکیج می‌تواند عضو داشته باشد.')
            return redirect('catalog_item_edit', pk=pk)
        child_id = request.POST.get('child_id')
        if not child_id:
            messages.error(request, 'یک آیتم برای افزودن انتخاب کنید.')
            return redirect('catalog_item_edit', pk=pk)
        child = get_object_or_404(
            CatalogItem,
            pk=child_id,
            workspace=item.workspace,
            platform=item.platform,
            is_active=True,
        )
        expected_type = (
            CatalogItem.ItemType.VIDEO
            if item.item_type == CatalogItem.ItemType.COURSE
            else CatalogItem.ItemType.DOWNLOAD
        )
        if child.normalized_item_type() != expected_type:
            messages.error(request, f'نوع آیتم انتخاب‌شده باید {expected_type} باشد.')
            return redirect('catalog_item_edit', pk=pk)
        sort_order = item.group_members.count()
        CatalogItemMember.objects.get_or_create(
            parent=item,
            child=child,
            defaults={'sort_order': sort_order},
        )
        messages.success(request, f'«{child.title}» اضافه شد.')
        return redirect('catalog_item_edit', pk=pk)


class CatalogItemMemberDeleteView(MiniAppPanelMixin, View):
    http_method_names = ['post']

    def post(self, request, pk, member_pk):
        item = get_object_or_404(CatalogItem.objects.filter(**self.scope_filter()), pk=pk)
        member = get_object_or_404(CatalogItemMember, pk=member_pk, parent=item)
        child = member.child
        member.delete()
        _maybe_delete_orphan_group_child(child)
        messages.success(request, 'عضو حذف شد.')
        return redirect('catalog_item_edit', pk=pk)


class CatalogItemMemberUpdateView(MiniAppPanelMixin, View):
    http_method_names = ['post']

    def post(self, request, pk, member_pk):
        parent = get_object_or_404(CatalogItem.objects.filter(**self.scope_filter()), pk=pk)
        member = get_object_or_404(CatalogItemMember, pk=member_pk, parent=parent)
        child = member.child

        title = (request.POST.get('lesson_title') or '').strip()
        if title:
            child.title = title
            child.save(update_fields=['title'])

        member.is_preview = request.POST.get('is_preview') == 'on'
        member.save(update_fields=['is_preview'])

        external_url = (request.POST.get('lesson_external_url') or '').strip()
        video_file = request.FILES.get('lesson_video')
        lesson_file = request.FILES.get('lesson_file')

        if parent.item_type == CatalogItem.ItemType.COURSE:
            if video_file or external_url:
                _update_child_video_media(
                    child,
                    title=title or child.title,
                    video_file=video_file,
                    external_url=external_url,
                )
        elif lesson_file or external_url:
            _update_child_download_media(child, lesson_file=lesson_file, external_url=external_url)

        messages.success(request, f'«{child.title}» به‌روزرسانی شد.')
        return redirect('catalog_item_edit', pk=pk)


class CatalogItemExternalMediaCreateView(MiniAppPanelMixin, View):
    http_method_names = ['post']

    def post(self, request, pk):
        item = get_object_or_404(CatalogItem.objects.filter(**self.scope_filter()), pk=pk)
        external_url = (request.POST.get('external_url') or '').strip()
        title = (request.POST.get('media_title') or '').strip()
        media_type = (request.POST.get('media_type') or 'video').strip()
        if not external_url:
            messages.error(request, 'لینک رسانه را وارد کنید.')
            return redirect('catalog_item_edit', pk=pk)
        if media_type not in (
            CatalogItemMedia.MediaType.VIDEO,
            CatalogItemMedia.MediaType.FILE,
            CatalogItemMedia.MediaType.IMAGE,
        ):
            media_type = CatalogItemMedia.MediaType.VIDEO
        sort_order = item.media.count()
        CatalogItemMedia.objects.create(
            item=item,
            external_url=external_url,
            media_type=media_type,
            title=title,
            sort_order=sort_order,
        )
        messages.success(request, 'رسانه با لینک خارجی اضافه شد.')
        return redirect('catalog_item_edit', pk=pk)


class CatalogItemMemberCreateWithUploadView(MiniAppPanelMixin, View):
    http_method_names = ['post']

    def post(self, request, pk):
        from balebot.services.slug_utils import resolve_model_slug

        parent = get_object_or_404(CatalogItem.objects.filter(**self.scope_filter()), pk=pk)
        if not parent.is_group_parent():
            messages.error(request, 'فقط دوره یا پکیج می‌تواند عضو داشته باشد.')
            return redirect('catalog_item_edit', pk=pk)

        title = (request.POST.get('lesson_title') or '').strip()
        if not title:
            messages.error(request, 'عنوان قسمت را وارد کنید.')
            return redirect('catalog_item_edit', pk=pk)

        external_url = (request.POST.get('lesson_external_url') or '').strip()
        video_file = request.FILES.get('lesson_video')
        lesson_file = request.FILES.get('lesson_file')

        if parent.item_type == CatalogItem.ItemType.COURSE:
            if not video_file and not external_url:
                messages.error(request, 'فایل ویدیو را آپلود کنید یا لینک ویدیو (مستقیم یا اپارات) وارد کنید.')
                return redirect('catalog_item_edit', pk=pk)
            child_type = CatalogItem.ItemType.VIDEO
        else:
            if not lesson_file and not external_url:
                messages.error(request, 'فایل را آپلود کنید یا لینک مستقیم وارد کنید.')
                return redirect('catalog_item_edit', pk=pk)
            child_type = CatalogItem.ItemType.DOWNLOAD

        slug = resolve_model_slug(
            CatalogItem,
            title,
            workspace=parent.workspace,
            platform=parent.platform,
            fallback='lesson',
            max_length=220,
        )
        child = CatalogItem.objects.create(
            workspace=parent.workspace,
            platform=parent.platform,
            title=title,
            slug=slug,
            item_type=child_type,
            sale_mode=CatalogItem.SaleMode.REQUEST_ONLY,
            is_active=True,
        )

        if parent.item_type == CatalogItem.ItemType.COURSE:
            if video_file:
                CatalogItemMedia.objects.create(
                    item=child,
                    file=video_file,
                    media_type=detect_media_type(video_file.name),
                    title=title,
                )
            elif external_url:
                CatalogItemMedia.objects.create(
                    item=child,
                    external_url=external_url,
                    media_type=CatalogItemMedia.MediaType.VIDEO,
                    title=title,
                )
        else:
            if lesson_file:
                child.download_file = lesson_file
                child.save(update_fields=['download_file'])
            elif external_url:
                child.download_link = external_url
                child.save(update_fields=['download_link'])

        sort_order = parent.group_members.count()
        is_preview = request.POST.get('is_preview') == 'on'
        CatalogItemMember.objects.create(
            parent=parent,
            child=child,
            sort_order=sort_order,
            is_preview=is_preview,
        )
        messages.success(request, f'«{title}» با موفقیت اضافه شد.')
        return redirect('catalog_item_edit', pk=pk)


class CatalogOrderListView(MiniAppPanelMixin, ListView):
    model = CatalogOrder
    template_name = 'balebot/catalog_order_list.html'
    context_object_name = 'orders'
    paginate_by = 25

    def get_queryset(self):
        scope = self.scope_filter()
        qs = (
            CatalogOrder.objects.filter(**scope)
            .select_related('subscriber')
            .annotate(line_count=Count('lines'))
        )
        status = (self.request.GET.get('status') or '').strip()
        if status:
            qs = qs.filter(status=status)

        payment = (self.request.GET.get('payment') or '').strip()
        if payment:
            qs = qs.filter(payment_method=payment)

        q = (self.request.GET.get('q') or '').strip()
        if q:
            filters = (
                Q(subscriber__first_name__icontains=q)
                | Q(subscriber__last_name__icontains=q)
                | Q(subscriber__username__icontains=q)
                | Q(subscriber__phone_number__icontains=q)
                | Q(note__icontains=q)
                | Q(admin_note__icontains=q)
                | Q(customer_note__icontains=q)
                | Q(recipient_name__icontains=q)
                | Q(recipient_phone__icontains=q)
                | Q(recipient_address__icontains=q)
                | Q(tracking_code__icontains=q)
                | Q(payment_charge_id__icontains=q)
                | Q(discount_code__icontains=q)
                | Q(public_token__icontains=q)
            )
            if q.isdigit():
                filters |= Q(pk=int(q)) | Q(subscriber__messenger_user_id=int(q))
            qs = qs.filter(filters)

        return qs.order_by('-created_at')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        scope = self.scope_filter()
        counts = _order_status_counts(scope)
        ctx['order_counts'] = counts
        ctx['order_revenue'] = (
            CatalogOrder.objects.filter(**scope, status=CatalogOrder.Status.PAID)
            .aggregate(total=Sum('total_amount'))['total'] or 0
        )
        ctx['current_status'] = (self.request.GET.get('status') or '').strip()
        ctx['current_payment'] = (self.request.GET.get('payment') or '').strip()
        ctx['payment_method_choices'] = CatalogSettings.PaymentMethod.choices
        ctx['list_qs'] = _order_list_querystring(self.request)
        ctx['filter_base_qs'] = _order_list_querystring(self.request, exclude_keys=['payment'])
        return ctx


class CatalogOrderDetailView(MiniAppPanelMixin, DetailView):
    model = CatalogOrder
    template_name = 'balebot/catalog_order_detail.html'
    context_object_name = 'order'

    def get_queryset(self):
        return (
            CatalogOrder.objects.filter(**self.scope_filter())
            .select_related('subscriber')
            .prefetch_related('lines__item')
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        catalog = self.get_catalog_settings()
        order = self.object
        ctx['customer_rows'] = _order_customer_rows(catalog, order)
        ctx['payment_method_label'] = _order_payment_label(order.payment_method)
        ctx['update_form'] = CatalogOrderUpdateForm(
            initial={
                'status': order.status,
                'fulfillment_status': order.fulfillment_status,
                'tracking_code': order.tracking_code,
                'admin_note': order.admin_note,
                'note': order.note,
            },
        )
        ctx['line_count'] = order.lines.count()
        ctx['items_subtotal'] = sum(line.line_total for line in order.lines.all())
        return ctx


class CatalogOrderUpdateView(MiniAppPanelMixin, View):
    def post(self, request, pk):
        order = get_object_or_404(CatalogOrder, pk=pk, **self.scope_filter())
        catalog = self.get_catalog_settings()
        form = CatalogOrderUpdateForm(request.POST)
        if not form.is_valid():
            messages.error(request, 'ذخیره نشد. وضعیت را بررسی کنید.')
            return redirect('catalog_order_detail', pk=pk)

        old_status = order.status
        old_fulfillment = order.fulfillment_status
        order.status = form.cleaned_data['status']
        order.fulfillment_status = form.cleaned_data['fulfillment_status']
        order.tracking_code = (form.cleaned_data.get('tracking_code') or '')[:64]
        order.admin_note = form.cleaned_data.get('admin_note') or ''
        order.note = form.cleaned_data['note']
        order.save(
            update_fields=[
                'status',
                'fulfillment_status',
                'tracking_code',
                'admin_note',
                'note',
                'updated_at',
            ],
        )

        if order.status == CatalogOrder.Status.PAID:
            from balebot.services.catalog_payment import mark_order_paid

            mark_order_paid(order)
            desired_fulfillment = form.cleaned_data['fulfillment_status']
            if order.fulfillment_status != desired_fulfillment:
                order.fulfillment_status = desired_fulfillment
                order.save(update_fields=['fulfillment_status', 'updated_at'])

        from balebot.services.order_fulfillment import notify_fulfillment_status_change

        if old_fulfillment != order.fulfillment_status:
            notify_fulfillment_status_change(
                order,
                catalog,
                old_status=old_fulfillment,
                new_status=order.fulfillment_status,
            )

        if old_status != order.status:
            messages.success(
                request,
                f'وضعیت پرداخت سفارش #{order.pk} به «{order.get_status_display()}» تغییر کرد.',
            )
        elif old_fulfillment != order.fulfillment_status:
            messages.success(
                request,
                f'وضعیت ارسال سفارش #{order.pk} به «{order.get_fulfillment_status_display()}» تغییر کرد.',
            )
        else:
            messages.success(request, 'سفارش ذخیره شد.')
        return redirect('catalog_order_detail', pk=pk)


class CatalogOrderDeleteView(MiniAppPanelMixin, View):
    http_method_names = ['post']

    def post(self, request, pk, *args, **kwargs):
        order = get_object_or_404(CatalogOrder.objects.filter(**self.scope_filter()), pk=pk)
        order_id = order.pk
        order.delete()
        messages.success(request, f'سفارش #{order_id} حذف شد.')
        return redirect('catalog_order_list')


class StoreTemplateListView(StoreTemplatePanelMixin, ListView):
    model = StoreTemplate
    template_name = 'balebot/catalog_templates.html'
    context_object_name = 'templates'

    def get_queryset(self):
        return StoreTemplate.objects.filter(is_active=True).order_by('sort_order', 'name')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        scope = self.get_template_scope()
        ctx['template_scope'] = scope
        ctx['industry_labels'] = STORE_TEMPLATE_INDUSTRY_LABELS
        templates = list(ctx['templates'])
        for tpl in templates:
            _enrich_store_template(tpl, scope=scope)
        ctx['templates'] = templates
        industries = sorted({tpl.industry for tpl in templates})
        ctx['industries'] = [
            {
                'key': key,
                'label': STORE_TEMPLATE_INDUSTRY_LABELS.get(key, key),
            }
            for key in industries
        ]
        ctx['can_manage_store_templates'] = self.request.user.is_superuser
        ctx['templates_list_url'] = store_templates_list_url(scope)
        ctx['template_apply_url_name'] = 'bot_template_apply' if scope == 'bot' else 'catalog_template_apply'
        if ctx['can_manage_store_templates']:
            ctx['store_template_active_count'] = StoreTemplate.objects.filter(is_active=True).count()
            ctx['store_template_total_count'] = StoreTemplate.objects.count()
        return ctx


class StoreTemplateApplyView(StoreTemplatePanelMixin, View):
    def post(self, request, slug):
        template = get_object_or_404(StoreTemplate, slug=slug, is_active=True)
        scope = resolve_store_template_scope(request)
        mode = (request.POST.get('mode') or 'append').strip()
        if mode not in ('append', 'replace'):
            mode = 'append'
        list_url = store_templates_list_url(scope)
        try:
            stats = apply_template(
                template,
                self.get_workspace(),
                self.get_active_platform(),
                mode=mode,
                scope=scope,
            )
        except Exception as exc:
            messages.error(request, f'اعمال الگو ناموفق بود: {exc}')
            return redirect(list_url)

        if scope == 'bot':
            parts = []
            if stats.get('bot_flow_applied'):
                parts.append('منوی /start')
            if stats.get('bot_settings_applied'):
                parts.append('تنظیمات ربات')
            if stats.get('discount_created'):
                parts.append(f'{stats["discount_created"]} کد تخفیف')
            if stats.get('campaign_created'):
                parts.append(f'{stats["campaign_created"]} کمپین نمونه')
            detail = '، '.join(parts) if parts else 'بدون تغییر قابل‌توجه'
            messages.success(
                request,
                f'بخش ربات از الگوی «{template.name}» اعمال شد — {detail}.',
            )
            return redirect('bot_flow_engine')

        messages.success(
            request,
            (
                f'بخش مینی‌اپ از الگوی «{template.name}» اعمال شد — '
                f'{stats["categories_created"]} دسته، '
                f'{stats["items_created"]} محصول.'
            ),
        )
        return redirect('catalog_onboarding')


class StoreTemplateUpdateView(SuperuserRequiredMixin, PanelAccessMixin, View):
    """ویرایش متادیتای الگو (نام، صنف، توضیح، ترتیب، وضعیت)."""

    http_method_names = ['post']

    def post(self, request, slug):
        template = get_object_or_404(StoreTemplate, slug=slug)
        name = (request.POST.get('name') or '').strip()
        industry = (request.POST.get('industry') or '').strip().lower()
        description = (request.POST.get('description') or '').strip()
        sort_order_raw = (request.POST.get('sort_order') or '').strip()
        is_active = (request.POST.get('is_active') or '').strip() == '1'
        scope = (request.POST.get('scope') or 'miniapp').strip()
        if scope not in ('bot', 'miniapp'):
            scope = 'miniapp'

        if not name:
            messages.error(request, 'نام قالب نمی‌تواند خالی باشد.')
            return redirect(store_templates_list_url(scope))
        if not industry:
            messages.error(request, 'صنف قالب را وارد کنید.')
            return redirect(store_templates_list_url(scope))
        sort_order = template.sort_order
        if sort_order_raw:
            try:
                sort_order = int(sort_order_raw)
            except ValueError:
                messages.error(request, 'ترتیب باید عدد باشد.')
                return redirect(store_templates_list_url(scope))

        template.name = name[:120]
        template.industry = industry[:60]
        template.description = description[:255]
        template.sort_order = sort_order
        template.is_active = is_active
        template.save(update_fields=['name', 'industry', 'description', 'sort_order', 'is_active', 'updated_at'])
        messages.success(request, f'قالب «{template.name}» به‌روزرسانی شد.')
        return redirect(store_templates_list_url(scope))


class StoreTemplateExportAllView(SuperuserRequiredMixin, PanelAccessMixin, View):
    """دانلود همهٔ الگوها به‌صورت JSON."""

    def get(self, request):
        include_inactive = (request.GET.get('all') or '').strip() in ('1', 'true', 'yes')
        qs = StoreTemplate.objects.order_by('sort_order', 'name')
        if not include_inactive:
            qs = qs.filter(is_active=True)
        payload = build_export_bundle(qs)
        body = json.dumps(payload, ensure_ascii=False, indent=2)
        response = HttpResponse(body, content_type='application/json; charset=utf-8')
        suffix = 'all' if include_inactive else 'active'
        response['Content-Disposition'] = f'attachment; filename="store-templates-{suffix}.json"'
        return response


class StoreTemplateExportView(SuperuserRequiredMixin, PanelAccessMixin, View):
    """دانلود یک الگو به‌صورت JSON."""

    def get(self, request, slug):
        template = get_object_or_404(StoreTemplate, slug=slug)
        payload = build_single_export(template)
        body = json.dumps(payload, ensure_ascii=False, indent=2)
        response = HttpResponse(body, content_type='application/json; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="store-template-{slug}.json"'
        return response


class StoreTemplateImportView(SuperuserRequiredMixin, PanelAccessMixin, View):
    """آپلود JSON الگوها — ایجاد یا به‌روزرسانی بر اساس slug."""

    def get(self, request):
        return redirect('catalog_templates')

    def post(self, request):
        upload = request.FILES.get('file')
        if not upload:
            messages.error(request, 'فایل JSON را انتخاب کنید.')
            return redirect('catalog_templates')

        if upload.size > 5 * 1024 * 1024:
            messages.error(request, 'حداکثر حجم فایل ۵ مگابایت است.')
            return redirect('catalog_templates')

        name = (upload.name or '').lower()
        if not name.endswith('.json'):
            messages.error(request, 'فقط فایل JSON پذیرفته می‌شود.')
            return redirect('catalog_templates')

        try:
            content = upload.read()
            rows = parse_store_template_import_file(content)
            deactivate_missing = (request.POST.get('deactivate_missing') or '').strip() == 'on'
            stats = import_store_templates(rows, deactivate_missing=deactivate_missing)
        except StoreTemplateImportError as exc:
            messages.error(request, str(exc))
            return redirect('catalog_templates')
        except Exception as exc:
            messages.error(request, f'ایمپورت ناموفق: {exc}')
            return redirect('catalog_templates')

        parts = [
            f'{stats["created"]} الگوی جدید',
            f'{stats["updated"]} به‌روزرسانی',
        ]
        if stats.get('deactivated'):
            parts.append(f'{stats["deactivated"]} غیرفعال‌شده')
        messages.success(request, 'ایمپورت انجام شد: ' + '، '.join(parts) + '.')
        return redirect('catalog_templates')


class StoreTemplateDeleteView(SuperuserRequiredMixin, PanelAccessMixin, View):
    """حذف دائمی یک الگو."""

    def get(self, request, slug):
        return redirect('catalog_templates')

    def post(self, request, slug):
        try:
            name = delete_store_template(slug)
        except StoreTemplateImportError as exc:
            messages.error(request, str(exc))
            return redirect('catalog_templates')
        messages.success(request, f'الگوی «{name}» حذف شد.')
        return redirect('catalog_templates')


class StoreTemplateDeleteAllView(SuperuserRequiredMixin, PanelAccessMixin, View):
    """حذف دسته‌جمعی الگوها."""

    def get(self, request):
        return redirect('catalog_templates')

    def post(self, request):
        scope = (request.POST.get('scope') or 'active').strip()
        if scope not in ('active', 'all'):
            scope = 'active'
        count = delete_all_store_templates(include_inactive=(scope == 'all'))
        if count:
            label = 'همه الگوها' if scope == 'all' else 'الگوهای فعال'
            messages.success(request, f'{count} مورد از {label} حذف شد.')
        else:
            messages.info(request, 'الگویی برای حذف یافت نشد.')
        return redirect('catalog_templates')


class CatalogBulkImportView(MiniAppPanelMixin, TemplateView):
    template_name = 'balebot/catalog_bulk_import.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['preview_rows'] = self.request.session.pop('bulk_import_preview', None)
        ctx['preview_errors'] = self.request.session.pop('bulk_import_errors', None)
        return ctx

    def post(self, request, *args, **kwargs):
        action = (request.POST.get('action') or 'preview').strip()
        if action == 'import':
            rows = request.session.get('bulk_import_preview') or []
            if not rows:
                messages.error(request, 'ابتدا فایل را پیش‌نمایش کنید.')
                return redirect('catalog_bulk_import')
            stats = import_rows(self.get_catalog_settings(), rows)
            request.session.pop('bulk_import_preview', None)
            request.session.pop('bulk_import_errors', None)
            messages.success(
                request,
                f'{stats["items_created"]} محصول و {stats["categories_created"]} دسته جدید ثبت شد.',
            )
            return redirect('catalog_item_list')

        upload = request.FILES.get('file')
        if not upload:
            messages.error(request, 'فایلی انتخاب نشده است.')
            return redirect('catalog_bulk_import')
        try:
            raw_rows = parse_import_file(upload.name, upload.read())
            valid, errors = preview_import_rows(raw_rows)
        except Exception as exc:
            messages.error(request, str(exc))
            return redirect('catalog_bulk_import')
        request.session['bulk_import_preview'] = valid
        request.session['bulk_import_errors'] = errors
        if not valid:
            messages.warning(request, 'هیچ ردیف معتبری یافت نشد.')
        else:
            messages.info(request, f'{len(valid)} ردیف آماده ثبت است. پیش‌نمایش را بررسی کنید.')
        return redirect('catalog_bulk_import')


class CatalogBulkImportSampleView(MiniAppPanelMixin, View):
    def get(self, request):
        from django.http import HttpResponse

        content = build_sample_workbook()
        response = HttpResponse(
            content,
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )
        response['Content-Disposition'] = 'attachment; filename="catalog-import-sample.xlsx"'
        return response


class CatalogOnboardingView(MiniAppPanelMixin, TemplateView):
    template_name = 'balebot/catalog_onboarding.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        scope = self.scope_filter()
        catalog = self.get_catalog_settings()
        bot = get_bot_settings_for_request(self.request)
        steps = _build_onboarding_steps(catalog=catalog, bot=bot, scope=scope)
        done = sum(1 for s in steps if s['done'])
        total = len(steps)
        ctx.update({
            'catalog': catalog,
            'bot': bot,
            'mini_app_url': catalog.build_mini_app_url(bot),
            'onboarding_steps': steps,
            'onboarding_done': done,
            'onboarding_total': total,
            'onboarding_percent': int((done / total) * 100) if total else 0,
        })
        return ctx
