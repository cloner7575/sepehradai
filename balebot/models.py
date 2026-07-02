import secrets
import uuid

from django.conf import settings as django_settings
from django.db import models
from django.utils import timezone


class Platform(models.TextChoices):
    BALE = 'bale', 'بله'
    TELEGRAM = 'telegram', 'تلگرام'


def generate_webhook_secret() -> str:
    return secrets.token_urlsafe(32)[:64]


class Workspace(models.Model):
    """فضای کاری اختصاصی هر کاربر پنل — داده‌های ربات از هم جدا می‌شوند."""

    name = models.CharField(max_length=120, verbose_name='نام پنل')
    owner = models.OneToOneField(
        django_settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='workspace',
    )
    is_active = models.BooleanField(default=True, verbose_name='فعال')
    allow_bale = models.BooleanField(default=True, verbose_name='دسترسی بله')
    allow_telegram = models.BooleanField(default=True, verbose_name='دسترسی تلگرام')
    allow_bale_miniapp = models.BooleanField(
        default=False,
        verbose_name='دسترسی مینی‌اپ بله',
    )
    allow_telegram_miniapp = models.BooleanField(
        default=False,
        verbose_name='دسترسی مینی‌اپ تلگرام',
    )
    allow_instagram = models.BooleanField(
        default=False,
        verbose_name='دسترسی اینستاگرام',
    )
    subscription_expires_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='تاریخ انقضای اشتراک',
        help_text='خالی = بدون محدودیت زمانی.',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'فضای کاری'
        verbose_name_plural = 'فضاهای کاری'

    def __str__(self):
        return self.name

    def allowed_platforms(self) -> list[str]:
        platforms: list[str] = []
        if self.allow_bale:
            platforms.append(Platform.BALE)
        if self.allow_telegram:
            platforms.append(Platform.TELEGRAM)
        return platforms

    def has_platform_access(self, platform: str) -> bool:
        platform = Platform.TELEGRAM if platform == Platform.TELEGRAM else Platform.BALE
        if platform == Platform.TELEGRAM:
            return self.allow_telegram
        return self.allow_bale

    def has_miniapp_access(self, platform: str) -> bool:
        platform = Platform.TELEGRAM if platform == Platform.TELEGRAM else Platform.BALE
        if platform == Platform.TELEGRAM:
            return self.allow_telegram and self.allow_telegram_miniapp
        return self.allow_bale and self.allow_bale_miniapp

    def has_instagram_access(self) -> bool:
        return self.allow_instagram

    def has_any_access(self) -> bool:
        return (
            self.allow_bale
            or self.allow_telegram
            or self.allow_instagram
            or (self.allow_bale and self.allow_bale_miniapp)
            or (self.allow_telegram and self.allow_telegram_miniapp)
        )

    def is_subscription_active(self) -> bool:
        if not self.is_active:
            return False
        if self.subscription_expires_at is None:
            return True
        return timezone.now() < self.subscription_expires_at

    def subscription_days_remaining(self) -> int | None:
        if self.subscription_expires_at is None:
            return None
        delta = self.subscription_expires_at - timezone.now()
        return max(0, delta.days)

    def subscription_status(self) -> str:
        """unlimited | active | expiring_soon | expired"""
        if not self.is_active:
            return 'expired'
        if self.subscription_expires_at is None:
            return 'unlimited'
        if not self.is_subscription_active():
            return 'expired'
        days = self.subscription_days_remaining()
        if days is not None and days <= 7:
            return 'expiring_soon'
        return 'active'


class FlowMedia(models.Model):
    """رسانهٔ آپلودشده برای نودهای مدیا در جریان /start."""

    class MediaKind(models.TextChoices):
        PHOTO = 'photo', 'عکس'
        VIDEO = 'video', 'ویدیو'
        VOICE = 'voice', 'صدا'
        DOCUMENT = 'document', 'سند'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(
        Workspace,
        on_delete=models.CASCADE,
        related_name='flow_media',
        db_index=True,
    )
    platform = models.CharField(
        max_length=16,
        choices=Platform.choices,
        default=Platform.BALE,
        db_index=True,
    )
    file = models.FileField(upload_to='flow_media/%Y/%m/')
    media_kind = models.CharField(
        max_length=16,
        choices=MediaKind.choices,
        default=MediaKind.PHOTO,
        db_index=True,
    )
    messenger_file_id = models.CharField(max_length=512, blank=True, default='')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-uploaded_at']

    def __str__(self):
        return str(self.id)


