# دایرکت هوشمند اینستاگرام — راحت‌سل

اتوماسیون پیام و کامنت اینستاگرام فقط از طریق **Meta Graph API رسمی**. رمز اینستاگرام هرگز دریافت یا ذخیره نمی‌شود.

## وضعیت قابلیت‌ها

| قابلیت | وضعیت |
|--------|--------|
| OAuth اتصال حساب حرفه‌ای | کامل (نیاز به Meta App) |
| رمزنگاری Token | کامل (Fernet) |
| Webhook verify + signature + idempotent queue | کامل |
| Inbox + Human Takeover | کامل |
| Rule / Flow MVP | کامل |
| Comment + Private Reply | زیرساخت کامل؛ **نیازمند App Review** |
| Story reply / mention | Adapter آماده؛ **نیازمند تأیید Meta** |
| Follow-check | **غیرفعال دائم** — API رسمی کافی نیست |
| Flow Builder بصری | MVP کامل |
| Analytics / Audit / Replay | کامل |
| Link tracking | کامل |
| AI Assistant | Placeholder؛ **Feature Flag خاموش** |
| پرداخت داخل اینستاگرام | عمداً پشتیبانی نمی‌شود |

## فهرست مستندات

1. [معماری](architecture.md)
2. [تنظیم Meta App](meta-app-setup.md)
3. [Permissionها](permissions.md)
4. [Webhook](webhook.md)
5. [متغیرهای محیطی](env.md)
6. [مدل داده](data-model.md)
7. [API داخلی](api.md)
8. [Queue jobs](queue-jobs.md)
9. [کدهای خطا](error-codes.md)
10. [تست](testing.md)
11. [استقرار](deployment.md)
12. [Rollback](rollback.md)
13. [محدودیت‌های Meta](meta-limits.md)
14. [راهنمای کاربری فارسی](user-guide-fa.md)

## TODO باقی‌مانده

- تکمیل App Review در Meta و روشن کردن `meta_*_approved` روی entitlement
- Provider واقعی AI پس از انتخاب سرویس
- Sync فهرست media از Graph برای انتخاب پست در UI کامنت
- ساعات کاری UI (مدل `InstagramBusinessHours` آماده است)
