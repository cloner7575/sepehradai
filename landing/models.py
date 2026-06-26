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
