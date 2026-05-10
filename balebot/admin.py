from django.contrib import admin

from .models import (
    BotSettings,
    CallbackLog,
    Campaign,
    CampaignDelivery,
    InboundMessage,
    Subscriber,
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


@admin.register(CampaignDelivery)
class CampaignDeliveryAdmin(admin.ModelAdmin):
    list_display = ('campaign', 'subscriber', 'status', 'sent_at', 'created_at')
    list_filter = ('status',)
