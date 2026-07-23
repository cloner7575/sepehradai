from __future__ import annotations

from django.conf import settings as django_settings
from django.db import models


class InstagramAutomationRule(models.Model):
    class TriggerType(models.TextChoices):
        MESSAGE_RECEIVED = 'message_received', 'پیام جدید'
        FIRST_CONVERSATION = 'first_conversation', 'اولین گفتگو'
        KEYWORD = 'keyword', 'کلمه کلیدی'
        EXACT_TEXT = 'exact_text', 'متن دقیق'
        STARTS_WITH = 'starts_with', 'شروع با'
        ENDS_WITH = 'ends_with', 'پایان با'
        ANY_KEYWORDS = 'any_keywords', 'هرکدام از کلمات'
        ALL_KEYWORDS = 'all_keywords', 'همه کلمات'
        EXCLUDE_KEYWORDS = 'exclude_keywords', 'بدون کلمات'
        NUMBER = 'number', 'عدد'
        IMAGE = 'image', 'تصویر'
        VIDEO = 'video', 'ویدیو'
        AUDIO = 'audio', 'صوت'
        ATTACHMENT = 'attachment', 'پیوست'
        STORY_REPLY = 'story_reply', 'پاسخ استوری'
        STORY_MENTION = 'story_mention', 'منشن استوری'
        COMMENT_ON_MEDIA = 'comment_on_media', 'کامنت روی محتوا'
        COMMENT_ANY = 'comment_any', 'کامنت روی هر محتوا'
        COMMENT_KEYWORD = 'comment_keyword', 'کلمه کلیدی کامنت'
        FIRST_INTERACTION = 'first_interaction', 'اولین تعامل'
        HAS_TAG = 'has_tag', 'دارای تگ'
        MISSING_TAG = 'missing_tag', 'بدون تگ'
        SCHEDULE = 'schedule', 'ساعت/روز'
        OUTSIDE_BUSINESS_HOURS = 'outside_business_hours', 'خارج ساعات کاری'
        NO_AGENT_REPLY = 'no_agent_reply', 'عدم پاسخ کارشناس'
        CONVERSATION_STATUS = 'conversation_status', 'تغییر وضعیت گفتگو'
        REFERRAL = 'referral', 'referral/postback'
        SEND_ERROR = 'send_error', 'خطای ارسال'
        CAMPAIGN_ENTRY = 'campaign_entry', 'ورود از کمپین'
        FALLBACK = 'fallback', 'پیش‌فرض ناشناخته'
        WELCOME = 'welcome', 'خوش‌آمدگویی'

    class MatchMode(models.TextChoices):
        ANY = 'any', 'هر شرط'
        ALL = 'all', 'همه شروط'

    workspace = models.ForeignKey(
        'balebot.Workspace',
        on_delete=models.CASCADE,
        related_name='instagram_rules',
        db_index=True,
    )
    connection = models.ForeignKey(
        'instagram.InstagramConnection',
        on_delete=models.CASCADE,
        related_name='rules',
        null=True,
        blank=True,
    )
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, default='')
    trigger_type = models.CharField(max_length=40, choices=TriggerType.choices, db_index=True)
    match_mode = models.CharField(
        max_length=8,
        choices=MatchMode.choices,
        default=MatchMode.ALL,
    )
    priority = models.IntegerField(default=100, db_index=True)
    is_active = models.BooleanField(default=False, db_index=True)
    schedule = models.JSONField(default=dict, blank=True)
    cooldown_seconds = models.PositiveIntegerField(default=0)
    stop_after_match = models.BooleanField(default=True)
    flow = models.ForeignKey(
        'instagram.InstagramFlow',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='rules',
    )
    created_by = models.ForeignKey(
        django_settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='instagram_rules_created',
    )
    last_executed_at = models.DateTimeField(null=True, blank=True)
    execution_count = models.PositiveIntegerField(default=0)
    success_count = models.PositiveIntegerField(default=0)
    last_error_sanitized = models.CharField(max_length=512, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['priority', 'created_at']
        verbose_name = 'قانون اتوماسیون اینستاگرام'
        verbose_name_plural = 'قوانین اتوماسیون اینستاگرام'
        indexes = [
            models.Index(fields=['workspace', 'is_active', 'priority']),
        ]

    def __str__(self):
        return self.name


class InstagramRuleCondition(models.Model):
    class Operator(models.TextChoices):
        EQ = 'eq', 'برابر'
        CONTAINS = 'contains', 'شامل'
        STARTS_WITH = 'starts_with', 'شروع با'
        ENDS_WITH = 'ends_with', 'پایان با'
        ANY_OF = 'any_of', 'هرکدام'
        ALL_OF = 'all_of', 'همه'
        NOT_CONTAINS = 'not_contains', 'بدون'
        REGEX = 'regex', 'عبارت منظم'
        EXISTS = 'exists', 'موجود'
        NOT_EXISTS = 'not_exists', 'ناموجود'

    rule = models.ForeignKey(
        InstagramAutomationRule,
        on_delete=models.CASCADE,
        related_name='conditions',
    )
    field = models.CharField(max_length=64, default='text')
    operator = models.CharField(max_length=20, choices=Operator.choices)
    value = models.JSONField(default=dict, blank=True)
    case_sensitive = models.BooleanField(default=False)
    normalize_persian = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'شرط قانون'
        verbose_name_plural = 'شروط قانون'


class InstagramFlow(models.Model):
    class Status(models.TextChoices):
        DRAFT = 'draft', 'پیش‌نویس'
        ACTIVE = 'active', 'فعال'
        ARCHIVED = 'archived', 'بایگانی'

    workspace = models.ForeignKey(
        'balebot.Workspace',
        on_delete=models.CASCADE,
        related_name='instagram_flows',
        db_index=True,
    )
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, default='')
    version = models.PositiveIntegerField(default=1)
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.DRAFT,
        db_index=True,
    )
    entry_node_id = models.CharField(max_length=64, blank=True, default='')
    definition = models.JSONField(default=dict, blank=True)
    created_by = models.ForeignKey(
        django_settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='instagram_flows_created',
    )
    published_at = models.DateTimeField(null=True, blank=True)
    parent_flow = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='versions',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']
        verbose_name = 'فلو اینستاگرام'
        verbose_name_plural = 'فلوهای اینستاگرام'
        indexes = [
            models.Index(fields=['workspace', 'status']),
        ]

    def __str__(self):
        return f'{self.name} v{self.version}'


