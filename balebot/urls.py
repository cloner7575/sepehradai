from django.contrib.auth import views as auth_views
from django.urls import path

from balebot import views_panel, views_webhook

urlpatterns = [
    path('health/', views_webhook.webhook_health, name='bale_health'),
    path('webhook/<str:secret>/', views_webhook.bale_webhook, name='bale_webhook'),
    path(
        'panel/login/',
        auth_views.LoginView.as_view(template_name='balebot/login.html'),
        name='panel_login',
    ),
    path(
        'panel/logout/',
        auth_views.LogoutView.as_view(),
        name='panel_logout',
    ),
    path('panel/', views_panel.DashboardView.as_view(), name='panel_dashboard'),
    path('panel/bot/', views_panel.BotSettingsView.as_view(), name='bot_settings'),
    path('panel/subscribers/', views_panel.SubscriberListView.as_view(), name='subscriber_list'),
    path('panel/campaigns/', views_panel.CampaignListView.as_view(), name='campaign_list'),
    path('panel/campaigns/new/', views_panel.CampaignCreateView.as_view(), name='campaign_create'),
    path(
        'panel/campaigns/<int:pk>/',
        views_panel.CampaignDetailView.as_view(),
        name='campaign_detail',
    ),
    path(
        'panel/campaigns/<int:pk>/edit/',
        views_panel.CampaignUpdateView.as_view(),
        name='campaign_edit',
    ),
    path('panel/callbacks/', views_panel.CallbackLogListView.as_view(), name='callback_log_list'),
    path('panel/inbound/', views_panel.InboundListView.as_view(), name='inbound_list'),
]
