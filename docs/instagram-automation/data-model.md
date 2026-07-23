# مدل داده

جداول اصلی در migration `instagram.0002_instagram_automation`:

Connection, Contact, Conversation, Message, AutomationRule, RuleCondition, Flow, FlowNode, FlowEdge, FlowExecution, CommentAutomation, WebhookEvent, AuditLog, Entitlement, QuickReply, TrackedLink, BusinessHours

همه با FK به `Workspace`. Token فقط به‌صورت `encrypted_access_token`.
