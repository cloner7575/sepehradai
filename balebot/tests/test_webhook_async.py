from django.test import Client, TestCase, override_settings
from django.urls import reverse

from balebot.models import BotSettings, Platform, Subscriber
from balebot.workspace import create_panel_user

CELERY_EAGER_SETTINGS = {
    'WEBHOOK_USE_CELERY': True,
    'CELERY_TASK_ALWAYS_EAGER': True,
    'CELERY_BROKER_URL': 'memory://',
    'CELERY_RESULT_BACKEND': 'cache+memory://',
}


class WebhookAsyncTests(TestCase):
    def setUp(self):
        self.user, self.workspace = create_panel_user(
            username='async_wh_user',
            password='testpass123',
            workspace_name='Async Webhook Panel',
        )
        self.cfg = BotSettings.get_for_platform(self.workspace, Platform.BALE)
        self.cfg.is_enabled = True
        self.cfg.save(update_fields=['is_enabled'])
        self.url = reverse(
            'platform_webhook',
            kwargs={'platform': Platform.BALE, 'secret': self.cfg.webhook_secret},
        )
        self.payload = (
            '{"message":{"from":{"id":42,"first_name":"Ali"},'
            '"chat":{"id":42},"text":"/start"}}'
        )

    @override_settings(**CELERY_EAGER_SETTINGS)
    def test_webhook_celery_eager_creates_subscriber(self):
        client = Client()
        response = client.post(self.url, data=self.payload, content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            Subscriber.objects.filter(
                workspace=self.workspace,
                platform=Platform.BALE,
                messenger_user_id=42,
            ).exists(),
        )

    @override_settings(WEBHOOK_USE_CELERY=False)
    def test_webhook_sync_creates_subscriber(self):
        client = Client()
        response = client.post(self.url, data=self.payload, content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            Subscriber.objects.filter(
                workspace=self.workspace,
                platform=Platform.BALE,
                messenger_user_id=42,
            ).exists(),
        )
