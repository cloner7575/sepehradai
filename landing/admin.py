from django.contrib import admin

from landing.models import BusinessCategory, LandingSettings, Lead, SubscriptionPlan


@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'phone',
        'business_type',
        'messenger',
        'is_contacted',
        'created_at',
    )
    list_filter = ('is_contacted', 'messenger', 'source')
    search_fields = ('name', 'phone', 'business_name', 'note')
    readonly_fields = ('created_at',)
    list_editable = ('is_contacted',)


@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = ('name', 'price_label', 'is_featured', 'is_active', 'sort_order')
    list_filter = ('is_active', 'is_featured')
    search_fields = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}


@admin.register(BusinessCategory)
class BusinessCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'sort_order', 'is_active', 'show_on_landing', 'is_other')
    list_filter = ('is_active', 'show_on_landing', 'is_other')
    search_fields = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}


@admin.register(LandingSettings)
class LandingSettingsAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return not LandingSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False
