from django.test import TestCase

from balebot.services.flow_engine import find_button_by_id, parse_flow_back_callback, parse_flow_callback
from balebot.services.flow_sanitize import sanitize_start_flow


class FlowCallbackIdTests(TestCase):
    def test_parse_template_style_button_ids(self):
        self.assertEqual(parse_flow_callback('fn_shop'), 'n_shop')
        self.assertEqual(parse_flow_callback('fn_offer'), 'n_offer')
        self.assertEqual(parse_flow_back_callback('fbn_shop'), 'n_shop')

    def test_sanitize_preserves_template_button_ids(self):
        flow = sanitize_start_flow({
            'version': 2,
            'root': {
                'type': 'sequence',
                'items': [{
                    'type': 'buttons',
                    'rows': [[{
                        'id': 'n_shop',
                        'label': 'فروشگاه',
                        'action': {'type': 'text', 'body': 'hi'},
                    }]],
                }],
            },
        })
        btn = flow['root']['items'][0]
        self.assertEqual(btn['id'], 'n_shop')

        class _Cfg:
            start_flow = flow

        self.assertIsNotNone(find_button_by_id(_Cfg(), 'n_shop'))

    def test_row_survives_sanitize_roundtrip(self):
        flow = sanitize_start_flow({
            'version': 2,
            'root': {
                'type': 'sequence',
                'items': [
                    {
                        'type': 'button',
                        'id': 'n_offer',
                        'text': 'تخفیف',
                        'row': 1,
                        'action': {'type': 'text', 'body': 'کد'},
                    },
                    {
                        'type': 'button',
                        'id': 'n_trust',
                        'text': 'ضمانت',
                        'row': 1,
                        'action': {'type': 'text', 'body': '۷ روز'},
                    },
                ],
            },
        })
        items = flow['root']['items']
        self.assertEqual(len(items), 2)
        self.assertEqual(items[0]['row'], 1)
        self.assertEqual(items[1]['row'], 1)

        again = sanitize_start_flow(flow)
        again_items = again['root']['items']
        self.assertEqual(again_items[0]['row'], 1)
        self.assertEqual(again_items[1]['row'], 1)

    def test_row_grouping_preserved_when_flattening(self):
        flow = sanitize_start_flow({
            'version': 2,
            'root': {
                'type': 'sequence',
                'items': [{
                    'type': 'buttons',
                    'rows': [
                        [{'id': 'n_a', 'text': 'A', 'action': {'type': 'text', 'body': 'a'}}],
                        [
                            {'id': 'n_b', 'text': 'B', 'action': {'type': 'text', 'body': 'b'}},
                            {'id': 'n_c', 'text': 'C', 'action': {'type': 'text', 'body': 'c'}},
                        ],
                    ],
                }],
            },
        })
        items = flow['root']['items']
        self.assertEqual(len(items), 3)
        self.assertEqual(items[0]['row'], 0)
        self.assertEqual(items[1]['row'], 1)
        self.assertEqual(items[2]['row'], 1)
