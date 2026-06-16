"""ویوهای پنل مدیریت فروشگاه مینی‌اپ."""

from __future__ import annotations

import json

from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.db.models import Count, Q
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.views import View
from django.views.generic import CreateView, DetailView, ListView, TemplateView, UpdateView

from balebot.forms_catalog import (
    CatalogCategoryForm,
    CatalogItemForm,
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
)
from balebot.platform import get_bot_settings_for_request, require_miniapp_access_for_request
from balebot.services.catalog_media import detect_media_type
from balebot.services.catalog_page_layout import get_home_blocks, sanitize_home_blocks
from balebot.services.public_url import resolve_public_base_url
from balebot.views_panel import PanelAccessMixin, WorkspaceScopedMixin


def _attach_item_preview_image(item: CatalogItem) -> None:
    img = next(
        (m for m in item.media.all() if m.media_type == CatalogItemMedia.MediaType.IMAGE),
        None,
    )
    item.preview_image = img.file if img else None


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
            messages.success(request, 'ظاهر فروشگاه مینی‌اپ ذخیره شد.')
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
                'label': 'عنوان فروشگاه',
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
                'done': bool(payment_methods),
                'label': 'روش پرداخت',
                'hint': 'زرین‌پال یا ارسال به ادمین',
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
            'has_payment': bool(payment_methods),
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
        ctx['mini_app_url'] = catalog.build_mini_app_url(bot)
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
    paginate_by = 30

    def get_queryset(self):
        qs = CatalogOrder.objects.filter(**self.scope_filter()).select_related('subscriber')
        status = (self.request.GET.get('status') or '').strip()
        if status:
            qs = qs.filter(status=status)
        return qs.order_by('-created_at')


class CatalogOrderDetailView(MiniAppPanelMixin, DetailView):
    model = CatalogOrder
    template_name = 'balebot/catalog_order_detail.html'
    context_object_name = 'order'

    def get_queryset(self):
        return CatalogOrder.objects.filter(**self.scope_filter()).prefetch_related('lines')
