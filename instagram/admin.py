from django.contrib import admin

from instagram.models import ActivityDomain, ExtractedPhone, ExtractionJob


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