class Tag(models.Model):
    class TagType(models.TextChoices):
        CLASS = 'class', 'کلاس'
        GENERIC = 'generic', 'عمومی'

    workspace = models.ForeignKey(
        Workspace,
        on_delete=models.CASCADE,
        related_name='tags',
        db_index=True,
    )
    platform = models.CharField(
        max_length=16,
        choices=Platform.choices,
        default=Platform.BALE,
        db_index=True,
    )
    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=140)
    tag_type = models.CharField(
        max_length=16,
        choices=TagType.choices,
        default=TagType.GENERIC,
        db_index=True,
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        constraints = [
            models.UniqueConstraint(
                fields=['workspace', 'platform', 'slug'],
                name='unique_tag_workspace_platform_slug',
            ),
            models.UniqueConstraint(
                fields=['workspace', 'platform', 'name'],
                name='unique_tag_workspace_platform_name',
            ),
        ]

    def __str__(self):
        return self.name


class Subscriber(models.Model):
    """کاربرانی که با بازو تعامل دارند."""

    workspace = models.ForeignKey(
        Workspace,
        on_delete=models.CASCADE,
        related_name='subscribers',
        db_index=True,
    )
    platform = models.CharField(
        max_length=16,
        choices=Platform.choices,
        default=Platform.BALE,
        db_index=True,
    )
    messenger_user_id = models.BigIntegerField(db_index=True)
    chat_id = models.BigIntegerField(db_index=True)
    phone_number = models.CharField(max_length=32, blank=True, default='')
    first_name = models.CharField(max_length=255, blank=True, default='')
    last_name = models.CharField(max_length=255, blank=True, default='')
    username = models.CharField(max_length=255, blank=True, default='')
    is_registered = models.BooleanField(
        default=False,
        help_text='پس از ارسال شماره تماس از طریق دکمهٔ تماس فعال می‌شود.',
    )
    is_active = models.BooleanField(
        default=True,
        help_text='در صورت غیرفعال، در کمپین‌ها ارسال نمی‌شود.',
    )
    menu_flow_log = models.JSONField(
        default=list,
        blank=True,
        help_text='تاریخچهٔ کلیک‌های منوی /start (آخرین مراحل).',
    )
    menu_flow_answers = models.JSONField(
        default=dict,
        blank=True,
        help_text='پاسخ‌های نام‌دار (flow_key) از دکمه‌های منو.',
    )
    awaiting_support_message = models.BooleanField(
        default=False,
        help_text='اگر روشن باشد، پیام بعدی کاربر به عنوان پیام پشتیبانی ثبت می‌شود.',
    )
    flow_state = models.JSONField(
        default=dict,
        blank=True,
        help_text='حالت موقت جریان (ورودی، فرم، رهگیری سفارش و …).',
    )
    miniapp_first_seen_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='اولین بازدید از مینی‌اپ فروشگاه.',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    tags = models.ManyToManyField(
        Tag,
        through='SubscriberTag',
        related_name='subscribers',
        blank=True,
    )

    class Meta:
        ordering = ['-updated_at']
        constraints = [
            models.UniqueConstraint(
                fields=['workspace', 'platform', 'messenger_user_id'],
                name='unique_subscriber_workspace_platform_user',
            ),
        ]

    def __str__(self):
        return f'{self.phone_number or self.messenger_user_id}'


class InboundMessage(models.Model):
    class MessageKind(models.TextChoices):
        TEXT = 'text', 'متن'
        VOICE = 'voice', 'صدا'
        PHOTO = 'photo', 'عکس'
        VIDEO = 'video', 'ویدیو'
        DOCUMENT = 'document', 'فایل'
        CONTACT = 'contact', 'مخاطب'
        OTHER = 'other', 'سایر'

    subscriber = models.ForeignKey(
        Subscriber,
        on_delete=models.CASCADE,
        related_name='inbound_messages',
    )
    kind = models.CharField(max_length=32, choices=MessageKind.choices)
    text = models.TextField(blank=True, default='')
    file_id = models.CharField(max_length=512, blank=True, default='')
    local_file = models.FileField(upload_to='inbound/%Y/%m/', blank=True, null=True)
    messenger_message_id = models.BigIntegerField(null=True, blank=True)
    is_support_request = models.BooleanField(
        default=False,
        help_text='اگر این پیام در جریان «پیام به پشتیبانی» ثبت شده باشد روشن است.',
    )
    is_support_read = models.BooleanField(
        default=False,
        help_text='فقط برای پیام‌های پشتیبانی: آیا توسط ادمین دیده شده است؟',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.kind} @ {self.created_at}'


class SupportTicketMessage(models.Model):
    class Sender(models.TextChoices):
        USER = 'user', 'کاربر'
        ADMIN = 'admin', 'ادمین'

    class MessageKind(models.TextChoices):
        TEXT = 'text', 'متن'
        PHOTO = 'photo', 'عکس'
        VIDEO = 'video', 'ویدیو'
        VOICE = 'voice', 'صدا'
        DOCUMENT = 'document', 'فایل'
        OTHER = 'other', 'سایر'

    subscriber = models.ForeignKey(
        Subscriber,
        on_delete=models.CASCADE,
        related_name='support_ticket_messages',
    )
    sender = models.CharField(max_length=16, choices=Sender.choices)
    kind = models.CharField(max_length=32, choices=MessageKind.choices, default=MessageKind.TEXT)
    text = models.TextField(blank=True, default='')
    file_id = models.CharField(max_length=512, blank=True, default='')
    inbound_message = models.ForeignKey(
        InboundMessage,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='support_ticket_items',
    )
    parent_user_message = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='admin_replies',
        help_text='برای پاسخ ادمین: پیام کاربرِ مبنای این تیکت.',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f'{self.subscriber_id}:{self.sender}:{self.kind}'


class CallbackLog(models.Model):
    subscriber = models.ForeignKey(
        Subscriber,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='callback_logs',
    )
    callback_query_id = models.CharField(max_length=128, db_index=True)
    data = models.CharField(max_length=256, blank=True, default='')
    campaign = models.ForeignKey(
        'Campaign',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='callback_logs',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']


class Campaign(models.Model):
    class ContentType(models.TextChoices):
        TEXT = 'text', 'متن'
        TEXT_BUTTONS = 'text_buttons', 'متن + دکمهٔ اینلاین'
        PHOTO = 'photo', 'عکس'
        VIDEO = 'video', 'ویدیو'
        VOICE = 'voice', 'صدا'
        DOCUMENT = 'document', 'فایل'

    class Status(models.TextChoices):
        DRAFT = 'draft', 'پیش‌نویس'
        QUEUED = 'queued', 'در صف'
        SENDING = 'sending', 'در حال ارسال'
        COMPLETED = 'completed', 'تمام‌شده'
        CANCELLED = 'cancelled', 'لغوشده'

    class ScheduleKind(models.TextChoices):
        INSTANT = 'instant', 'آنی'
        SCHEDULED = 'scheduled', 'زمان‌بندی‌شده'

    workspace = models.ForeignKey(
        Workspace,
        on_delete=models.CASCADE,
        related_name='campaigns',
        db_index=True,
    )
    platform = models.CharField(
        max_length=16,
        choices=Platform.choices,
        default=Platform.BALE,
        db_index=True,
    )
    title = models.CharField(max_length=255, verbose_name='عنوان کمپین')
    content_type = models.CharField(
        max_length=32,
        choices=ContentType.choices,
        verbose_name='نوع محتوا',
    )
    body = models.TextField(
        blank=True,
        default='',
        verbose_name='متن پیام',
        help_text='متن اصلی پیام یا زیرنویس رسانه',
    )
    media = models.FileField(
        upload_to='campaigns/%Y/%m/',
        blank=True,
        null=True,
        verbose_name='فایل',
        help_text='برای عکس، ویدیو یا فایل — بسته به نوع محتوا',
    )
    inline_keyboard = models.JSONField(
        default=list,
        blank=True,
        help_text='لیست ردیف‌ها: هر ردیف آرایه‌ای از {text, callback_data}',
    )
    target_tags = models.ManyToManyField(
        Tag,
        related_name='campaigns',
        blank=True,
        help_text='اگر انتخاب شود، کمپین فقط برای اعضای همین برچسب‌ها صف می‌شود.',
    )
    audience_snapshot = models.JSONField(
        default=list,
        blank=True,
        help_text='شناسهٔ مشترکین نهایی این کمپین در زمان صف‌بندی.',
    )
    audience_snapshot_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(
        max_length=32,
        choices=Status.choices,
        default=Status.DRAFT,
        db_index=True,
    )
    schedule_kind = models.CharField(
        max_length=16,
        choices=ScheduleKind.choices,
        default=ScheduleKind.INSTANT,
        verbose_name='نوع زمان ارسال',
        help_text='آنی: بلافاصله پس از قرار گرفتن در صف؛ زمان‌بندی‌شده: در تاریخ و ساعت شمسی تعیین‌شده.',
    )
    scheduled_at = models.DateTimeField(null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        from django.urls import reverse

        return reverse('campaign_detail', kwargs={'pk': self.pk})

    @property
    def scheduled_at_jalali_display(self) -> str:
        if not self.scheduled_at:
            return ''
        from balebot.services.jalali_datetime import aware_to_jalali_parts

        d, t = aware_to_jalali_parts(self.scheduled_at)
        return f'{d}، ساعت {t}'


class CampaignDelivery(models.Model):
    class DeliveryStatus(models.TextChoices):
        PENDING = 'pending', 'در انتظار'
        SENT = 'sent', 'ارسال‌شده'
        FAILED = 'failed', 'خطا'

    campaign = models.ForeignKey(
        Campaign,
        on_delete=models.CASCADE,
        related_name='deliveries',
    )
    subscriber = models.ForeignKey(
        Subscriber,
        on_delete=models.CASCADE,
        related_name='campaign_deliveries',
    )
    status = models.CharField(
        max_length=16,
        choices=DeliveryStatus.choices,
        default=DeliveryStatus.PENDING,
        db_index=True,
    )
    error_message = models.TextField(blank=True, default='')
    sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['campaign', 'subscriber'],
                name='unique_campaign_subscriber_delivery',
            ),
        ]

    def __str__(self):
        return f'{self.campaign_id} → {self.subscriber_id} ({self.status})'


class SubscriberTag(models.Model):
    subscriber = models.ForeignKey(
        Subscriber,
        on_delete=models.CASCADE,
        related_name='subscriber_tags',
    )
    tag = models.ForeignKey(
        Tag,
        on_delete=models.CASCADE,
        related_name='subscriber_tags',
    )
    assigned_by = models.ForeignKey(
        'auth.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_subscriber_tags',
    )
    assigned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-assigned_at']
        constraints = [
            models.UniqueConstraint(
                fields=['subscriber', 'tag'],
                name='unique_subscriber_tag',
            ),
        ]

    def __str__(self):
        return f'{self.subscriber_id}:{self.tag_id}'


class ClassEnrollmentRequest(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', 'در انتظار'
        APPROVED = 'approved', 'تایید شده'
        REJECTED = 'rejected', 'رد شده'

    subscriber = models.ForeignKey(
        Subscriber,
        on_delete=models.CASCADE,
        related_name='enrollment_requests',
    )
    tag = models.ForeignKey(
        Tag,
        on_delete=models.CASCADE,
        related_name='enrollment_requests',
        limit_choices_to={'tag_type': Tag.TagType.CLASS},
    )
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )
    note = models.CharField(max_length=500, blank=True, default='')
    requested_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(
        'auth.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_enrollment_requests',
    )

    class Meta:
        ordering = ['-requested_at']
        indexes = [
            models.Index(fields=['status', 'requested_at']),
        ]

    def __str__(self):
        return f'{self.subscriber_id}:{self.tag_id}:{self.status}'


class BotSettings(models.Model):
    """تنظیمات هر پلتفرم (بله / تلگرام) — یک رکورد به ازای هر workspace+platform."""

    workspace = models.ForeignKey(
        Workspace,
        on_delete=models.CASCADE,
        related_name='bot_settings',
        db_index=True,
    )
    platform = models.CharField(
        max_length=16,
        choices=Platform.choices,
        db_index=True,
    )
    bot_token = models.CharField(
        max_length=256,
        blank=True,
        default='',
        verbose_name='توکن ربات',
        help_text='از BotFather دریافت می‌شود.',
    )
    webhook_secret = models.CharField(
        max_length=128,
        blank=True,
        default='',
        unique=True,
        verbose_name='رمز وب‌هوک',
        help_text='بخش secret در URL وب‌هوک.',
    )
    webhook_public_url = models.URLField(
        blank=True,
        default='',
        verbose_name='آدرس عمومی سرور',
        help_text='مثلاً https://example.com — بدون اسلش پایانی.',
    )
    is_enabled = models.BooleanField(
        default=True,
        verbose_name='فعال',
        help_text='اگر خاموش باشد وب‌هوک پاسخ نمی‌دهد.',
    )

    panel_brand_title = models.CharField(
        max_length=120,
        default='کنترل بازو',
        verbose_name='عنوان پنل (نوار کناری)',
    )
    panel_brand_subtitle = models.CharField(
        max_length=180,
        blank=True,
        default='مدیریت کمپین و مخاطبان',
        verbose_name='زیرعنوان پنل',
    )

    start_message_normal = models.TextField(
        blank=True,
        default='',
        verbose_name='پیام /start معمولی',
        help_text=(
            'منسوخ — خوش‌آمد را در طراحی منوی /start قرار دهید. '
            'فقط وقتی منو خالی است و این فیلد پر باشد ارسال می‌شود.'
        ),
    )
    contact_button_label = models.CharField(
        max_length=64,
        default='ارسال شماره تماس',
        verbose_name='برچسب دکمهٔ تماس',
    )
    registration_success_message = models.TextField(
        default=(
            'ثبت‌نام با موفقیت انجام شد. می‌توانید از طریق همین بازو '
            'پیام‌های ما را دریافت کنید.'
        ),
        verbose_name='پیام پس از دریافت شماره',
    )
    unsubscribe_message = models.TextField(
        default=(
            'اشتراک شما غیرفعال شد. هر زمان بخواهید دوباره /start بزنید.'
        ),
        verbose_name='پیام خروج (/stop)',
    )
    callback_ack_message = models.CharField(
        max_length=200,
        default='ثبت شد',
        verbose_name='اعلان کوتاه پس از کلیک دکمهٔ اینلاین',
    )

    help_message = models.TextField(
        blank=True,
        default='راهنما: با /start ثبت‌نام کنید. با /stop اطلاعیه‌ها را قطع کنید.',
        verbose_name='متن دستور /help',
    )

    start_inline_keyboard = models.JSONField(
        default=dict,
        blank=True,
        help_text='(منسوخ) — از start_flow استفاده کنید.',
    )
    start_flow = models.JSONField(
        default=dict,
        blank=True,
        help_text='جریان پس از /start: sequence از متن، عکس و دکمه با اکشن‌های تو در تو.',
    )
    start_flow_default_text = models.TextField(
        blank=True,
        default='گزینه‌ای برای ادامه در دسترس نیست.',
        verbose_name='متن پیش‌فرض جریان (بن‌بست)',
        help_text='وقتی مسیر دکمه به جایی وصل نیست یا اکشن نامعتبر است.',
    )
    start_message_contact = models.TextField(
        default=(
            'سلام! برای تکمیل ثبت‌نام و دریافت اطلاعیه‌ها، شمارهٔ خود را '
            'با دکمهٔ زیر ارسال کنید.'
        ),
        verbose_name='پیام /start هنگام درخواست شماره',
        help_text=(
            'فقط برای کاربرانی که هنوز شماره نداده‌اند، وقتی گزینهٔ دریافت شماره روشن باشد. '
            'اگر منوی اینلاین هم دارید، این متن در پیام اول با اینلاین می‌آید؛ پیام بعد فقط دکمهٔ تماس است.'
        ),
    )

    collect_contact_on_start = models.BooleanField(
        default=False,
        verbose_name='نمایش دکمهٔ ارسال شماره بعد از /start',
    )
    enable_help_command = models.BooleanField(
        default=True,
        verbose_name='فعال بودن دستور /help',
    )
    enable_stop_command = models.BooleanField(
        default=True,
        verbose_name='فعال بودن دستور /stop',
    )
    enable_support = models.BooleanField(
        default=False,
        verbose_name='فعال بودن پشتیبانی',
    )
    support_button_label = models.CharField(
        max_length=64,
        default='پیام به پشتیبانی',
        verbose_name='برچسب دکمهٔ پشتیبانی',
    )
    support_start_prompt_message = models.TextField(
        default='برای ارسال پیام به پشتیبانی روی دکمهٔ زیر بزنید.',
        verbose_name='متن راهنمای شروع پشتیبانی',
    )
    support_waiting_message = models.TextField(
        default='پیام شما ثبت شد. لطفاً منتظر پاسخ پشتیبانی باشید.',
        verbose_name='پیام ثبت درخواست پشتیبانی',
    )

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'تنظیمات بازو'
        verbose_name_plural = 'تنظیمات بازو'
        constraints = [
            models.UniqueConstraint(
                fields=['workspace', 'platform'],
                name='unique_botsettings_workspace_platform',
            ),
        ]

    def __str__(self):
        return f'{self.workspace_id} — {self.get_platform_display()}'

    @classmethod
    def _defaults_for_platform(cls, platform: str) -> dict:
        brand = 'کنترل بازو' if platform == Platform.BALE else 'کنترل تلگرام'
        return {
            'platform': platform,
            'panel_brand_title': brand,
            'panel_brand_subtitle': 'مدیریت کمپین و مخاطبان',
        }

    @classmethod
    def get_for_platform(cls, workspace: Workspace, platform: str):
        platform = Platform.TELEGRAM if platform == Platform.TELEGRAM else Platform.BALE
        defaults = cls._defaults_for_platform(platform)
        if not defaults.get('webhook_secret'):
            defaults['webhook_secret'] = generate_webhook_secret()
        obj, _ = cls.objects.get_or_create(
            workspace=workspace,
            platform=platform,
            defaults=defaults,
        )
        return obj

    @classmethod
    def ensure_for_workspace(cls, workspace: Workspace) -> None:
        for platform in (Platform.BALE, Platform.TELEGRAM):
            cls.get_for_platform(workspace, platform)

    @classmethod
    def get_solo(cls):
        """سازگاری با کد قدیمی — اولین workspace و تنظیمات بله."""
        ws = Workspace.objects.order_by('id').first()
        if ws is None:
            raise cls.DoesNotExist('هیچ workspaceای وجود ندارد.')
        return cls.get_for_platform(ws, Platform.BALE)

    def masked_bot_token(self) -> str:
        token = (self.bot_token or '').strip()
        if not token:
            return ''
        if len(token) <= 8:
            return '••••••••'
        return f'{token[:4]}…{token[-4:]}'

    def build_webhook_url(self) -> str:
        from balebot.services.public_url import resolve_public_base_url

        base = resolve_public_base_url(self).rstrip('/')
        secret = (self.webhook_secret or '').strip()
        if not base or not secret:
            return ''
        return f'{base}/webhook/{self.platform}/{secret}/'

    def has_bot_token(self) -> bool:
        return bool((self.bot_token or '').strip())


def default_catalog_theme() -> dict:
    return {
        'primary_color': '#2563eb',
        'accent_color': '#7c3aed',
        'layout': 'grid',
        'font_family': 'Vazirmatn',
    }


def default_catalog_labels() -> dict:
    return {
        'buy_now': 'خرید',
        'add_to_cart': 'افزودن به سبد',
        'request_quote': 'درخواست / تماس',
        'cart': 'سبد خرید',
        'checkout': 'تسویه',
        'download': 'دانلود',
        'remove_from_cart': 'حذف',
    }


def default_checkout_form() -> dict:
    from balebot.services.checkout_form import default_checkout_form as _default

    return _default()


class CatalogSettings(models.Model):
    workspace = models.ForeignKey(
        Workspace,
        on_delete=models.CASCADE,
        related_name='catalog_settings',
        db_index=True,
    )
    platform = models.CharField(
        max_length=16,
        choices=Platform.choices,
        default=Platform.BALE,
        db_index=True,
    )
    public_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    is_enabled = models.BooleanField(default=False, verbose_name='فعال')

    class PaymentMethod(models.TextChoices):
        ADMIN_CART = 'admin_cart', 'ارسال سبد به ادمین'
        CARD_TO_CARD = 'card_to_card', 'کارت به کارت'
        BALE = 'bale', 'پرداخت بله'

    payment_admin_enabled = models.BooleanField(
        default=False,
        verbose_name='فعال‌سازی ارسال سبد به ادمین',
    )
    payment_card_to_card_enabled = models.BooleanField(
        default=False,
        verbose_name='فعال‌سازی کارت به کارت',
    )
    payment_bale_enabled = models.BooleanField(
        default=False,
        verbose_name='فعال‌سازی پرداخت بله',
    )
    bale_payment_card_number = models.CharField(
        max_length=32,
        blank=True,
        default='',
        verbose_name='شماره کارت فروشنده (بله)',
        help_text='به‌عنوان provider_token در sendInvoice استفاده می‌شود.',
    )
    bale_payment_card_holder = models.CharField(
        max_length=128,
        blank=True,
        default='',
        verbose_name='نام دارنده کارت',
    )
    payment_default_method = models.CharField(
        max_length=16,
        choices=PaymentMethod.choices,
        default=PaymentMethod.ADMIN_CART,
        verbose_name='روش پرداخت پیش‌فرض',
    )
    admin_notify_chat_id = models.BigIntegerField(
        null=True,
        blank=True,
        verbose_name='چت‌آیدی ادمین برای سفارش‌ها',
        help_text='شناسه گفتگوی ادمین در بله/تلگرام برای دریافت سبد خرید.',
    )
    card_to_card_number = models.CharField(
        max_length=32,
        blank=True,
        default='',
        verbose_name='شماره کارت',
    )
    card_to_card_sheba = models.CharField(
        max_length=34,
        blank=True,
        default='',
        verbose_name='شماره شبا',
    )
    card_to_card_holder = models.CharField(
        max_length=128,
        blank=True,
        default='',
        verbose_name='نام صاحب حساب',
    )
    provider_token = models.CharField(
        max_length=256,
        blank=True,
        default='',
        verbose_name='توکن پرداخت (منسوخ)',
        help_text='دیگر استفاده نمی‌شود؛ از زرین‌پال یا ارسال به ادمین استفاده کنید.',
    )
    hero_title = models.CharField(max_length=200, blank=True, default='')
    hero_subtitle = models.CharField(max_length=300, blank=True, default='')
    logo = models.ImageField(upload_to='catalog/%Y/%m/', blank=True, null=True)
    hero_background = models.ImageField(
        upload_to='catalog/%Y/%m/',
        blank=True,
        null=True,
        verbose_name='تصویر پس‌زمینه هیرو',
    )
    theme_config = models.JSONField(default=default_catalog_theme, blank=True)
    labels = models.JSONField(default=default_catalog_labels, blank=True)
    checkout_form = models.JSONField(default=default_checkout_form, blank=True)
    require_channel_membership = models.BooleanField(
        default=False,
        verbose_name='الزام عضویت در کانال',
    )
    required_channel_id = models.CharField(
        max_length=128,
        blank=True,
        default='',
        verbose_name='شناسه کانال',
        help_text='@username کانال یا شناسه عددی. ربات باید ادمین کانال باشد.',
    )
    channel_membership_message = models.TextField(
        blank=True,
        default='برای استفاده از مینی‌اپ ابتدا در کانال ما عضو شوید.',
        verbose_name='پیام عضویت کانال',
    )
    channel_invite_link = models.URLField(
        blank=True,
        default='',
        verbose_name='لینک پیوستن به کانال',
    )
    class ShippingMode(models.TextChoices):
        FREE = 'free', 'رایگان'
        FLAT = 'flat', 'ثابت'
        BY_PROVINCE = 'by_province', 'بر اساس استان'

    shipping_mode = models.CharField(
        max_length=20,
        choices=ShippingMode.choices,
        default=ShippingMode.FLAT,
        verbose_name='روش محاسبه ارسال',
    )
    shipping_flat_cost = models.BigIntegerField(
        default=0,
        verbose_name='هزینه ثابت ارسال (ریال)',
    )
    free_shipping_threshold = models.BigIntegerField(
        null=True,
        blank=True,
        verbose_name='آستانه ارسال رایگان (ریال)',
    )
    shipping_by_province = models.JSONField(
        default=dict,
        blank=True,
        verbose_name='هزینه ارسال به تفکیک استان',
    )
    order_notify_shipped_template = models.TextField(
        blank=True,
        default='سفارش شما ارسال شد 📦 کد رهگیری: {tracking_code}',
        verbose_name='پیام وضعیت «ارسال‌شده»',
    )
    order_notify_delivered_template = models.TextField(
        blank=True,
        default='سفارش شما تحویل داده شد. ممنون از خریدتان 🌹',
        verbose_name='پیام وضعیت «تحویل‌شده»',
    )
    abandoned_cart_message_template = models.TextField(
        blank=True,
        default='سبد خریدت منتظرته 🛍 با کد {code} ۱۰٪ تخفیف بگیر.',
        verbose_name='پیام سبد رها‌شده',
    )
    abandoned_cart_hours = models.PositiveIntegerField(
        default=24,
        verbose_name='ساعت انتظار قبل از یادآوری سبد',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'تنظیمات فروشگاه'
        verbose_name_plural = 'تنظیمات فروشگاه'
        constraints = [
            models.UniqueConstraint(
                fields=['workspace', 'platform'],
                name='unique_catalog_settings_workspace_platform',
            ),
        ]

    def __str__(self):
        return f'فروشگاه {self.workspace_id} — {self.get_platform_display()}'

    @classmethod
    def get_for_platform(cls, workspace: Workspace, platform: str):
        platform = Platform.TELEGRAM if platform == Platform.TELEGRAM else Platform.BALE
        obj, _ = cls.objects.get_or_create(
            workspace=workspace,
            platform=platform,
            defaults={'platform': platform},
        )
        return obj

    def build_mini_app_url(self, bot_settings: BotSettings | None = None) -> str:
        if not bot_settings:
            return ''
        from balebot.services.public_url import resolve_public_base_url

        base = resolve_public_base_url(bot_settings).rstrip('/')
        if not base:
            return ''
        return f'{base}/shop/{self.public_id}/'

    def payment_admin_ready(self) -> bool:
        return bool(self.payment_admin_enabled and self.admin_notify_chat_id)

    def payment_card_to_card_ready(self) -> bool:
        from balebot.services.card_to_card import payment_card_to_card_ready

        return payment_card_to_card_ready(self)

    def payment_bale_ready(self) -> bool:
        card = (self.bale_payment_card_number or '').strip()
        if not self.payment_bale_enabled or not card:
            return False
        digits = ''.join(ch for ch in card if ch.isdigit())
        return len(digits) >= 16

    def enabled_payment_methods(self) -> list[tuple[str, str]]:
        methods: list[tuple[str, str]] = []
        if self.payment_admin_ready():
            methods.append((self.PaymentMethod.ADMIN_CART, self.PaymentMethod.ADMIN_CART.label))
        if self.payment_card_to_card_ready():
            methods.append((self.PaymentMethod.CARD_TO_CARD, self.PaymentMethod.CARD_TO_CARD.label))
        if self.payment_bale_ready() and self.platform == Platform.BALE:
            methods.append((self.PaymentMethod.BALE, self.PaymentMethod.BALE.label))
        return methods

    def is_payment_ready(self) -> bool:
        return bool(self.enabled_payment_methods())

    def can_accept_orders(self) -> bool:
        return self.is_enabled and self.is_payment_ready()

    def resolve_payment_method(self, requested: str | None) -> str | None:
        enabled = {m[0] for m in self.enabled_payment_methods()}
        if not enabled:
            return None
        if requested and requested in enabled:
            return requested
        default = self.payment_default_method
        if default in enabled:
            return default
        return next(iter(enabled))


class CatalogCategory(models.Model):
    workspace = models.ForeignKey(
        Workspace,
        on_delete=models.CASCADE,
        related_name='catalog_categories',
        db_index=True,
    )
    platform = models.CharField(
        max_length=16,
        choices=Platform.choices,
        default=Platform.BALE,
        db_index=True,
    )
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='children',
    )
    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=140)
    icon = models.CharField(max_length=64, blank=True, default='')
    image = models.ImageField(upload_to='catalog/categories/%Y/%m/', blank=True, null=True)
    sort_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['sort_order', 'name']
        verbose_name = 'دسته فروشگاه'
        verbose_name_plural = 'دسته‌های فروشگاه'
        constraints = [
            models.UniqueConstraint(
                fields=['workspace', 'platform', 'slug'],
                name='unique_catalog_category_slug',
            ),
        ]

    def __str__(self):
        return self.name


