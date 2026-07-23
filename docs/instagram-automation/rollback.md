# Rollback

1. قطع اتصال همه حساب‌ها از پنل (پاک‌سازی token).
2. `python manage.py migrate instagram 0001_initial`
3. حذف envهای Meta در صورت نیاز.
4. بازگردانی `docker/start.sh` queues اگر لازم است.

Migration `0002` reversible است؛ دادهٔ اتوماسیون حذف می‌شود.
