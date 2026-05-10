"""
URL configuration for core project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.http import HttpResponseRedirect
from django.urls import include, path


def redirect_panel_root(_request):
    return HttpResponseRedirect('/')


def redirect_panel_nested(_request, subpath):
    subpath = (subpath or '').strip('/')
    if subpath:
        return HttpResponseRedirect(f'/{subpath}/')
    return HttpResponseRedirect('/')


urlpatterns = [
    path('admin/', admin.site.urls),
    # مسیرهای قدیمی /panel/… برای نشانک‌ها
    path('panel/', redirect_panel_root),
    path('panel/<path:subpath>/', redirect_panel_nested),
    path('', include('balebot.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