class CatalogItem(models.Model):
    class ItemType(models.TextChoices):
        PRODUCT = 'product', 'محصول'
        DOWNLOAD = 'download', 'فایل دانلود'
        VIDEO = 'video', 'ویدیو و آموزش'
        SHOWCASE = 'showcase', 'معرفی و نمونه‌کار'

    class SaleMode(models.TextChoices):
        BUYABLE = 'buyable', 'قابل خرید'
        REQUEST_ONLY = 'request_only', 'فقط درخواست'
        BOTH = 'both', 'خرید و درخواست'

    workspace = models.ForeignKey(
        Workspace,
        on_delete=models.CASCADE,
        related_name='catalog_items',
        db_index=True,
    )
    platform = models.CharField(
        max_length=16,
        choices=Platform.choices,
        default=Platform.BALE,
        db_index=True,
    )
    category = models.ForeignKey(
        CatalogCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='items',
    )
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220)
    short_description = models.CharField(max_length=300, blank=True, default='')
    description = models.TextField(blank=True, default='')
    item_type = models.CharField(
        max_length=16,
        choices=ItemType.choices,
        default=ItemType.PRODUCT,
    )
    price = models.PositiveBigIntegerField(
        null=True,
        blank=True,
        help_text='قیمت به ریال',
    )
    compare_at_price = models.PositiveBigIntegerField(
        null=True,
        blank=True,
        help_text='قیمت قبل از تخفیف (برای نمایش خط‌خورده)',
    )
    sales_count = models.PositiveIntegerField(
        default=0,
        help_text='تعداد فروش موفق (برای پرفروش‌ترین‌ها)',
    )
    sale_mode = models.CharField(
        max_length=16,
        choices=SaleMode.choices,
        default=SaleMode.BOTH,
    )
    stock = models.PositiveIntegerField(null=True, blank=True)
    cover = models.ImageField(
        upload_to='catalog/items/covers/%Y/%m/',
        blank=True,
        null=True,
        help_text='تصویر کاور برای نمایش (مخصوص فایل دانلود)',
    )
    download_file = models.FileField(
        upload_to='catalog/items/downloads/%Y/%m/',
        blank=True,
        null=True,
        help_text='فایل اصلی قابل دانلود (آپلود روی سرور)',
    )
    download_link = models.URLField(
        max_length=500,
        blank=True,
        default='',
        help_text='لینک مستقیم دانلود (گوگل‌درایو، دراپ‌باکس و...)',
    )
    metadata = models.JSONField(default=dict, blank=True)
    is_flash_sale = models.BooleanField(
        default=False,
        help_text='نمایش در بخش حراج مینی‌اپ',
    )
    flash_sale_starts_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='شروع حراج (اختیاری)',
    )
    flash_sale_ends_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='پایان حراج (اختیاری)',
    )
    is_active = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    sort_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['sort_order', '-created_at']
        verbose_name = 'آیتم فروشگاه'
        verbose_name_plural = 'آیتم‌های فروشگاه'
        constraints = [
            models.UniqueConstraint(
                fields=['workspace', 'platform', 'slug'],
                name='unique_catalog_item_slug',
            ),
        ]

    def __str__(self):
        return self.title

    def normalized_item_type(self) -> str:
        if self.item_type == 'portfolio':
            return self.ItemType.SHOWCASE
        if self.item_type == 'service':
            return self.ItemType.SHOWCASE
        return self.item_type

    def is_downloadable(self) -> bool:
        if self.normalized_item_type() != self.ItemType.DOWNLOAD:
            return False
        return bool(self.download_file) or bool((self.download_link or '').strip())

    def resolve_download_url(self, request=None, catalog=None) -> str:
        if self.download_file:
            from balebot.services.catalog_media import absolute_media_url

            return absolute_media_url(request, self.download_file.url, catalog=catalog)
        return (self.download_link or '').strip()

    def is_buyable(self) -> bool:
        item_type = self.normalized_item_type()
        if item_type in (self.ItemType.DOWNLOAD, self.ItemType.SHOWCASE):
            return False
        if self.sale_mode == self.SaleMode.REQUEST_ONLY:
            return False
        return self.price is not None and self.price > 0

    def is_requestable(self) -> bool:
        item_type = self.normalized_item_type()
        if item_type == self.ItemType.DOWNLOAD:
            return False
        if item_type == self.ItemType.SHOWCASE:
            return True
        return self.sale_mode in (self.SaleMode.REQUEST_ONLY, self.SaleMode.BOTH)

    def first_image(self):
        for media in self.media.all():
            if media.media_type == 'image':
                return media
        return None

    def is_flash_sale_active(self, at=None) -> bool:
        if not self.is_flash_sale:
            return False
        at = at or timezone.now()
        if self.flash_sale_starts_at and at < self.flash_sale_starts_at:
            return False
        if self.flash_sale_ends_at and at > self.flash_sale_ends_at:
            return False
        return True


