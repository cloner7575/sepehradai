from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from balebot.models import BotSettings, Campaign, CatalogSettings, Platform, Workspace
from balebot.services.campaign_runner import run_campaign_delivery_batch
from balebot.services.workspace_subscription import workspace_block_reason, workspace_can_operate
from balebot.workspace import create_panel_user

User = get_user_model()


class WorkspaceSubscriptionModelTests(TestCase):
    def setUp(self):
        self.user, self.workspace = create_panel_user(
            username='sub_test_user',
            password='testpass123',
            workspace_name='Test Panel',
        )

    def test_unlimited_subscription_is_active(self):
        self.workspace.subscription_expires_at = None
        self.workspace.save(update_fields=['subscription_expires_at'])
        self.assertTrue(self.workspace.is_subscription_active())
        self.assertEqual(self.workspace.subscription_status(), 'unlimited')

    def test_future_expiry_is_active(self):
        self.workspace.subscription_expires_at = timezone.now() + timedelta(days=30)
        self.workspace.save(update_fields=['subscription_expires_at'])
        self.assertTrue(self.workspace.is_subscription_active())
        self.assertEqual(self.workspace.subscription_status(), 'active')

    def test_expired_subscription(self):
        self.workspace.subscription_expires_at = timezone.now() - timedelta(hours=1)
        self.workspace.save(update_fields=['subscription_expires_at'])
        self.assertFalse(self.workspace.is_subscription_active())
        self.assertEqual(self.workspace.subscription_status(), 'expired')
        self.assertIsNotNone(workspace_block_reason(self.workspace))

    def test_inactive_workspace_blocks_operation(self):
        self.workspace.is_active = False
        self.workspace.save(update_fields=['is_active'])
        self.assertFalse(workspace_can_operate(self.workspace))


class WorkspaceSubscriptionWebhookTests(TestCase):
    def setUp(self):
        self.user, self.workspace = create_panel_user(
            username='wh_sub_user',
            password='testpass123',
            workspace_name='Webhook Panel',
        )
        self.cfg = BotSettings.get_for_platform(self.workspace, Platform.BALE)
        self.cfg.is_enabled = True
        self.cfg.save(update_fields=['is_enabled'])
        self.url = reverse(
            'platform_webhook',
            kwargs={'platform': Platform.BALE, 'secret': self.cfg.webhook_secret},
        )

    def test_webhook_processes_when_subscription_active(self):
        self.workspace.subscription_expires_at = timezone.now() + timedelta(days=7)
        self.workspace.save(update_fields=['subscription_expires_at'])
        client = Client()
        response = client.post(
            self.url,
            data='{"message":{"chat":{"id":1},"text":"/start"}}',
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)

    def test_webhook_ignored_when_subscription_expired(self):
        self.workspace.subscription_expires_at = timezone.now() - timedelta(hours=1)
        self.workspace.save(update_fields=['subscription_expires_at'])
        client = Client()
        response = client.post(
            self.url,
            data='{"message":{"chat":{"id":1},"text":"/start"}}',
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(response.content, {'ok': True})


class WorkspaceSubscriptionMiniAppTests(TestCase):
    def setUp(self):
        self.user, self.workspace = create_panel_user(
            username='mini_sub_user',
            password='testpass123',
            workspace_name='Mini Panel',
            allow_bale_miniapp=True,
        )
        self.catalog = CatalogSettings.get_for_platform(self.workspace, Platform.BALE)

    def test_miniapp_api_blocked_when_expired(self):
        self.workspace.subscription_expires_at = timezone.now() - timedelta(hours=1)
        self.workspace.save(update_fields=['subscription_expires_at'])
        client = Client()
        url = reverse('api_catalog_config', kwargs={'public_id': self.catalog.public_id})
        response = client.get(url)
        self.assertEqual(response.status_code, 403)


class WorkspaceSubscriptionCampaignTests(TestCase):
    def setUp(self):
        self.user, self.workspace = create_panel_user(
            username='camp_sub_user',
            password='testpass123',
            workspace_name='Campaign Panel',
        )
        self.campaign = Campaign.objects.create(
            workspace=self.workspace,
            platform=Platform.BALE,
            title='Test Campaign',
            content_type=Campaign.ContentType.TEXT,
            body='hello',
            status=Campaign.Status.SENDING,
        )

    def test_campaign_batch_blocked_when_expired(self):
        self.workspace.subscription_expires_at = timezone.now() - timedelta(hours=1)
        self.workspace.save(update_fields=['subscription_expires_at'])
        result = run_campaign_delivery_batch(self.campaign.pk)
        self.assertFalse(result['ok'])
        self.campaign.refresh_from_db()
        self.assertEqual(self.campaign.status, Campaign.Status.CANCELLED)
