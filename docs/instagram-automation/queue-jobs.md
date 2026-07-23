# Queue jobs

صف: `instagram` (در `docker/start.sh`)

| Task | نقش |
|------|-----|
| process_instagram_webhook | پردازش رویداد |
| retry_failed_instagram_event | replay |
| retry_due_instagram_events | beat هر ۶۰ثانیه |
| execute_instagram_flow | ادامه فلو |
| refresh_instagram_token | جایگاه تمدید |
| cleanup_instagram_data | پاکسازی |
| calculate_instagram_analytics | خلاصه آمار |
| notify_instagram_connection_error | audit خطا |
