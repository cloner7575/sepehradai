from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View

from balebot.models import CatalogItem, CatalogSettings
from instagram.mixins import InstagramPanelMixin
from instagram.automation.models import (
    InstagramConnection,
    InstagramMedia,
    InstagramStorefrontConfig,
)


class InstagramCatalogView(InstagramPanelMixin, View):
    template_name = 'instagram/automation/catalog_media.html'

    def get(self, request):
        workspace = self.get_workspace()
        catalogs = CatalogSettings.objects.filter(workspace=workspace, is_enabled=True).order_by('platform')
        storefront = InstagramStorefrontConfig.objects.filter(workspace=workspace).first()
        if not storefront and catalogs.count() == 1:
            storefront = InstagramStorefrontConfig.objects.create(
                workspace=workspace,
                catalog=catalogs.first(),
                is_enabled=True,
            )
        selected_catalog = storefront.catalog if storefront and storefront.catalog_id else None
        products = CatalogItem.objects.filter(workspace=workspace, is_active=True)
        if selected_catalog:
            products = products.filter(platform=selected_catalog.platform)
        media = InstagramMedia.objects.filter(workspace=workspace).select_related('connection', 'product')[:200]
        connections = InstagramConnection.objects.filter(
            workspace=workspace,
            connection_status=InstagramConnection.ConnectionStatus.CONNECTED,
        )
        return render(request, self.template_name, {
            'catalogs': catalogs,
            'storefront': storefront,
            'products': products.order_by('title'),
            'media_items': media,
            'connections': connections,
        })

    def post(self, request):
        workspace = self.get_workspace()
        catalog = get_object_or_404(
            CatalogSettings,
            pk=request.POST.get('catalog_id'),
            workspace=workspace,
            is_enabled=True,
        )
        InstagramStorefrontConfig.objects.update_or_create(
            workspace=workspace,
            defaults={'catalog': catalog, 'is_enabled': True},
        )
        messages.success(request, 'کاتالوگ مبدا اینستاگرام ذخیره شد.')
        return redirect('instagram:catalog_media')


class InstagramMediaSyncView(InstagramPanelMixin, View):
    def post(self, request):
        workspace = self.get_workspace()
        connection = get_object_or_404(
            InstagramConnection,
            pk=request.POST.get('connection_id'),
            workspace=workspace,
            connection_status=InstagramConnection.ConnectionStatus.CONNECTED,
        )
        from instagram.automation.tasks import sync_instagram_media

        sync_instagram_media.delay(connection.pk)
        messages.success(request, 'همگام‌سازی محتوا در صف اینستاگرام قرار گرفت.')
        return redirect('instagram:catalog_media')


class InstagramMediaBindView(InstagramPanelMixin, View):
    def post(self, request, pk):
        workspace = self.get_workspace()
        media = get_object_or_404(InstagramMedia, pk=pk, workspace=workspace)
        product_id = request.POST.get('product_id')
        product = None
        if product_id:
            storefront = get_object_or_404(
                InstagramStorefrontConfig.objects.select_related('catalog'),
                workspace=workspace,
                is_enabled=True,
            )
            product = get_object_or_404(
                CatalogItem,
                pk=product_id,
                workspace=workspace,
                platform=storefront.catalog.platform,
                is_active=True,
            )
        media.product = product
        media.save(update_fields=['product'])
        if request.headers.get('Accept') == 'application/json':
            return JsonResponse({'ok': True, 'product_id': product.pk if product else None})
        messages.success(request, 'اتصال محتوا به محصول ذخیره شد.')
        return redirect('instagram:catalog_media')
