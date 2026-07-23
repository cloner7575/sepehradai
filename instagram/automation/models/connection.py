from __future__ import annotations

from django.conf import settings as django_settings
from django.db import models


class WorkspaceInstagramEntitlement(models.Model):
    """Feature flags و entitlement ماژول اینستاگرام برای هر workspace."""

    workspace = models.OneToOneField(
        'balebot.Workspace',
        on_delete=models.CASCADE,
        related_name='instagram_entitlement',
    )
    instagram_module = models.BooleanField(default=True)
    instagram_connection = models.BooleanField(default=True)
    instagram_inbox = models.BooleanField(default=True)
    instagram_dm_automation = models.BooleanField(default=True)
    instagram_comment_automation = models.BooleanField(default=False)
    instagram_private_reply = models.BooleanField(default=False)
    instagram_flow_builder = models.BooleanField(default=True)
    instagram_analytics = models.BooleanField(default=True)
    instagram_ai_assistant = models.BooleanField(default=False)
    # قابلیت‌های نیازمند App Review — در UI به‌صورت نیازمند تأیید نمایش داده می‌شوند
    meta_messaging_approved = models.BooleanField(default=False)
    meta_comments_approved = models.BooleanField(default=False)
    meta_private_reply_approved = models.BooleanField(default=False)
    staff_permissions = models.JSONField(
        default=dict,
        blank=True,
        help_text='نقشه‌ی permissionهای instagram.* برای کاربران staff غیرمالک.',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'دسترسی اینستاگرام workspace'
        verbose_name_plural = 'دسترسی‌های اینستاگرام workspace'

    def __str__(self):
        return f'IG entitlement:{self.workspace_id}'


class InstagramConnection(models.Model):
    class ConnectionStatus(models.TextChoices):
        PENDING = 'pending', 'در انتظار'
        CONNECTED = 'connected', 'متصل'
        DEGRADED = 'degraded', 'ناقص'
        DISCONNECTED = 'disconnected', 'قطع‌شده'
        ERROR = 'error', 'خطا'

    class WebhookStatus(models.TextChoices):
        UNKNOWN = 'unknown', 'نامشخص'
        ACTIVE = 'active', 'فعال'
        INACTIVE = 'inactive', 'غیرفعال'
        ERROR = 'error', 'خطا'

    class AuthProvider(models.TextChoices):
        INSTAGRAM_LOGIN = 'instagram_login', 'Instagram Login'
        FACEBOOK_LEGACY = 'facebook_login_legacy', 'Facebook Login (legacy)'


    workspace = models.ForeignKey(
        'balebot.Workspace',
        on_delete=models.CASCADE,
        related_name='instagram_connections',
        db_index=True,
    )
    connected_by = models.ForeignKey(
        django_settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='instagram_connections_created',
    )
    auth_provider = models.CharField(
        max_length=32,
        choices=AuthProvider.choices,
        default=AuthProvider.FACEBOOK_LEGACY,
        db_index=True,
    )
    instagram_account_id = models.CharField(max_length=64, db_index=True)
    facebook_page_id = models.CharField(max_length=64, blank=True, default='')
    username = models.CharField(max_length=255, blank=True, default='')
    profile_name = models.CharField(max_length=255, blank=True, default='')
    profile_picture_url = models.URLField(max_length=1024, blank=True, default='')
    encrypted_access_token = models.TextField(blank=True, default='')
    token_expires_at = models.DateTimeField(null=True, blank=True)
    scopes = models.JSONField(default=list, blank=True)
    webhook_subscribed_fields = models.JSONField(default=list, blank=True)
    capability_status = models.JSONField(default=dict, blank=True)
    token_last_refreshed_at = models.DateTimeField(null=True, blank=True)
    connection_status = models.CharField(
        max_length=20,
        choices=ConnectionStatus.choices,
        default=ConnectionStatus.PENDING,
        db_index=True,
    )
    webhook_status = models.CharField(
        max_length=20,
        choices=WebhookStatus.choices,
        default=WebhookStatus.UNKNOWN,
    )
    last_sync_at = models.DateTimeField(null=True, blank=True)
    last_webhook_at = models.DateTimeField(null=True, blank=True)
    last_error_code = models.CharField(max_length=64, blank=True, default='')
    last_error_message_sanitized = models.CharField(max_length=512, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    disconnected_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-updated_at']
        verbose_name = 'اتصال اینستاگرام'
        verbose_name_plural = 'اتصالات اینستاگرام'
        constraints = [
            models.UniqueConstraint(
                fields=['instagram_account_id'],
                condition=models.Q(connection_status='connected'),
                name='ig_connection_account_connected_uniq',
            ),
            models.UniqueConstraint(
                fields=['workspace', 'instagram_account_id'],
                name='ig_connection_workspace_account_uniq',
            ),
        ]
        indexes = [
            models.Index(fields=['workspace', 'connection_status']),
            models.Index(fields=['facebook_page_id']),
        ]

    def __str__(self):
        return self.username or self.instagram_account_id

    @property
    def is_connected(self) -> bool:
        return self.connection_status == self.ConnectionStatus.CONNECTED
