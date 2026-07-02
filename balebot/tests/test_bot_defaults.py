from django.test import TestCase

from balebot.models import BotSettings, Platform
from balebot.workspace import create_panel_user


class BotSettingsDefaultsTests(TestCase):
    def test_collect_contact_on_start_defaults_false_for_new_workspace(self):
        _user, workspace = create_panel_user(
            username='bot_defaults_user',
            password='testpass123',
            workspace_name='Bot Defaults Panel',
        )
        cfg = BotSettings.get_for_platform(workspace, Platform.BALE)
        self.assertFalse(cfg.collect_contact_on_start)

    def test_start_message_normal_defaults_empty(self):
        _user, workspace = create_panel_user(
            username='bot_defaults_user2',
            password='testpass123',
            workspace_name='Bot Defaults Panel 2',
        )
        cfg = BotSettings.get_for_platform(workspace, Platform.BALE)
        self.assertEqual((cfg.start_message_normal or '').strip(), '')
