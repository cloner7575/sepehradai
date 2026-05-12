from django.db import models


class Tag(models.Model):
    class TagType(models.TextChoices):
        CLASS = 'class', 'کلاس'
        GENERIC = 'generic', 'عمومی'

    name = models.CharField(max_length=120, unique=True)
    slug = models.SlugField(max_length=140, unique=True)
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

    def __str__(self):
        return self.name


class Subscriber(models.Model):
    """کاربرانی که با بازو تعامل دارند."""

    bale_user_id = models.BigIntegerField(unique=True, db_index=True)
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

    def __str__(self):
        return f'{self.phone_number or self.bale_user_id}'


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
    bale_message_id = models.BigIntegerField(null=True, blank=True)
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
        DOCUMENT = 'document', 'سند'

    class Status(models.TextChoices):
        DRAFT = 'draft', 'پیش‌نویس'
        QUEUED = 'queued', 'در صف'
        SENDING = 'sending', 'در حال ارسال'
        COMPLETED = 'completed', 'تمام‌شده'
        CANCELLED = 'cancelled', 'لغوشده'

    class ScheduleKind(models.TextChoices):
        INSTANT = 'instant', 'آنی'
        SCHEDULED = 'scheduled', 'زمان‌بندی‌شده'

    title = models.CharField(max_length=255)
    content_type = models.CharField(max_length=32, choices=ContentType.choices)
    body = models.TextField(blank=True, default='', help_text='متن یا زیرنویس رسانه')
    media = models.FileField(upload_to='campaigns/%Y/%m/', blank=True, null=True)
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
    """یک رکورد ثابت (pk=1): متن‌ها و رفتار بازو از پنل قابل ویرایش است."""

    id = models.PositiveSmallIntegerField(primary_key=True, default=1, editable=False)

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
        default=(
            'سلام! خوش آمدید.\n'
            'می‌توانید از منوی زیر استفاده کنید و اطلاعیه‌ها را دریافت کنید.'
        ),
        verbose_name='پیام /start معمولی',
        help_text=(
            'برای کاربرانی که قبلاً شماره داده‌اند، یا وقتی گزینهٔ «دریافت شماره بعد از /start» خاموش است.'
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
        help_text='دکمه‌های اینلاین پس از /start: بخش‌ها و ردیف‌ها (همان ساختار کمپین) + نوع اکشن برای هر دکمه.',
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
        default=True,
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

    def __str__(self):
        return 'تنظیمات بازو'

    @classmethod
    def get_solo(cls):
        obj, _ = cls.objects.get_or_create(id=1)
        return obj
