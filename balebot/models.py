from django.db import models


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
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

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
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.kind} @ {self.created_at}'


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

    title = models.CharField(max_length=255)
    content_type = models.CharField(max_length=32, choices=ContentType.choices)
    body = models.TextField(blank=True, default='', help_text='متن یا زیرنویس رسانه')
    media = models.FileField(upload_to='campaigns/%Y/%m/', blank=True, null=True)
    inline_keyboard = models.JSONField(
        default=list,
        blank=True,
        help_text='لیست ردیف‌ها: هر ردیف آرایه‌ای از {text, callback_data}',
    )
    status = models.CharField(
        max_length=32,
        choices=Status.choices,
        default=Status.DRAFT,
        db_index=True,
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

    welcome_message = models.TextField(
        default=(
            'سلام! برای ثبت‌نام و دریافت اطلاعیه‌ها، شمارهٔ خود را '
            'با دکمهٔ زیر ارسال کنید.'
        ),
        verbose_name='پیام خوش‌آمدگویی (/start)',
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
    contact_prompt_message = models.TextField(
        blank=True,
        default='',
        verbose_name='پیام جدا برای درخواست شماره',
        help_text=(
            'وقتی هم دکمهٔ اینلاین /start و هم دکمهٔ تماس فعال باشد، این متن در پیام دوم '
            'قبل از صفحه‌کلید تماس ارسال می‌شود.'
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