class CatalogItemMedia(models.Model):
    class MediaType(models.TextChoices):
        IMAGE = 'image', 'تصویر'
        VIDEO = 'video', 'ویدیو'
        FILE = 'file', 'فایل'

    item = models.ForeignKey(
        CatalogItem,
        on_delete=models.CASCADE,
        related_name='media',
    )
    file = models.FileField(upload_to='catalog/items/%Y/%m/')
    media_type = models.CharField(
        max_length=8,
        choices=MediaType.choices,
        default=MediaType.IMAGE,
    )
    title = models.CharField(max_length=200, blank=True, default='')
    sort_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['sort_order', 'id']
        verbose_name = 'رسانه آیتم'
        verbose_name_plural = 'رسانه‌های آیتم'

    def __str__(self):
        return f'{self.item_id} — {self.media_type} — {self.sort_order}'


def _order_public_token() -> str:
    return uuid.uuid4().hex


class CatalogOrder(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', 'در انتظار پرداخت'
        PAID = 'paid', 'پرداخت‌شده'
        FAILED = 'failed', 'ناموفق'
        CANCELLED = 'cancelled', 'لغوشده'
        REQUEST = 'request', 'درخواست'

    workspace = models.ForeignKey(
        Workspace,
        on_delete=models.CASCADE,
        related_name='catalog_orders',
        db_index=True,
    )
    platform = models.CharField(
        max_length=16,
        choices=Platform.choices,
        default=Platform.BALE,
        db_index=True,
    )
    subscriber = models.ForeignKey(
        'Subscriber',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='catalog_orders',
    )
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )
    class FulfillmentStatus(models.TextChoices):
        PENDING = 'pending', 'در انتظار پرداخت'
        PAID = 'paid', 'پرداخت‌شده'
        PREPARING = 'preparing', 'در حال آماده‌سازی'
        SHIPPED = 'shipped', 'ارسال‌شده'
        DELIVERED = 'delivered', 'تحویل‌شده'
        CANCELLED = 'cancelled', 'لغو‌شده'
        RETURNED = 'returned', 'مرجوعی'

    fulfillment_status = models.CharField(
        max_length=20,
        choices=FulfillmentStatus.choices,
        default=FulfillmentStatus.PENDING,
        db_index=True,
    )
    tracking_code = models.CharField(max_length=64, blank=True, default='')
    customer_note = models.TextField(blank=True, default='')
    admin_note = models.TextField(blank=True, default='')
    recipient_name = models.CharField(max_length=120, blank=True, default='')
    recipient_phone = models.CharField(max_length=20, blank=True, default='')
    recipient_address = models.TextField(blank=True, default='')
    recipient_postal_code = models.CharField(max_length=20, blank=True, default='')
    shipping_cost = models.BigIntegerField(default=0)
    discount_code = models.CharField(max_length=40, blank=True, default='')
    discount_amount = models.BigIntegerField(default=0)
    public_token = models.CharField(
        max_length=64,
        unique=True,
        default=_order_public_token,
        editable=False,
        db_index=True,
    )
    total_amount = models.PositiveBigIntegerField(default=0)
    currency = models.CharField(max_length=8, default='IRR')
    payment_method = models.CharField(max_length=16, blank=True, default='')
    payment_charge_id = models.CharField(max_length=256, blank=True, default='')
    payment_receipt = models.ImageField(upload_to='catalog/receipts/%Y/%m/', blank=True, null=True)
    receipt_uploaded_at = models.DateTimeField(null=True, blank=True)
    note = models.TextField(blank=True, default='')
    customer_data = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'سفارش فروشگاه'
        verbose_name_plural = 'سفارش‌های فروشگاه'

    def __str__(self):
        return f'سفارش #{self.pk}'


