"""ویوهای پنل مدیریت فروشگاه مینی‌اپ."""

from __future__ import annotations

from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.db.models import Count, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.views import View
from django.views.generic import CreateView, DetailView, ListView, TemplateView, UpdateView

from balebot.forms_catalog import CatalogCategoryForm, CatalogItemForm, CatalogSettingsForm
from balebot.models import (
    BotSettings,
    CatalogCategory,
    CatalogItem,
    CatalogItemImage,
    CatalogOrder,
    CatalogSettings,
)
from balebot.platform import get_bot_settings_for_request, require_miniapp_access_for_request
from balebot.views_panel import PanelAccessMixin, WorkspaceScopedMixin


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


class CatalogDashboardView(MiniAppPanelMixin, TemplateView):
    template_name = 'balebot/catalog_dashboard.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        scope = self.scope_filter()
        catalog = self.get_catalog_settings()
        bot = get_bot_settings_for_request(self.request)
        ctx['catalog'] = catalog
        ctx['mini_app_url'] = catalog.build_mini_app_url(bot)
        ctx['catalog_public_id'] = catalog.public_id
        ctx['webhook_public_url'] = (bot.webhook_public_url or '').strip()
        ctx['item_count'] = CatalogItem.objects.filter(**scope).count()
        ctx['category_count'] = CatalogCategory.objects.filter(**scope, is_active=True).count()
        ctx['order_count'] = CatalogOrder.objects.filter(**scope).count()
        ctx['order_pending'] = CatalogOrder.objects.filter(
            **scope,
            status=CatalogOrder.Status.PENDING,
        ).count()
        ctx['recent_orders'] = CatalogOrder.objects.filter(**scope).select_related('subscriber')[:10]
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
        ctx['webhook_public_url'] = (bot.webhook_public_url or '').strip()
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
        qs = CatalogItem.objects.filter(**self.scope_filter()).select_related('category')
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
        self._save_images()
        messages.success(self.request, 'آیتم ذخیره شد.')
        return redirect(self.get_success_url())

    def _save_images(self):
        files = self.request.FILES.getlist('images')
        for idx, f in enumerate(files):
            CatalogItemImage.objects.create(item=self.object, image=f, sort_order=idx)

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
        ctx['item_images'] = self.object.images.all()
        return ctx

    def form_valid(self, form):
        self.object = form.save()
        files = self.request.FILES.getlist('images')
        base = self.object.images.count()
        for idx, f in enumerate(files):
            CatalogItemImage.objects.create(item=self.object, image=f, sort_order=base + idx)
        messages.success(self.request, 'آیتم به‌روزرسانی شد.')
        return redirect(self.get_success_url())

    def get_success_url(self):
        return reverse('catalog_item_list')


class CatalogItemImageDeleteView(MiniAppPanelMixin, View):
    def post(self, request, pk, image_pk):
        item = get_object_or_404(CatalogItem, pk=pk, **self.scope_filter())
        img = get_object_or_404(CatalogItemImage, pk=image_pk, item=item)
        img.delete()
        messages.success(request, 'تصویر حذف شد.')
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
