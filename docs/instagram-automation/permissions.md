# Permissionهای داخلی و Meta

## داخلی (RBAC)

`instagram.view`, `connect`, `disconnect`, `inbox.view|reply|assign`, `automation.view|create|edit|publish|delete`, `analytics.view`, `settings.manage`, `logs.view`, `events.replay`, `export`

Map نقش: owner/admin/manager/support_agent/viewer در `permissions.py`.

## Meta (نمونه‌ها)

| Permission | کاربرد | نیازمند Review |
|------------|--------|----------------|
| instagram_basic | پروفایل | اغلب بله |
| instagram_manage_messages | DM | بله |
| instagram_manage_comments | کامنت | بله |
| pages_manage_metadata | webhook | بله |
| pages_messaging | private reply مسیر Page | بله |
