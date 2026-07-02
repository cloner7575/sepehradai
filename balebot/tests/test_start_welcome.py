from unittest.mock import patch

from django.test import TestCase

from balebot.models import BotSettings, Platform, Subscriber
from balebot.workspace import create_panel_user

SAMPLE_FLOW = {
    'version': 2,
    'root': {
        'type': 'sequence',
        'items': [
            {
                'type': 'text',
                'body': 'منوی فروشگاه',
            },
        ],
    },
}


class StartWelcomeMessageTests(TestCase):
    def setUp(self):
        _user, self.workspace = create_panel_user(
            username='start_welcome_user',
            password='testpass123',
            workspace_name='Start Welcome Panel',
        )
        self.cfg = BotSettings.get_for_platform(self.workspace, Platform.BALE)
        self.sub = Subscriber.objects.create(
            workspace=self.workspace,
            platform=Platform.BALE,
            messenger_user_id=100,
            chat_id=100,
            is_registered=True,
        )

    @patch('balebot.services.webhook_logic.render_root_flow')
    @patch('balebot.services.webhook_logic.messenger_api.send_message')
    def test_with_flow_skips_welcome_message(self, mock_send, mock_render):
        from balebot.services.webhook_logic import _send_start_with_flow

        self.cfg.start_flow = SAMPLE_FLOW
        self.cfg.save(update_fields=['start_flow'])

        _send_start_with_flow(self.cfg, self.sub)

        mock_render.assert_called_once()
        mock_send.assert_not_called()

    @patch('balebot.services.webhook_logic.render_root_flow')
    @patch('balebot.services.webhook_logic.messenger_api.send_message')
    def test_without_flow_and_empty_welcome_sends_nothing(self, mock_send, mock_render):
        from balebot.services.webhook_logic import _send_start_with_flow

        self.cfg.start_flow = {'version': 2, 'root': {'type': 'sequence', 'items': []}}
        self.cfg.start_message_normal = ''
        self.cfg.enable_support = False
        self.cfg.save(update_fields=['start_flow', 'start_message_normal', 'enable_support'])

        _send_start_with_flow(self.cfg, self.sub)

        mock_render.assert_not_called()
        mock_send.assert_not_called()

    @patch('balebot.services.webhook_logic.render_root_flow')
    @patch('balebot.services.webhook_logic.messenger_api.send_message')
    def test_without_flow_sends_legacy_welcome_if_set(self, mock_send, mock_render):
        from balebot.services.webhook_logic import _send_start_with_flow

        self.cfg.start_flow = {'version': 2, 'root': {'type': 'sequence', 'items': []}}
        self.cfg.start_message_normal = 'سلام، خوش آمدید!'
        self.cfg.save(update_fields=['start_flow', 'start_message_normal'])

        _send_start_with_flow(self.cfg, self.sub)

        mock_render.assert_not_called()
        mock_send.assert_called_once()
        self.assertIn('خوش آمدید', mock_send.call_args[0][2])