class CatalogOrderLine(models.Model):
    order = models.ForeignKey(
        CatalogOrder,
        on_delete=models.CASCADE,
        related_name='lines',
    )
    item = models.ForeignKey(
        CatalogItem,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    title_snapshot = models.CharField(max_length=200)
    price_snapshot = models.PositiveBigIntegerField(default=0)
    quantity = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ['id']

    def __str__(self):
        return self.title_snapshot

    @property
    def line_total(self) -> int:
        return self.price_snapshot * self.quantity


class CatalogCart(models.Model):
    workspace = models.ForeignKey(
        Workspace,
        on_delete=models.CASCADE,
        related_name='catalog_carts',
    )
    platform = models.CharField(
        max_length=16,
        choices=Platform.choices,
        default=Platform.BALE,
    )
    subscriber = models.ForeignKey(
        'Subscriber',
        on_delete=models.CASCADE,
        related_name='catalog_carts',
    )
    reminder_sent_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['workspace', 'platform', 'subscriber'],
                name='unique_catalog_cart_per_subscriber',
            ),
        ]

    def __str__(self):
        return f'سبد {self.subscriber_id}'


class CatalogCartItem(models.Model):
    cart = models.ForeignKey(
        CatalogCart,
        on_delete=models.CASCADE,
        related_name='items',
    )
    catalog_item = models.ForeignKey(
        CatalogItem,
        on_delete=models.CASCADE,
        related_name='cart_entries',
    )
    quantity = models.PositiveIntegerField(default=1)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['cart', 'catalog_item'],
                name='unique_cart_catalog_item',
            ),
        ]

    def __str__(self):
        return f'{self.catalog_item_id} x{self.quantity}'


