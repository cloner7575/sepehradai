from django.contrib import admin

from .models import (
    BotSettings,
    CallbackLog,
    Campaign,
    CampaignDelivery,
    CatalogCategory,
    CatalogItem,
    CatalogOrder,
    CatalogSettings,
    ClassEnrollmentRequest,
    FlowMedia,
    InboundMessage,
    Platform,
    Subscriber,
    SubscriberTag,
    Tag,
    Workspace,
)


@admin.register(Workspace)
class WorkspaceAdmin(admin.ModelAdmin):
    list_display = ('name', 'owner', 'is_active', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('name', 'owner__username')


@admin.register(FlowMedia)
class FlowMediaAdmin(admin.ModelAdmin):
    list_display = ('id', 'workspace', 'platform', 'uploaded_at', 'messenger_file_id')
    list_filter = ('workspace', 'platform')
    readonly_fields = ('id', 'uploaded_at')


@admin.register(BotSettings)
class BotSettingsAdmin(admin.ModelAdmin):
    list_display = ('workspace', 'platform', 'is_enabled', 'masked_bot_token', 'updated_at')
    list_filter = ('workspace', 'platform', 'is_enabled')

    def has_add_permission(self, request):
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Subscriber)
class SubscriberAdmin(admin.ModelAdmin):
    list_display = (
        'workspace',
        'platform',
        'messenger_user_id',
        'chat_id',
        'phone_number',
        'first_name',
        'is_registered',
        'is_active',
        'updated_at',
    )
    list_filter = ('workspace', 'platform', 'is_registered', 'is_active')
    search_fields = ('phone_number', 'username', 'first_name', 'messenger_user_id', 'chat_id')


@admin.register(InboundMessage)
class InboundMessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'subscriber', 'kind', 'created_at')
    list_filter = ('kind',)


@admin.register(CallbackLog)
class CallbackLogAdmin(admin.ModelAdmin):
    list_display = ('id', 'subscriber', 'data', 'campaign', 'created_at')
    search_fields = ('data', 'callback_query_id')


@admin.register(Campaign)
class CampaignAdmin(admin.ModelAdmin):
    list_display = ('title', 'workspace', 'platform', 'content_type', 'schedule_kind', 'status', 'scheduled_at', 'created_at')
    list_filter = ('workspace', 'platform', 'status', 'content_type', 'schedule_kind')
    filter_horizontal = ('target_tags',)


@admin.register(CampaignDelivery)
class CampaignDeliveryAdmin(admin.ModelAdmin):
    list_display = ('campaign', 'subscriber', 'status', 'sent_at', 'created_at')
    list_filter = ('status',)


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('name', 'workspace', 'platform', 'slug', 'tag_type', 'is_active', 'updated_at')
    list_filter = ('workspace', 'platform', 'tag_type', 'is_active')
    search_fields = ('name', 'slug')


@admin.register(SubscriberTag)
class SubscriberTagAdmin(admin.ModelAdmin):
    list_display = ('subscriber', 'tag', 'assigned_by', 'assigned_at')
    list_filter = ('tag',)
    search_fields = ('subscriber__phone_number', 'subscriber__username', 'tag__name')


@admin.register(ClassEnrollmentRequest)
class ClassEnrollmentRequestAdmin(admin.ModelAdmin):
    list_display = ('subscriber', 'tag', 'status', 'requested_at', 'reviewed_at', 'reviewed_by')
    list_filter = ('status', 'tag')
    search_fields = ('subscriber__phone_number', 'subscriber__username', 'tag__name')


@admin.register(CatalogSettings)
class CatalogSettingsAdmin(admin.ModelAdmin):
    list_display = ('workspace', 'platform', 'is_enabled', 'public_id', 'updated_at')
    list_filter = ('platform', 'is_enabled')


@admin.register(CatalogCategory)
class CatalogCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'workspace', 'platform', 'sort_order', 'is_active')
    list_filter = ('platform', 'is_active')


@admin.register(CatalogItem)
class CatalogItemAdmin(admin.ModelAdmin):
    list_display = ('title', 'workspace', 'platform', 'price', 'is_active', 'is_featured')
    list_filter = ('platform', 'item_type', 'is_active')


@admin.register(CatalogOrder)
class CatalogOrderAdmin(admin.ModelAdmin):
    list_display = ('pk', 'workspace', 'platform', 'status', 'total_amount', 'created_at')
    list_filter = ('platform', 'status')
