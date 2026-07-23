from django.urls import path

from instagram import views
from instagram.automation.views import webhook as ig_webhook
from instagram.automation.views import connection as ig_conn
from instagram.automation.views import inbox as ig_inbox
from instagram.automation.views import panel as ig_panel
from instagram.automation.views import tracking as ig_track
from instagram.automation.views import ai as ig_ai
from instagram.automation.views import legal as ig_legal
from instagram.automation.views import catalog as ig_catalog

app_name = 'instagram'

urlpatterns = [
    path('instagram/privacy/', ig_legal.PrivacyPolicyView.as_view(), name='privacy_policy'),
    path('instagram/data-deletion/', ig_legal.DataDeletionView.as_view(), name='data_deletion'),
    # --- استخراج شماره (موجود) ---
    path('instagram/', views.InstagramDashboardView.as_view(), name='dashboard'),
    path('instagram/extract/', views.PhoneExtractorView.as_view(), name='phone_extractor'),
    path('instagram/guide/', views.BackupGuideView.as_view(), name='backup_guide'),
    path('instagram/history/', views.ExtractionHistoryView.as_view(), name='history'),
    path('instagram/phones/', views.ExtractedPhoneListView.as_view(), name='phone_list'),
    path('instagram/phones/export/', views.ExtractedPhoneExportView.as_view(), name='phone_list_export'),
    path('instagram/extract/start/', views.ExtractionStartView.as_view(), name='extraction_start'),
    path('instagram/extract/phone/', views.ExtractionSavePhoneView.as_view(), name='extraction_save_phone'),
    path('instagram/extract/finish/', views.ExtractionFinishView.as_view(), name='extraction_finish'),
    path('instagram/extract/<int:pk>/', views.ExtractionDetailView.as_view(), name='extraction_detail'),
    path('instagram/extract/<int:pk>/export/', views.ExtractionExportView.as_view(), name='extraction_export'),
    path('instagram/domains/', views.ActivityDomainListView.as_view(), name='activity_domain_list'),
    path('instagram/domains/<int:pk>/toggle/', views.ActivityDomainToggleView.as_view(), name='activity_domain_toggle'),
    # --- دایرکت هوشمند ---
    path('instagram/smart/', ig_panel.OverviewView.as_view(), name='overview'),
    path('instagram/connect/', ig_conn.ConnectionListView.as_view(), name='connection'),
    path('instagram/oauth/start/', ig_conn.OAuthStartView.as_view(), name='oauth_start'),
    path('instagram/oauth/callback/', ig_conn.OAuthCallbackView.as_view(), name='oauth_callback'),
    path('instagram/oauth/select/', ig_conn.ConnectionSelectView.as_view(), name='connection_select'),
    path('instagram/connections/<int:pk>/disconnect/', ig_conn.ConnectionDisconnectView.as_view(), name='connection_disconnect'),
    path('instagram/connections/<int:pk>/test/', ig_conn.ConnectionTestView.as_view(), name='connection_test'),
    path('instagram/connections/health/', ig_conn.ConnectionHealthApiView.as_view(), name='connection_health'),
    path('instagram/webhook/', ig_webhook.meta_webhook, name='webhook'),
    path('instagram/inbox/', ig_inbox.InboxListView.as_view(), name='inbox'),
    path('instagram/inbox/<int:pk>/', ig_inbox.InboxDetailView.as_view(), name='inbox_detail'),
    path('instagram/inbox/<int:pk>/reply/', ig_inbox.InboxReplyView.as_view(), name='inbox_reply'),
    path('instagram/inbox/<int:pk>/assign/', ig_inbox.InboxAssignView.as_view(), name='inbox_assign'),
    path('instagram/inbox/<int:pk>/automation/', ig_inbox.InboxAutomationToggleView.as_view(), name='inbox_automation'),
    path('instagram/inbox/<int:pk>/note/', ig_inbox.InboxNoteView.as_view(), name='inbox_note'),
    path('instagram/inbox/<int:pk>/poll/', ig_inbox.InboxPollView.as_view(), name='inbox_poll'),
    path('instagram/contacts/', ig_panel.ContactsView.as_view(), name='ig_contacts'),
    path('instagram/contacts/<int:pk>/link/', ig_inbox.ContactLinkSubscriberView.as_view(), name='contact_link'),
    path('instagram/rules/', ig_panel.RuleListView.as_view(), name='rules'),
    path('instagram/rules/new/', ig_panel.RuleEditView.as_view(), name='rule_create'),
    path('instagram/rules/preset/<str:key>/', ig_panel.RulePresetApplyView.as_view(), name='rule_preset'),
    path('instagram/rules/<int:pk>/', ig_panel.RuleEditView.as_view(), name='rule_edit'),
    path('instagram/rules/<int:pk>/toggle/', ig_panel.RuleToggleView.as_view(), name='rule_toggle'),
    path('instagram/flows/', ig_panel.FlowListView.as_view(), name='flows'),
    path('instagram/flows/new/', ig_panel.FlowEditView.as_view(), name='flow_create'),
    path('instagram/flows/<int:pk>/', ig_panel.FlowEditView.as_view(), name='flow_edit'),
    path('instagram/flows/<int:pk>/publish/', ig_panel.FlowPublishView.as_view(), name='flow_publish'),
    path('instagram/flows/<int:pk>/test/', ig_panel.FlowTestView.as_view(), name='flow_test'),
    path('instagram/flows/<int:pk>/duplicate/', ig_panel.FlowDuplicateView.as_view(), name='flow_duplicate'),
    path('instagram/comments/', ig_panel.CommentAutomationListView.as_view(), name='comments'),
    path('instagram/quick-replies/', ig_panel.QuickReplyListView.as_view(), name='quick_replies'),
    path('instagram/analytics/', ig_panel.AnalyticsView.as_view(), name='analytics'),
    path('instagram/analytics/export/', ig_panel.AnalyticsExportView.as_view(), name='analytics_export'),
    path('instagram/catalog/', ig_catalog.InstagramCatalogView.as_view(), name='catalog_media'),
    path('instagram/catalog/sync/', ig_catalog.InstagramMediaSyncView.as_view(), name='media_sync'),
    path('instagram/catalog/media/<int:pk>/bind/', ig_catalog.InstagramMediaBindView.as_view(), name='media_bind'),
    path('instagram/logs/', ig_panel.LogsView.as_view(), name='logs'),
    path('instagram/events/<int:pk>/replay/', ig_panel.EventReplayView.as_view(), name='event_replay'),
    path('instagram/r/<str:code>/', ig_track.TrackedLinkRedirectView.as_view(), name='tracked_link'),
    path('instagram/inbox/<int:pk>/ai/suggest/', ig_ai.AISuggestReplyView.as_view(), name='ai_suggest'),
    path('instagram/inbox/<int:pk>/ai/classify/', ig_ai.AIClassifyView.as_view(), name='ai_classify'),
]