class InstagramFlowNode(models.Model):
    flow = models.ForeignKey(
        InstagramFlow,
        on_delete=models.CASCADE,
        related_name='nodes',
    )
    node_key = models.CharField(max_length=64)
    node_type = models.CharField(max_length=64, db_index=True)
    position_x = models.FloatField(default=0)
    position_y = models.FloatField(default=0)
    config = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['flow', 'node_key'],
                name='ig_flow_node_key_uniq',
            ),
        ]

    def __str__(self):
        return f'{self.node_type}:{self.node_key}'


class InstagramFlowEdge(models.Model):
    flow = models.ForeignKey(
        InstagramFlow,
        on_delete=models.CASCADE,
        related_name='edges',
    )
    source_node = models.ForeignKey(
        InstagramFlowNode,
        on_delete=models.CASCADE,
        related_name='out_edges',
    )
    target_node = models.ForeignKey(
        InstagramFlowNode,
        on_delete=models.CASCADE,
        related_name='in_edges',
    )
    condition_key = models.CharField(max_length=64, blank=True, default='')
    priority = models.IntegerField(default=0)

    class Meta:
        ordering = ['priority', 'id']


class InstagramFlowExecution(models.Model):
    class Status(models.TextChoices):
        RUNNING = 'running', 'در حال اجرا'
        WAITING = 'waiting', 'منتظر'
        COMPLETED = 'completed', 'تمام'
        FAILED = 'failed', 'شکست'
        CANCELLED = 'cancelled', 'لغو'

    workspace = models.ForeignKey(
        'balebot.Workspace',
        on_delete=models.CASCADE,
        related_name='instagram_flow_executions',
        db_index=True,
    )
    flow = models.ForeignKey(
        InstagramFlow,
        on_delete=models.CASCADE,
        related_name='executions',
    )
    flow_version = models.PositiveIntegerField(default=1)
    conversation = models.ForeignKey(
        'instagram.InstagramConversation',
        on_delete=models.CASCADE,
        related_name='flow_executions',
        null=True,
        blank=True,
    )
    contact = models.ForeignKey(
        'instagram.InstagramContact',
        on_delete=models.CASCADE,
        related_name='flow_executions',
    )
    current_node_key = models.CharField(max_length=64, blank=True, default='')
    state = models.JSONField(default=dict, blank=True)
    variables = models.JSONField(default=dict, blank=True)
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.RUNNING,
        db_index=True,
    )
    is_test_mode = models.BooleanField(default=False)
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    failed_at = models.DateTimeField(null=True, blank=True)
    failure_reason_sanitized = models.CharField(max_length=512, blank=True, default='')
    log = models.JSONField(default=list, blank=True)

    class Meta:
        ordering = ['-started_at']
        indexes = [
            models.Index(fields=['workspace', 'status', 'started_at']),
        ]


