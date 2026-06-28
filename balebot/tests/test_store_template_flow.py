from django.test import TestCase

from balebot.services.flow_engine import category_slugs_for_button, find_button_by_id, _ButtonRef
from balebot.services.store_template import prepare_start_flow


TEMPLATE_FLOW = {
    'version': 2,
    'root': {
        'type': 'sequence',
        'items': [
            {
                'type': 'buttons',
                'rows': [
                    [
                        {
                            'id': 'n_shop',
                            'label': '🛍 ورود به فروشگاه',
                            'label_slug': 'shop',
                            'action': {'type': 'url', 'url': '{shop_url}'},
                        },
                        {
                            'id': 'n_offer',
                            'label': '🎁 تخفیف',
                            'label_slug': 'offer',
                            'action': {'type': 'text', 'text': 'کد تخفیف'},
                        },
                    ],
                ],
            },
        ],
    },
}


class StoreTemplateFlowCategoryTests(TestCase):
    def test_prepare_start_flow_strips_template_label_slugs(self):
        flow = prepare_start_flow(TEMPLATE_FLOW, 'https://example.com/shop/abc/')

        rows = flow['root']['items'][0]['rows'][0]
        for btn in rows:
            self.assertNotIn('label_slug', btn)

    def test_category_slug_is_used_for_tagging_not_label_slug(self):
        flow = {
            'version': 2,
            'root': {
                'type': 'sequence',
                'items': [
                    {
                        'type': 'buttons',
                        'rows': [[
                            {
                                'id': 'n_a1b2c3d4',
                                'text': 'مانتو',
                                'category_slug': 'manto',
                                'label_slug': 'should-be-ignored',
                                'action': {'type': 'text', 'body': 'لیست مانتوها'},
                            },
                        ]],
                    },
                ],
            },
        }

        class _Cfg:
            start_flow = flow

        ref = find_button_by_id(_Cfg(), 'n_a1b2c3d4')
        self.assertIsNotNone(ref)
        self.assertEqual(category_slugs_for_button(ref), ['manto'])
