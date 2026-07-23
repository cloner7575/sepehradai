# استقرار

1. متغیرهای Meta را در `.env` بگذارید.
2. `pip install -r requirements.txt` (شامل `cryptography`).
3. `python manage.py migrate`
4. Celery باید صف `instagram` را مصرف کند.
5. Webhook عمومی HTTPS به `/instagram/webhook/`
6. اختیاری: `python manage.py seed_instagram_automation --workspace-id=ID` (قانون/فلو غیرفعال)
