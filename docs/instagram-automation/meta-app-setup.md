# تنظیم Meta App

1. در developers.facebook.com یک App بسازید (Business).
2. محصول Instagram + Webhooks + Facebook Login را اضافه کنید.
3. Valid OAuth Redirect URI = مقدار `META_REDIRECT_URI`.
4. Webhook Callback URL = `https://YOUR_DOMAIN/instagram/webhook/`
5. Verify Token = `META_WEBHOOK_VERIFY_TOKEN`
6. Subscribe به فیلدهای مجاز: `messages`, `messaging_postbacks`, `comments` (پس از تأیید).
7. مجوزهای لازم را برای App Review ارسال کنید (جدول permissions.md).
8. توکن‌ها فقط از OAuth Page دریافت می‌شوند — هرگز رمز کاربر اینستاگرام.
