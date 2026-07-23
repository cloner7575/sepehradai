from __future__ import annotations

from django.conf import settings as django_settings
from django.db import models


class InstagramContact(models.Model):
    class ConversationStatus(models.TextChoices):
        OPEN = 'open', 'باز'
        PENDING = 'pending', 'در انتظار'
        CLOSED = 'closed', 'بسته'
        SPAM = 'spam', 'اسپم'

    workspace = models.ForeignKey(
        'balebot.Workspace',
        on_delete=models.CASCADE,
        related_name='instagram_contacts',
        db_index=True,
    )
    customer = models.ForeignKey(
        'balebot.CustomerProfile',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='instagram_contacts',
    )
    connection = models.ForeignKey(
        'instagram.InstagramConnection',
        on_delete=models.CASCADE,
        related_name='contacts',
    )
    instagram_scoped_user_id = models.CharField(max_length=64, db_index=True)
    username = models.CharField(max_length=255, blank=True, default='')
    display_name = models.CharField(max_length=255, blank=True, default='')
    profile_picture_url = models.URLField(max_length=1024, blank=True, default='')
    subscriber = models.ForeignKey(
        'balebot.Subscriber',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='instagram_contacts',
    )
    first_interaction_at = models.DateTimeField(null=True, blank=True)
    last_interaction_at = models.DateTimeField(null=True, blank=True)
    conversation_status = models.CharField(
        max_length=16,
        choices=ConversationStatus.choices,
        default=ConversationStatus.OPEN,
        db_index=True,
    )
    assigned_user = models.ForeignKey(
        django_settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_instagram_contacts',
    )
    is_blocked = models.BooleanField(default=False)
    metadata = models.JSONField(default=dict, blank=True)
    tags = models.ManyToManyField(
        'balebot.Tag',
        blank=True,
        related_name='instagram_contacts',
    )
    consent_opt_out = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-last_interaction_at', '-id']
        verbose_name = 'مخاطب اینستاگرام'
        verbose_name_plural = 'مخاطبان اینستاگرام'
        constraints = [
            models.UniqueConstraint(
                fields=['connection', 'instagram_scoped_user_id'],
                name='ig_contact_connection_scoped_uniq',
            ),
        ]
        indexes = [
            models.Index(fields=['workspace', 'last_interaction_at']),
            models.Index(fields=['workspace', 'assigned_user']),
        ]

    def __str__(self):
        return self.display_name or self.username or self.instagram_scoped_user_id


