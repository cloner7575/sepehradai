# استقرار بازو و پنل

## پیش‌نیاز

- پایتون ۳.۱۲+ (یا نسخه‌ای که با Django 6 سازگار است)
- HTTPS عمومی روی پورت **۴۴۳ یا ۸۸** برای وب‌هوک بله

## نصب

```bash
python -m venv .venv
.venv\Scripts\activate   # ویندوز
pip install -r requirements.txt
copy .env.example .env
```

مقادیر `DJANGO_SECRET_KEY`، `BALE_BOT_TOKEN`، `BALE_WEBHOOK_SECRET` و در صورت نیاز `DJANGO_ALLOWED_HOSTS` و `DJANGO_CSRF_TRUSTED_ORIGINS` را در `.env` تنظیم کنید.

## دیتابیس و کاربر ادمین

```bash
python manage.py migrate
python manage.py createsuperuser
```

کاربر ادمین با پرچم **staff** می‌تواند به `/bale/panel/` وارد شود.

## آدرس‌ها

| مسیر | توضیح |
|------|--------|
| `/bale/webhook/<BALE_WEBHOOK_SECRET>/` | وب‌هوک POST (JSON آپدیت بله) |
| `/bale/panel/` | داشبورد (نیاز به ورود staff) |
| `/bale/health/` | سلامت سرویس (متن `ok`) |
| `/admin/` | ادمین جنگو |

نمونهٔ URL وب‌هوک:

`https://yourdomain.com/bale/webhook/your-secret-string/`

## ثبت وب‌هوک در بله

```bash
python manage.py set_bale_webhook https://yourdomain.com/bale/webhook/your-secret-string/
```

یا متغیر `BALE_WEBHOOK_PUBLIC_URL` را برابر همان آدرس قرار دهید و بدون آرگومان:

```bash
python manage.py set_bale_webhook
```

حذف وب‌هوک:

```bash
python manage.py set_bale_webhook --delete
```

## ارسال کمپین‌ها (cron)

کمپین‌هایی که از پنل «در صف» شده‌اند با این دستور پردازش می‌شوند:

```bash
python manage.py process_campaigns
```

نمونهٔ **Linux cron** (هر ۲ دقیقه):

```cron
*/2 * * * * cd /path/to/core && /path/to/.venv/bin/python manage.py process_campaigns >> /var/log/bale_campaigns.log 2>&1
```

تلاش مجدد برای تحویل‌های ناموفق (اختیاری):

```bash
python manage.py retry_failed_deliveries --limit 200
python manage.py process_campaigns
```

## فایل‌های رسانه

پوشهٔ `media/` برای آپلود کمپین و رسانه‌ها استفاده می‌شود؛ در production با وب‌سرور یا استوریج ابری سرو کنید و `MEDIA_ROOT` را متناسب تنظیم کنید.

## ایمنی

- `BALE_WEBHOOK_SECRET` را طولانی و تصادفی نگه دارید؛ بدون آن هر کسی می‌تواند آپدیت جعلی بفرستد.
- `DEBUG=0` در محیط واقعی و `ALLOWED_HOSTS` صحیح.
