from django.conf import settings as django_settings
from django.db import models


class ActivityDomain(models.Model):
    """حوزه‌های فعالیت از پیش‌تعریف‌شده برای هر workspace."""

    workspace = models.ForeignKey(
        'balebot.Workspace',
        on_delete=models.CASCADE,
        related_name='instagram_activity_domains',
    )
    name = models.CharField(max_length=120, verbose_name='نام حوزه')
    is_active = models.BooleanField(default=True, verbose_name='فعال')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'حوزه فعالیت'
        verbose_name_plural = 'حوزه‌های فعالیت'
        constraints = [
            models.UniqueConstraint(
                fields=['workspace', 'name'],
                name='instagram_activitydomain_workspace_name_uniq',
            ),
        ]

    def __str__(self):
        return self.name


class ExtractionJob(models.Model):
    class Status(models.TextChoices):
        RUNNING = 'running', 'در حال اجرا'
        COMPLETED = 'completed', 'تمام‌شده'
        FAILED = 'failed', 'ناموفق'

    workspace = models.ForeignKey(
        'balebot.Workspace',
        on_delete=models.CASCADE,
        related_name='instagram_extraction_jobs',
    )
    created_by = models.ForeignKey(
        django_settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='instagram_extraction_jobs',
    )
    activity_domain = models.ForeignKey(
        ActivityDomain,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='extraction_jobs',
    )
    activity_domain_custom = models.CharField(
        max_length=120,
        blank=True,
        default='',
        verbose_name='حوزه سفارشی',
    )
    source_filename = models.CharField(max_length=255, blank=True, default='')
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.RUNNING,
        db_index=True,
    )
    phone_count = models.PositiveIntegerField(default=0)
    json_files_scanned = models.PositiveIntegerField(default=0)
    error_message = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'عملیات استخراج'
        verbose_name_plural = 'عملیات‌های استخراج'

    def __str__(self):
        return f'{self.domain_label} — {self.source_filename or self.pk}'

    @property
    def domain_label(self) -> str:
        if self.activity_domain_id:
            return self.activity_domain.name
        return (self.activity_domain_custom or '').strip() or '—'


class ExtractedPhone(models.Model):
    job = models.ForeignKey(
        ExtractionJob,
        on_delete=models.CASCADE,
        related_name='phones',
    )
    workspace = models.ForeignKey(
        'balebot.Workspace',
        on_delete=models.CASCADE,
        related_name='instagram_extracted_phones',
    )
    phone_number = models.CharField(max_length=11, db_index=True)
    activity_domain_label = models.CharField(max_length=120, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'شماره استخراج‌شده'
        verbose_name_plural = 'شماره‌های استخراج‌شده'
        constraints = [
            models.UniqueConstraint(
                fields=['job', 'phone_number'],
                name='instagram_extractedphone_job_phone_uniq',
            ),
        ]
        indexes = [
            models.Index(fields=['workspace', 'activity_domain_label']),
            models.Index(fields=['workspace', 'phone_number']),
        ]

    def __str__(self):
        return self.phone_number