class InstagramConversation(models.Model):
    class Status(models.TextChoices):
        OPEN = 'open', 'باز'
        PENDING = 'pending', 'در انتظار'
        CLOSED = 'closed', 'بسته'
        SPAM = 'spam', 'اسپم'

    class Mode(models.TextChoices):
        AUTOMATION = 'automation', 'اتوماسیون'
        HUMAN = 'human', 'انسانی'
        HYBRID = 'hybrid', 'ترکیبی'

    workspace = models.ForeignKey(
        'balebot.Workspace',
        on_delete=models.CASCADE,
        related_name='instagram_conversations',
        db_index=True,
    )
    connection = models.ForeignKey(
        'instagram.InstagramConnection',
        on_delete=models.CASCADE,
        related_name='conversations',
    )
    contact = models.ForeignKey(
        InstagramContact,
        on_delete=models.CASCADE,
        related_name='conversations',
    )
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.OPEN,
        db_index=True,
    )
    mode = models.CharField(
        max_length=16,
        choices=Mode.choices,
        default=Mode.AUTOMATION,
        db_index=True,
    )
    assigned_user = models.ForeignKey(
        django_settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_instagram_conversations',
    )
    last_message_at = models.DateTimeField(null=True, blank=True, db_index=True)
    last_customer_message_at = models.DateTimeField(null=True, blank=True, db_index=True)
    unread_count = models.PositiveIntegerField(default=0)
    automation_paused_until = models.DateTimeField(null=True, blank=True)
    automation_paused_permanent = models.BooleanField(default=False)
    last_flow = models.ForeignKey(
        'instagram.InstagramFlow',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='conversations',
    )
    close_reason = models.CharField(max_length=255, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-last_message_at', '-id']
        verbose_name = 'گفتگوی اینستاگرام'
        verbose_name_plural = 'گفتگوهای اینستاگرام'
        constraints = [
            models.UniqueConstraint(
                fields=['connection', 'contact'],
                name='ig_conversation_connection_contact_uniq',
            ),
        ]
        indexes = [
            models.Index(fields=['workspace', 'status', 'mode']),
            models.Index(fields=['workspace', 'assigned_user']),
        ]

    def __str__(self):
        return f'Conv:{self.pk} {self.contact_id}'

    def is_automation_active(self) -> bool:
        if self.automation_paused_permanent:
            return False
        if self.mode == self.Mode.HUMAN:
            return False
        if self.automation_paused_until is None:
            return True
        from django.utils import timezone

        return timezone.now() >= self.automation_paused_until


class InstagramMessage(models.Model):
    class Direction(models.TextChoices):
        INBOUND = 'inbound', 'ورودی'
        OUTBOUND = 'outbound', 'خروجی'

    class SenderType(models.TextChoices):
        CUSTOMER = 'customer', 'مشتری'
        AUTOMATION = 'automation', 'اتوماسیون'
        AGENT = 'agent', 'کارشناس'
        SYSTEM = 'system', 'سیستم'

    class DeliveryStatus(models.TextChoices):
        PENDING = 'pending', 'در صف'
        SENT = 'sent', 'ارسال‌شده'
        DELIVERED = 'delivered', 'تحویل'
        READ = 'read', 'خوانده‌شده'
        FAILED = 'failed', 'ناموفق'

    workspace = models.ForeignKey(
        'balebot.Workspace',
        on_delete=models.CASCADE,
        related_name='instagram_messages',
        db_index=True,
    )
    conversation = models.ForeignKey(
        InstagramConversation,
        on_delete=models.CASCADE,
        related_name='messages',
    )
    external_message_id = models.CharField(max_length=512, blank=True, default='', db_index=True)
    direction = models.CharField(max_length=16, choices=Direction.choices)
    sender_type = models.CharField(max_length=16, choices=SenderType.choices)
    message_type = models.CharField(max_length=32, default='text')
    text = models.TextField(blank=True, default='')
    media_url = models.URLField(max_length=1024, blank=True, default='')
    media_storage_key = models.CharField(max_length=512, blank=True, default='')
    reply_to_external_message_id = models.CharField(max_length=512, blank=True, default='')
    delivery_status = models.CharField(
        max_length=16,
        choices=DeliveryStatus.choices,
        default=DeliveryStatus.PENDING,
        db_index=True,
    )
    failure_code = models.CharField(max_length=64, blank=True, default='')
    failure_message_sanitized = models.CharField(max_length=512, blank=True, default='')
    sent_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    read_at = models.DateTimeField(null=True, blank=True)
    raw_event = models.ForeignKey(
        'instagram.InstagramWebhookEvent',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='messages',
    )
    is_internal_note = models.BooleanField(default=False)
    created_by = models.ForeignKey(
        django_settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='instagram_messages_created',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']
        verbose_name = 'پیام اینستاگرام'
        verbose_name_plural = 'پیام‌های اینستاگرام'
        constraints = [
            models.UniqueConstraint(
                fields=['conversation', 'external_message_id'],
                condition=~models.Q(external_message_id=''),
                name='ig_message_conversation_external_uniq',
            ),
        ]
        indexes = [
            models.Index(fields=['workspace', 'created_at']),
            models.Index(fields=['conversation', 'created_at']),
        ]

    def __str__(self):
        return f'Msg:{self.pk}:{self.direction}'
