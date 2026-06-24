"""ویوهای پنل مدیریت فروشگاه مینی‌اپ."""

from __future__ import annotations

import json

from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.db.models import Count, Q, Sum
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.views import View
from django.views.generic import CreateView, DetailView, ListView, TemplateView, UpdateView

from balebot.forms_catalog import (
    CatalogCategoryForm,
    CatalogItemForm,
    CatalogOrderUpdateForm,
    CatalogSettingsForm,
    MiniAppFlowForm,
)
from balebot.models import (
    BotSettings,
    CatalogCategory,
    CatalogItem,
    CatalogItemMedia,
    CatalogOrder,
    CatalogSettings,
    StoreTemplate,
)
from balebot.platform import get_bot_settings_for_request, require_miniapp_access_for_request
from balebot.services.catalog_item_types import ITEM_TYPE_GUIDES, get_item_type_guide
from balebot.services.catalog_media import detect_media_type
from balebot.services.catalog_page_layout import get_home_blocks, sanitize_home_blocks
from balebot.services.checkout_form import get_checkout_form
from balebot.services.public_url import resolve_public_base_url
from balebot.services.store_template import apply_template
from balebot.services.catalog_bulk_import import (
    build_sample_workbook,
    import_rows,
    parse_import_file,
    preview_import_rows,
)
from balebot.views_panel import PanelAccessMixin, WorkspaceScopedMixin

STORE_TEMPLATE_INDUSTRY_LABELS = {
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
            else (f'{price:,} ریال' if price else '—')
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
                'price': int(i.price or 0),
                'image_url': i.preview_image.url if getattr(i, 'preview_image', None) else '',
                'is_featured': i.is_featured,
            }
            for i in items
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

    def form_valid(self, form):
        messages.success(self.request, 'دسته‌بندی به‌روزرسانی شد.')
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('catalog_category_list')


class CatalogItemListView(MiniAppPanelMixin, ListView):
    model = CatalogItem
    template_name = 'balebot/catalog_item_list.html'
    context_object_name = 'items'
    paginate_by = 30

    def get_queryset(self):
        qs = CatalogItem.objects.filter(**self.scope_filter()).select_related('category').prefetch_related('media')
        q = (self.request.GET.get('q') or '').strip()
        if q:
            qs = qs.filter(Q(title__icontains=q) | Q(short_description__icontains=q))
        return qs.order_by('sort_order', '-created_at')


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
        return reverse('catalog_item_list')


class CatalogItemMediaDeleteView(MiniAppPanelMixin, View):
    def post(self, request, pk, media_pk):
        item = get_object_or_404(CatalogItem, pk=pk, **self.scope_filter())
        media = get_object_or_404(CatalogItemMedia, pk=media_pk, item=item)
        media.delete()
        messages.success(request, 'رسانه حذف شد.')
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

        if (
            order.status == CatalogOrder.Status.PAID
            and old_status != CatalogOrder.Status.PAID
        ):
            from balebot.services.catalog_payment import mark_order_paid

            mark_order_paid(order)
            if form.cleaned_data['fulfillment_status'] != CatalogOrder.FulfillmentStatus.PAID:
                order.fulfillment_status = form.cleaned_data['fulfillment_status']
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


class StoreTemplateListView(MiniAppPanelMixin, ListView):
    model = StoreTemplate
    template_name = 'balebot/catalog_templates.html'
    context_object_name = 'templates'

    def get_queryset(self):
        return StoreTemplate.objects.filter(is_active=True).order_by('sort_order', 'name')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['industry_labels'] = STORE_TEMPLATE_INDUSTRY_LABELS
        templates = list(ctx['templates'])
        for tpl in templates:
            tpl.industry_label = STORE_TEMPLATE_INDUSTRY_LABELS.get(tpl.industry, tpl.industry)
        ctx['templates'] = templates
        industries = sorted({tpl.industry for tpl in templates})
        ctx['industries'] = [
            {
                'key': key,
                'label': STORE_TEMPLATE_INDUSTRY_LABELS.get(key, key),
            }
            for key in industries
        ]
        return ctx


class StoreTemplateApplyView(MiniAppPanelMixin, View):
    def post(self, request, slug):
        template = get_object_or_404(StoreTemplate, slug=slug, is_active=True)
        mode = (request.POST.get('mode') or 'append').strip()
        if mode not in ('append', 'replace'):
            mode = 'append'
        try:
            stats = apply_template(
                template,
                self.get_workspace(),
                self.get_active_platform(),
                mode=mode,
            )
        except Exception as exc:
            messages.error(request, f'اعمال الگو ناموفق بود: {exc}')
            return redirect('catalog_templates')

        messages.success(
            request,
            (
                f'الگوی «{template.name}» اعمال شد — '
                f'{stats["categories_created"]} دسته، '
                f'{stats["items_created"]} محصول'
                + (f'، {stats["campaign_created"]} کمپین نمونه' if stats['campaign_created'] else '')
                + (f'، {stats["discount_created"]} کد تخفیف' if stats.get('discount_created') else '')
                + '.'
            ),
        )
        return redirect('catalog_onboarding')


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
