from django.contrib import admin

from .models import (
    BotSettings,
    CallbackLog,
    Campaign,
    CampaignDelivery,
    ClassEnrollmentRequest,
    InboundMessage,
    Subscriber,
    SubscriberTag,
    Tag,
)


@admin.register(BotSettings)
class BotSettingsAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return not BotSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Subscriber)
class SubscriberAdmin(admin.ModelAdmin):
    list_display = (
        'bale_user_id',
        'chat_id',
        'phone_number',
        'first_name',
        'is_registered',
        'is_active',
        'updated_at',
    )
    list_filter = ('is_registered', 'is_active')
    search_fields = ('phone_number', 'username', 'first_name', 'bale_user_id', 'chat_id')


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
    list_display = ('title', 'content_type', 'schedule_kind', 'status', 'scheduled_at', 'created_at')
    list_filter = ('status', 'content_type', 'schedule_kind')
    filter_horizontal = ('target_tags',)


@admin.register(CampaignDelivery)
class CampaignDeliveryAdmin(admin.ModelAdmin):
    list_display = ('campaign', 'subscriber', 'status', 'sent_at', 'created_at')
    list_filter = ('status',)


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'tag_type', 'is_active', 'updated_at')
    list_filter = ('tag_type', 'is_active')
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
