from django.contrib import admin

from landing.models import Lead


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
