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

    def test_sanitize_preserves_webapp_category_target(self):
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
        self.assertEqual(action['target'], {'kind': 'category', 'value': 'electronics'})

    def test_build_webapp_url_for_category(self):
        url = _build_webapp_url(
            self.bot,
            {'kind': 'category', 'value': 'electronics'},
        )
        self.assertIn('/category/electronics', url)
        self.assertTrue(url.startswith('http'))

    def test_build_webapp_url_for_item(self):
        url = _build_webapp_url(
            self.bot,
            {'kind': 'item', 'value': 'my-course'},
        )
        self.assertIn('/item/my-course', url)

    def test_sanitize_preserves_webapp_item_target(self):
        flow = sanitize_start_flow({
            'version': 2,
            'root': {
                'type': 'sequence',
                'items': [{
                    'type': 'button',
                    'id': 'n_item',
                    'text': 'دوره',
                    'action': {
                        'type': 'webapp',
                        'label': 'مشاهده',
                        'target': {'kind': 'item', 'value': 'my-course'},
                    },
                }],
            },
        })
        action = flow['root']['items'][0]['action']
        self.assertEqual(action['target'], {'kind': 'item', 'value': 'my-course'})

    def test_sanitize_drops_category_target_without_value(self):
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
                        'target': {'kind': 'category', 'value': ''},
                    },
                }],
            },
        })
        action = flow['root']['items'][0]['action']
        self.assertEqual(action['type'], 'webapp')
        self.assertNotIn('target', action)
