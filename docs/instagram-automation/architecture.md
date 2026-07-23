# معماری

```
Meta Webhook → Verify/Signature → Persist InstagramWebhookEvent → Celery queue `instagram`
→ EventProcessor → ContactResolution → RuleMatching → FlowExecution → MetaGraphClient
→ Delivery + Analytics + AuditLog
```

- Tenant: `balebot.Workspace` + `allow_instagram` + `WorkspaceInstagramEntitlement`
- اپ: `instagram/automation/`
- UI: Django templates RTL + Bootstrap (الگوی `ig-*`)
- صف: Celery Redis queue `instagram`
