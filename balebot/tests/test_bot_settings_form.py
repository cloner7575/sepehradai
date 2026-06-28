from django.test import TestCase

from balebot.forms import BotSettingsForm
from balebot.models import BotSettings, Platform
from balebot.workspace import create_panel_user

SAMPLE_FLOW = {
    'version': 2,
    'root': {
        'type': 'sequence',
        'items': [
            {
                'type': 'message',
                'text': 'سلام',
            },
        ],
    },
}


class BotSettingsFormFlowPreservationTests(TestCase):
    def setUp(self):
        _user, self.workspace = create_panel_user(
            username='bot_settings_form_user',
            password='testpass123',
            workspace_name='Bot Settings Form Panel',
        )
        self.cfg = BotSettings.get_for_platform(self.workspace, Platform.BALE)
        self.cfg.start_flow = SAMPLE_FLOW
        self.cfg.start_flow_default_text = 'مسیر نامشخص'
        self.cfg.save(update_fields=['start_flow', 'start_flow_default_text'])

    def _settings_post_data(self):
        return {
            'bot_token': '',
            'is_enabled': 'on',
            'panel_brand_title': self.cfg.panel_brand_title,
            'panel_brand_subtitle': self.cfg.panel_brand_subtitle,
            'start_message_normal': self.cfg.start_message_normal,
            'start_message_contact': self.cfg.start_message_contact,
            'contact_button_label': self.cfg.contact_button_label,
            'registration_success_message': self.cfg.registration_success_message,
            'unsubscribe_message': self.cfg.unsubscribe_message,
            'callback_ack_message': self.cfg.callback_ack_message,
            'help_message': self.cfg.help_message,
            'support_button_label': self.cfg.support_button_label,
            'support_start_prompt_message': self.cfg.support_start_prompt_message,
            'support_waiting_message': self.cfg.support_waiting_message,
        }

    def test_save_does_not_wipe_start_flow(self):
        form = BotSettingsForm(data=self._settings_post_data(), instance=self.cfg)
        self.assertTrue(form.is_valid(), form.errors)
        form.save()

        self.cfg.refresh_from_db()
        self.assertEqual(self.cfg.start_flow, SAMPLE_FLOW)
        self.assertEqual(self.cfg.start_flow_default_text, 'مسیر نامشخص')
