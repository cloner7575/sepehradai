from django.contrib import admin

from instagram.models import (
    ActivityDomain,
    ExtractedPhone,
    ExtractionJob,
    InstagramConnection,
    InstagramConversation,
    InstagramWebhookEvent,
    InstagramAuditLog,
    InstagramFlow,
    InstagramAutomationRule,
    WorkspaceInstagramEntitlement,
)


class ExtractedPhoneInline(admin.TabularInline):
    model = ExtractedPhone
    extra = 0
    readonly_fields = ('phone_number', 'activity_domain_label', 'created_at')
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(ActivityDomain)
class ActivityDomainAdmin(admin.ModelAdmin):
    list_display = ('name', 'workspace', 'is_active', 'created_at')
    list_filter = ('is_active', 'workspace')
    search_fields = ('name',)


@admin.register(ExtractionJob)
class ExtractionJobAdmin(admin.ModelAdmin):
    list_display = (
        'pk',
        'domain_label',
        'workspace',
        'status',
        'phone_count',
        'source_filename',
        'created_at',
    )
    list_filter = ('status', 'workspace')
    search_fields = ('source_filename', 'activity_domain_custom')
    readonly_fields = ('phone_count', 'json_files_scanned', 'created_at', 'completed_at')
    inlines = [ExtractedPhoneInline]

    @admin.display(description='حوزه فعالیت')
    def domain_label(self, obj):
        return obj.domain_label


@admin.register(ExtractedPhone)
class ExtractedPhoneAdmin(admin.ModelAdmin):
    list_display = ('phone_number', 'activity_domain_label', 'workspace', 'job', 'created_at')
    list_filter = ('workspace', 'activity_domain_label')
    search_fields = ('phone_number',)


@admin.register(InstagramConnection)
class InstagramConnectionAdmin(admin.ModelAdmin):
    list_display = ('username', 'workspace', 'connection_status', 'webhook_status', 'updated_at')
    list_filter = ('connection_status', 'workspace')
    search_fields = ('username', 'instagram_account_id')
    readonly_fields = ('encrypted_access_token',)


@admin.register(InstagramConversation)
class InstagramConversationAdmin(admin.ModelAdmin):
    list_display = ('id', 'workspace', 'status', 'mode', 'unread_count', 'last_message_at')
    list_filter = ('status', 'mode', 'workspace')


@admin.register(InstagramWebhookEvent)
class InstagramWebhookEventAdmin(admin.ModelAdmin):
    list_display = ('event_type', 'processing_status', 'attempts', 'received_at', 'workspace')
    list_filter = ('processing_status', 'event_type')
    search_fields = ('fingerprint', 'correlation_id')


admin.site.register(InstagramAuditLog)
admin.site.register(InstagramFlow)
admin.site.register(InstagramAutomationRule)
admin.site.register(WorkspaceInstagramEntitlement)
