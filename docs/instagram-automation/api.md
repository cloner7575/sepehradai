# API داخلی (نمونه مسیرها)

قرارداد JSON: `{ok, error}`

- اتصال: `/instagram/connect/`, `/instagram/oauth/start/`, `/instagram/oauth/callback/`
- Inbox: `/instagram/inbox/`, reply/assign/automation/poll
- Rules/Flows/Comments/Analytics/Logs مطابق `instagram/urls.py`
- Tracked link: `/instagram/r/<code>/`
- AI (خاموش): `/instagram/inbox/<id>/ai/suggest/`
