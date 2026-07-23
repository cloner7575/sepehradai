"""Celery task discovery entry for the instagram app."""

from instagram.automation.tasks import (  # noqa: F401
    calculate_instagram_analytics,
    cleanup_instagram_data,
    execute_instagram_flow,
    notify_instagram_connection_error,
    process_instagram_webhook,
    refresh_instagram_token,
    retry_due_instagram_events,
    retry_failed_instagram_event,
)
