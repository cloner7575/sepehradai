from django.conf import settings as django_settings
from django.core.validators import FileExtensionValidator
from django.db import models

from landing.constants import MESSENGER_CHOICES


class Lead(models.Model):
    name = models.CharField(max_length=120, verbose_name='نام')
    business_name = models.CharField(max_length=160, blank=True, verbose_name='نام کسب‌وکار')
    phone = models.CharField(max_length=20, verbose_name='موبایل')
    messenger = models.CharField(
        max_length=20,
        choices=MESSENGER_CHOICES,
        blank=True,
        verbose_name='پیام‌رسان',
    )
    business_type = models.CharField(max_length=60, blank=True, verbose_name='صنف')
    business_type_other = models.CharField(
        max_length=80,
        blank=True,
        verbose_name='صنف (سایر)',
    )
    note = models.TextField(blank=True, verbose_name='توضیحات')
    source = models.CharField(max_length=60, default='landing', verbose_name='منبع')
    is_contacted = models.BooleanField(default=False, verbose_name='تماس گرفته شده')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاریخ ثبت')

    class Meta:
        verbose_name = 'سرنخ'
        verbose_name_plural = 'سرنخ‌ها'
        ordering = ['-created_at']

    def __str__(self) -> str:
        return f'{self.name} — {self.phone}'

    def get_messenger_display_fa(self) -> str:
        return dict(MESSENGER_CHOICES).get(self.messenger, self.messenger or '—')

    def business_type_display(self) -> str:
        label = (self.business_type or '').strip()
        other = (self.business_type_other or '').strip()
        if not label:
            return other or '—'
        if other:
            return f'{label} ({other})'
        return label


class BusinessCategory(models.Model):
    name = models.CharField(max_length=80, verbose_name='نام صنف')
    slug = models.SlugField(max_length=40, unique=True, verbose_name='شناسه')
    sort_order = models.PositiveSmallIntegerField(default=0, verbose_name='ترتیب')
    is_active = models.BooleanField(default=True, verbose_name='فعال در فرم لندینگ')
    show_on_landing = models.BooleanField(default=True, verbose_name='نمایش در بخش الگوها')
    is_other = models.BooleanField(
        default=False,
        verbose_name='گزینه سایر',
        help_text='فقط یک مورد می‌تواند گزینه «سایر» باشد.',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'صنف'
        verbose_name_plural = 'اصناف'
        ordering = ['sort_order', 'id']

    def __str__(self) -> str:
        return self.name


class LandingSettings(models.Model):
    """تنظیمات سراسری لندینگ — تک‌رکورد."""

    demo_bot_url = models.URLField(
        max_length=500,
        blank=True,
        default='',
        verbose_name='لینک ربات نمونه',
    )
    announce_text = models.CharField(
        max_length=200,
        default='راه‌اندازی فروشگاهت کمتر از ۱۰ دقیقه طول می‌کشه',
        verbose_name='نوار اعلان',
    )
    stats_label = models.CharField(
        max_length=200,
        default='مورد اعتماد فروشگاه‌های پوشاک، آرایشی، خوراکی و …',
        verbose_name='متن نوار آمار',
    )
    stat_stores = models.CharField(max_length=40, default='+۵۰', verbose_name='آمار فروشگاه')
    stat_orders = models.CharField(max_length=40, default='+۱۰۰۰', verbose_name='آمار سفارش')
    stat_setup_minutes = models.CharField(max_length=40, default='۱۰', verbose_name='آمار راه‌اندازی (دقیقه)')
    pricing_note = models.CharField(
        max_length=300,
        default='مطمئن نیستی کدوم مناسبته؟ یه دمو رایگان بگیر، با هم انتخاب می‌کنیم.',
        verbose_name='یادداشت بخش قیمت',
    )
    brand_icon_svg = models.FileField(
        upload_to='brand/',
        blank=True,
        validators=[FileExtensionValidator(['svg'])],
        verbose_name='آیکون برند (SVG)',
        help_text='آیکون مربعی برای سایدبار و هدر. فرمت SVG با پس‌زمینه شفاف.',
    )
    brand_logo_svg = models.FileField(
        upload_to='brand/',
        blank=True,
        validators=[FileExtensionValidator(['svg'])],
        verbose_name='لوگوی افقی (SVG)',
        help_text='اگر آپلود شود، به‌جای آیکون+متن نمایش داده می‌شود.',
    )
    brand_favicon_svg = models.FileField(
        upload_to='brand/',
        blank=True,
        validators=[FileExtensionValidator(['svg'])],
        verbose_name='فاوآیکون (SVG)',
        help_text='آیکون تب مرورگر. پیش‌فرض: آیکون برند.',
    )
    brand_wordmark_primary = models.CharField(
        max_length=40,
        default='Rahat',
        blank=True,
        verbose_name='متن وردمارک (بخش اول)',
    )
    brand_wordmark_accent = models.CharField(
        max_length=40,
        default='sell',
        blank=True,
        verbose_name='متن وردمارک (بخش دوم)',
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'تنظیمات لندینگ'
        verbose_name_plural = 'تنظیمات لندینگ'

    def __str__(self) -> str:
        return 'تنظیمات لندینگ'

    @classmethod
    def get_solo(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def resolved_demo_bot_url(self) -> str:
        url = (self.demo_bot_url or '').strip()
        if url:
            return url
        return getattr(django_settings, 'LANDING_DEMO_BOT_URL', '').strip()


class SubscriptionPlan(models.Model):
    class ButtonStyle(models.TextChoices):
        PRIMARY = 'primary', 'اصلی'
        OUTLINE = 'outline', 'حاشیه‌ای'

    name = models.CharField(max_length=80, verbose_name='نام پلن')
    slug = models.SlugField(max_length=40, unique=True, verbose_name='شناسه')
    price_label = models.CharField(
        max_length=40,
        verbose_name='مبلغ نمایشی',
        help_text='مثال: ۴۹۰٬۰۰۰',
    )
    price_period = models.CharField(
        max_length=40,
        default='تومان / ماه',
        verbose_name='دوره قیمت',
    )
    description = models.CharField(max_length=200, blank=True, verbose_name='توضیح کوتاه')
    features = models.JSONField(default=list, blank=True, verbose_name='امکانات')
    is_featured = models.BooleanField(default=False, verbose_name='پیشنهاد ویژه')
    is_active = models.BooleanField(default=True, verbose_name='فعال در لندینگ')
    sort_order = models.PositiveSmallIntegerField(default=0, verbose_name='ترتیب')
    button_style = models.CharField(
        max_length=16,
        choices=ButtonStyle.choices,
        default=ButtonStyle.OUTLINE,
        verbose_name='استایل دکمه',
    )
    cta_label = models.CharField(max_length=60, default='درخواست دمو', verbose_name='متن دکمه')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'پلن اشتراک'
        verbose_name_plural = 'پلن‌های اشتراک'
        ordering = ['sort_order', 'id']

    def __str__(self) -> str:
        return self.name

    def feature_list(self) -> list[str]:
        if not isinstance(self.features, list):
            return []
        return [str(item).strip() for item in self.features if str(item).strip()]
