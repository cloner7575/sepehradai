from django.urls import path

from instagram import views

app_name = 'instagram'

urlpatterns = [
    path('instagram/', views.InstagramDashboardView.as_view(), name='dashboard'),
    path('instagram/extract/', views.PhoneExtractorView.as_view(), name='phone_extractor'),
    path('instagram/guide/', views.BackupGuideView.as_view(), name='backup_guide'),
    path('instagram/history/', views.ExtractionHistoryView.as_view(), name='history'),
    path('instagram/phones/', views.ExtractedPhoneListView.as_view(), name='phone_list'),
    path('instagram/phones/export/', views.ExtractedPhoneExportView.as_view(), name='phone_list_export'),
    path(
        'instagram/extract/start/',
        views.ExtractionStartView.as_view(),
        name='extraction_start',
    ),
    path(
        'instagram/extract/phone/',
        views.ExtractionSavePhoneView.as_view(),
        name='extraction_save_phone',
    ),
    path(
        'instagram/extract/finish/',
        views.ExtractionFinishView.as_view(),
        name='extraction_finish',
    ),
    path(
        'instagram/extract/<int:pk>/',
        views.ExtractionDetailView.as_view(),
        name='extraction_detail',
    ),
    path(
        'instagram/extract/<int:pk>/export/',
        views.ExtractionExportView.as_view(),
        name='extraction_export',
    ),
    path(
        'instagram/domains/',
        views.ActivityDomainListView.as_view(),
        name='activity_domain_list',
    ),
    path(
        'instagram/domains/<int:pk>/toggle/',
        views.ActivityDomainToggleView.as_view(),
        name='activity_domain_toggle',
    ),
]
