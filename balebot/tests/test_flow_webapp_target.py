from django.test import TestCase

from balebot.models import BotSettings, CatalogSettings, Platform
from balebot.services.flow_interactive import _build_webapp_url
from balebot.services.flow_sanitize import sanitize_start_flow
from balebot.workspace import create_panel_user


class FlowWebappTargetTests(TestCase):
    def setUp(self):
        _user, self.workspace = create_panel_user(
            username='flow_webapp_target_user',
            password='testpass123',
            workspace_name='Flow Webapp Panel',
        )
        self.platform = Platform.BALE
        self.bot = BotSettings.get_for_platform(self.workspace, self.platform)
        self.catalog = CatalogSettings.get_for_platform(self.workspace, self.platform)

    def test_sanitize_preserves_webapp_library_target(self):
        flow = sanitize_start_flow({
            'version': 2,
            'root': {
                'type': 'sequence',
                'items': [{
                    'type': 'button',
                    'id': 'n_library',
                    'text': 'کتابخانه',
                    'action': {
                        'type': 'webapp',
                        'label': 'کتابخانه من',
                        'target': {'kind': 'library', 'value': ''},
                    },
                }],
            },
        })
        action = flow['root']['items'][0]['action']
        self.assertEqual(action['type'], 'webapp')
        self.assertEqual(action['target'], {'kind': 'library', 'value': ''})

    def test_build_webapp_url_for_library(self):
        url = _build_webapp_url(self.bot, {'kind': 'library', 'value': ''})
        self.assertTrue(url.endswith('/library'))

    def test_build_webapp_url_defaults_to_home(self):
        url = _build_webapp_url(self.bot, {'kind': 'home', 'value': ''})
        self.assertTrue(url.endswith('/'))

    def test_sanitize_drops_legacy_category_target(self):
        flow = sanitize_start_flow({
            'version': 2,
            'root': {
                'type': 'sequence',
                'items': [{
                    'type': 'button',
                    'id': 'n_shop',
                    'text': 'فروشگاه',
                    'action': {
                        'type': 'webapp',
                        'label': 'ورود',
                        'target': {'kind': 'category', 'value': 'electronics'},
                    },
                }],
            },
        })
        action = flow['root']['items'][0]['action']
        self.assertEqual(action['type'], 'webapp')
        self.assertNotIn('target', action)
