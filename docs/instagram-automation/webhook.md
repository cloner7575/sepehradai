# Webhook

- `GET /instagram/webhook/` — verification (`hub.verify_token`)
- `POST /instagram/webhook/` — events + `X-Hub-Signature-256`
- پاسخ سریع `{"ok": true}` پس از persist + enqueue
- Idempotency با `fingerprint` یکتا
- Replay: `POST /instagram/events/<id>/replay/` (نیازمند `instagram.events.replay`)
- Health: `GET /instagram/connections/health/`