class StoreTemplate(models.Model):
    """الگوی آماده فروشگاه — سراسری (بدون workspace)."""

    slug = models.SlugField(unique=True, max_length=80)
    name = models.CharField(max_length=120)
    industry = models.CharField(max_length=60, db_index=True)
    description = models.CharField(max_length=255, blank=True, default='')
    preview_image = models.ImageField(upload_to='store_templates/', blank=True)
    data = models.JSONField(default=dict, blank=True)
    sort_order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['sort_order', 'name']
        verbose_name = 'الگوی فروشگاه'
        verbose_name_plural = 'الگوهای فروشگاه'

    def __str__(self):
        return self.name


class DiscountCode(models.Model):
    class Kind(models.TextChoices):
        PERCENT = 'percent', 'درصدی'
        AMOUNT = 'amount', 'مبلغی'

    workspace = models.ForeignKey(
        Workspace,
        on_delete=models.CASCADE,
        related_name='discount_codes',
        db_index=True,
    )
    platform = models.CharField(
        max_length=16,
        choices=Platform.choices,
        default=Platform.BALE,
        db_index=True,
    )
    code = models.CharField(max_length=40)
    kind = models.CharField(max_length=10, choices=Kind.choices)
    value = models.BigIntegerField(help_text='درصد یا مبلغ به ریال')
    max_uses = models.IntegerField(null=True, blank=True)
    used_count = models.IntegerField(default=0)
    min_order_amount = models.BigIntegerField(default=0)
    max_discount_amount = models.BigIntegerField(
        null=True,
        blank=True,
        help_text='سقف مبلغ تخفیف به ریال (برای کدهای درصدی)',
    )
    first_purchase_only = models.BooleanField(
        default=False,
        help_text='فقط برای مشتری بدون سفارش پرداخت‌شده قبلی',
    )
    expires_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'کد تخفیف'
        verbose_name_plural = 'کدهای تخفیف'
        constraints = [
            models.UniqueConstraint(
                fields=['workspace', 'platform', 'code'],
                name='unique_discount_code_workspace_platform',
            ),
        ]

    def __str__(self):
        return self.code
