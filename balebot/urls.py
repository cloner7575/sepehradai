from django.contrib.auth import views as auth_views
from django.urls import path

from balebot import views_panel, views_webhook

urlpatterns = [
    path('health/', views_webhook.webhook_health, name='bale_health'),
    path(
        'webhook/<str:platform>/<str:secret>',
        views_webhook.platform_webhook,
        name='platform_webhook',
    ),
    path(
        'webhook/<str:platform>/<str:secret>/',
        views_webhook.platform_webhook,
        name='platform_webhook_slash',
    ),
    path('webhook/<str:secret>', views_webhook.bale_webhook_legacy, name='bale_webhook'),
    path('webhook/<str:secret>/', views_webhook.bale_webhook_legacy, name='bale_webhook_slash'),
    # آدرس قدیمی وب‌هوک وقتی پروژه زیر /bale/ بود
    path('bale/webhook/<str:secret>', views_webhook.bale_webhook_legacy),
    path('bale/webhook/<str:secret>/', views_webhook.bale_webhook_legacy),
    path(
        'login/',
        auth_views.LoginView.as_view(template_name='balebot/login.html'),
        name='panel_login',
    ),
    path(
        'logout/',
        auth_views.LogoutView.as_view(),
        name='panel_logout',
    ),
    path('', views_panel.DashboardView.as_view(), name='panel_dashboard'),
    path(
        'switch-platform/',
        views_panel.SwitchPlatformView.as_view(),
        name='panel_switch_platform',
    ),
    path('bot/', views_panel.BotSettingsView.as_view(), name='bot_settings'),
    path('subscribers/', views_panel.SubscriberListView.as_view(), name='subscriber_list'),
    path('subscribers/<int:pk>/', views_panel.SubscriberDetailView.as_view(), name='subscriber_detail'),
    path(
        'bot/flow-media-upload/',
        views_panel.FlowMediaUploadView.as_view(),
        name='flow_media_upload',
    ),
    path('campaigns/', views_panel.CampaignListView.as_view(), name='campaign_list'),
    path('campaigns/new/', views_panel.CampaignCreateView.as_view(), name='campaign_create'),
    path(
        'campaigns/<int:pk>/',
        views_panel.CampaignDetailView.as_view(),
        name='campaign_detail',
    ),
    path(
        'campaigns/<int:pk>/edit/',
        views_panel.CampaignUpdateView.as_view(),
        name='campaign_edit',
    ),
    path(
        'campaigns/media-upload/',
        views_panel.CampaignMediaUploadView.as_view(),
        name='campaign_media_upload',
    ),
    path(
        'campaigns/media-upload/clear/',
        views_panel.CampaignMediaClearView.as_view(),
        name='campaign_media_clear',
    ),
    path('callbacks/', views_panel.CallbackLogListView.as_view(), name='callback_log_list'),
    path('inbound/', views_panel.InboundListView.as_view(), name='inbound_list'),
]