class InstagramCommentAutomation(models.Model):
    class FollowCheckMode(models.TextChoices):
        DISABLED = 'disabled', 'غیرفعال — API رسمی پشتیبانی نمی‌کند'
        UNSUPPORTED = 'unsupported', 'نیازمند تأیید Meta'

    workspace = models.ForeignKey(
        'balebot.Workspace',
        on_delete=models.CASCADE,
        related_name='instagram_comment_automations',
        db_index=True,
    )
    connection = models.ForeignKey(
        'instagram.InstagramConnection',
        on_delete=models.CASCADE,
        related_name='comment_automations',
    )
    media_id = models.CharField(max_length=64, blank=True, default='', db_index=True)
    media_caption_preview = models.CharField(max_length=255, blank=True, default='')
    rule = models.ForeignKey(
        InstagramAutomationRule,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='comment_automations',
    )
    flow = models.ForeignKey(
        InstagramFlow,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='comment_automations',
    )
    is_active = models.BooleanField(default=False)
    include_keywords = models.JSONField(default=list, blank=True)
    exclude_keywords = models.JSONField(default=list, blank=True)
    public_replies = models.JSONField(default=list, blank=True)
    private_reply_text = models.TextField(blank=True, default='')
    public_reply_enabled = models.BooleanField(default=True)
    private_reply_enabled = models.BooleanField(default=False)
    follow_check_mode = models.CharField(
        max_length=20,
        choices=FollowCheckMode.choices,
        default=FollowCheckMode.DISABLED,
    )
    skip_own_comments = models.BooleanField(default=True)
    cooldown_seconds = models.PositiveIntegerField(default=60)
    tag = models.ForeignKey(
        'balebot.Tag',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='instagram_comment_automations',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']
        verbose_name = 'اتوماسیون کامنت'
        verbose_name_plural = 'اتوماسیون‌های کامنت'


class InstagramQuickReply(models.Model):
    workspace = models.ForeignKey(
        'balebot.Workspace',
        on_delete=models.CASCADE,
        related_name='instagram_quick_replies',
    )
    title = models.CharField(max_length=120)
    text = models.TextField()
    media_url = models.URLField(max_length=1024, blank=True, default='')
    category = models.CharField(max_length=64, blank=True, default='')
    shortcut = models.CharField(max_length=32, blank=True, default='')
    is_active = models.BooleanField(default=True)
    usage_count = models.PositiveIntegerField(default=0)
    created_by = models.ForeignKey(
        django_settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='instagram_quick_replies_created',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['title']


class InstagramTrackedLink(models.Model):
    workspace = models.ForeignKey(
        'balebot.Workspace',
        on_delete=models.CASCADE,
        related_name='instagram_tracked_links',
    )
    short_code = models.CharField(max_length=32, unique=True, db_index=True)
    code_digest = models.CharField(max_length=64, blank=True, default='', db_index=True)
    target_url = models.URLField(max_length=2048)
    campaign_id = models.CharField(max_length=64, blank=True, default='')
    flow = models.ForeignKey(
        InstagramFlow,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tracked_links',
    )
    rule = models.ForeignKey(
        InstagramAutomationRule,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tracked_links',
    )
    contact = models.ForeignKey(
        'instagram.InstagramContact',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tracked_links',
    )
    source_media = models.ForeignKey(
        'instagram.InstagramMedia',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tracked_links',
    )
    product_id = models.PositiveIntegerField(null=True, blank=True)
    click_count = models.PositiveIntegerField(default=0)
    last_clicked_at = models.DateTimeField(null=True, blank=True)
    conversion_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True, db_index=True)
    claimed_at = models.DateTimeField(null=True, blank=True)
    claimed_session_hash = models.CharField(max_length=64, blank=True, default='')
    revoked_at = models.DateTimeField(null=True, blank=True)
    is_single_use = models.BooleanField(default=True)


    class Meta:
        indexes = [
            models.Index(fields=['workspace', 'created_at']),
        ]


class InstagramMedia(models.Model):
    class MediaType(models.TextChoices):
        IMAGE = 'IMAGE', 'Image'
        VIDEO = 'VIDEO', 'Video'
        CAROUSEL = 'CAROUSEL_ALBUM', 'Carousel'
        STORY = 'STORY', 'Story'
        REEL = 'REEL', 'Reel'

    workspace = models.ForeignKey(
        'balebot.Workspace',
        on_delete=models.CASCADE,
        related_name='instagram_media',
        db_index=True,
    )
    connection = models.ForeignKey(
        'instagram.InstagramConnection',
        on_delete=models.CASCADE,
        related_name='media_items',
    )
    external_media_id = models.CharField(max_length=128, db_index=True)
    media_type = models.CharField(max_length=32, choices=MediaType.choices, blank=True, default='')
    media_product_type = models.CharField(max_length=32, blank=True, default='')
    caption = models.TextField(blank=True, default='')
    permalink = models.URLField(max_length=2048, blank=True, default='')
    media_url = models.URLField(max_length=2048, blank=True, default='')
    thumbnail_url = models.URLField(max_length=2048, blank=True, default='')
    published_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    product = models.ForeignKey(
        'balebot.CatalogItem',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='instagram_media_bindings',
    )
    is_active = models.BooleanField(default=True)
    last_synced_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-published_at', '-id']
        constraints = [
            models.UniqueConstraint(
                fields=['connection', 'external_media_id'],
                name='ig_media_connection_external_uniq',
            ),
        ]
        indexes = [
            models.Index(fields=['workspace', 'media_type', 'is_active']),
        ]


class InstagramStorefrontConfig(models.Model):
    workspace = models.OneToOneField(
        'balebot.Workspace',
        on_delete=models.CASCADE,
        related_name='instagram_storefront',
    )
    catalog = models.ForeignKey(
        'balebot.CatalogSettings',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='instagram_storefronts',
    )
    is_enabled = models.BooleanField(default=True)
    secure_link_hours = models.PositiveSmallIntegerField(default=24)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class InstagramAutomationActionRun(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        SUCCEEDED = 'succeeded', 'Succeeded'
        FAILED = 'failed', 'Failed'
        SKIPPED = 'skipped', 'Skipped'

    workspace = models.ForeignKey(
        'balebot.Workspace',
        on_delete=models.CASCADE,
        related_name='instagram_action_runs',
    )
    event = models.ForeignKey(
        'instagram.InstagramWebhookEvent',
        on_delete=models.CASCADE,
        related_name='action_runs',
    )
    rule = models.ForeignKey(
        InstagramAutomationRule,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='action_runs',
    )
    action_key = models.CharField(max_length=128)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)
    external_id = models.CharField(max_length=128, blank=True, default='')
    error_code = models.CharField(max_length=64, blank=True, default='')
    attempts = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['event', 'rule', 'action_key'],
                name='ig_action_event_rule_key_uniq',
            ),
        ]


class InstagramBusinessHours(models.Model):
    workspace = models.OneToOneField(
        'balebot.Workspace',
        on_delete=models.CASCADE,
        related_name='instagram_business_hours',
    )
    timezone = models.CharField(max_length=64, default='Asia/Tehran')
    weekly_schedule = models.JSONField(
        default=dict,
        blank=True,
        help_text='{"0":[{"start":"09:00","end":"18:00"}], ...} — 0=شنبه',
    )
    holidays = models.JSONField(default=list, blank=True)
    outside_hours_message = models.TextField(blank=True, default='')
    agent_transfer_delay_minutes = models.PositiveIntegerField(default=30)
    sla_first_response_minutes = models.PositiveIntegerField(default=15)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
