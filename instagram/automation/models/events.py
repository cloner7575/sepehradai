from __future__ import annotations

from django.db import models


class InstagramWebhookEvent(models.Model):
    class ProcessingStatus(models.TextChoices):
        RECEIVED = 'received', 'دریافت‌شده'
        QUEUED = 'queued', 'در صف'
        PROCESSING = 'processing', 'در حال پردازش'
        PROCESSED = 'processed', 'پردازش‌شده'
        FAILED = 'failed', 'شکست'
        DEAD = 'dead', 'dead-letter'
        SKIPPED = 'skipped', 'رد شده'

    connection = models.ForeignKey(
        'instagram.InstagramConnection',
        on_delete=models.CASCADE,
        related_name='webhook_events',
        null=True,
        blank=True,
    )
    workspace = models.ForeignKey(
        'balebot.Workspace',
        on_delete=models.CASCADE,
        related_name='instagram_webhook_events',
        null=True,
        blank=True,
        db_index=True,
    )
    external_event_id = models.CharField(max_length=512, blank=True, default='', db_index=True)
    event_type = models.CharField(max_length=64, db_index=True)
    fingerprint = models.CharField(max_length=128, db_index=True)
    payload_redacted = models.JSONField(default=dict, blank=True)
    processing_status = models.CharField(
        max_length=16,
        choices=ProcessingStatus.choices,
        default=ProcessingStatus.RECEIVED,
        db_index=True,
    )
    attempts = models.PositiveIntegerField(default=0)
    received_at = models.DateTimeField(auto_now_add=True, db_index=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    failed_at = models.DateTimeField(null=True, blank=True)
    next_retry_at = models.DateTimeField(null=True, blank=True)
    correlation_id = models.CharField(max_length=64, db_index=True)
    last_error_sanitized = models.CharField(max_length=512, blank=True, default='')

    class Meta:
        ordering = ['-received_at']
        verbose_name = 'رویداد وب‌هوک اینستاگرام'
        verbose_name_plural = 'رویدادهای وب‌هوک اینستاگرام'
        constraints = [
            models.UniqueConstraint(
                fields=['fingerprint'],
                name='ig_webhook_fingerprint_uniq',
            ),
        ]
        indexes = [
            models.Index(fields=['processing_status', 'next_retry_at']),
            models.Index(fields=['workspace', 'event_type', 'received_at']),
        ]

    def __str__(self):
        return f'{self.event_type}:{self.fingerprint[:12]}'


class InstagramAuditLog(models.Model):
    class ActorType(models.TextChoices):
        USER = 'user', 'کاربر'
        SYSTEM = 'system', 'سیستم'
        AUTOMATION = 'automation', 'اتوماسیون'
        META = 'meta', 'Meta'

    workspace = models.ForeignKey(
        'balebot.Workspace',
        on_delete=models.CASCADE,
        related_name='instagram_audit_logs',
        db_index=True,
    )
    actor_type = models.CharField(max_length=16, choices=ActorType.choices)
    actor_id = models.CharField(max_length=64, blank=True, default='')
    action = models.CharField(max_length=64, db_index=True)
    entity_type = models.CharField(max_length=64, blank=True, default='')
    entity_id = models.CharField(max_length=64, blank=True, default='')
    before_data_redacted = models.JSONField(default=dict, blank=True)
    after_data_redacted = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=512, blank=True, default='')
    correlation_id = models.CharField(max_length=64, blank=True, default='', db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'لاگ حسابرسی اینستاگرام'
        verbose_name_plural = 'لاگ‌های حسابرسی اینستاگرام'
        indexes = [
            models.Index(fields=['workspace', 'action', 'created_at']),
            models.Index(fields=['workspace', 'entity_type', 'entity_id']),
        ]
