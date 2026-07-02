from django.test import TestCase

from balebot.data.start_flow_presets import flatten_buttons_to_items
from balebot.services.flow_sanitize import sanitize_start_flow


class FlowAliasSanitizeTests(TestCase):
    def test_text_node_accepts_text_field(self):
        flow = sanitize_start_flow({
            'version': 2,
            'root': {
                'type': 'sequence',
                'items': [{'type': 'text', 'text': 'سلام از قالب'}],
            },
        })
        items = flow['root']['items']
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]['body'], 'سلام از قالب')

    def test_buttons_block_becomes_independent_button_items(self):
        flow = sanitize_start_flow({
            'version': 2,
            'root': {
                'type': 'sequence',
                'items': [
                    {'type': 'text', 'body': 'خوش آمدید'},
                    {
                        'type': 'buttons',
                        'rows': [
                            [
                                {
                                    'id': 'n_a',
                                    'label': 'فروشگاه',
                                    'action': {'type': 'text', 'text': 'متن اکشن'},
                                },
                                {
                                    'id': 'n_b',
                                    'label': 'پشتیبانی',
                                    'action': {'type': 'handoff', 'message': 'سلام'},
                                },
                            ],
                        ],
                    },
                ],
            },
        })
        items = flow['root']['items']
        self.assertEqual(len(items), 3)
        self.assertEqual(items[0]['type'], 'text')
        self.assertEqual(items[1]['type'], 'button')
        self.assertEqual(items[2]['type'], 'button')
        self.assertEqual(items[1]['text'], 'فروشگاه')
        self.assertEqual(items[1]['action']['body'], 'متن اکشن')
        self.assertEqual(items[2]['text'], 'پشتیبانی')


class FlattenButtonsToItemsTests(TestCase):
    def test_each_button_is_separate_item(self):
        flow = {
            'version': 2,
            'root': {
                'type': 'sequence',
                'items': [
                    {'type': 'text', 'body': 'خوش آمدید'},
                    {
                        'type': 'buttons',
                        'rows': [
                            [{'id': 'n_a', 'text': 'A', 'action': {'type': 'text', 'body': 'a'}}],
                            [{'id': 'n_b', 'text': 'B', 'action': {'type': 'text', 'body': 'b'}}],
                        ],
                    },
                ],
            },
        }
        out = flatten_buttons_to_items(flow)
        items = out['root']['items']
        self.assertEqual(len(items), 3)
        self.assertEqual(items[0]['type'], 'text')
        self.assertEqual(items[1]['type'], 'button')
        self.assertEqual(items[2]['type'], 'button')
        self.assertEqual(items[1]['text'], 'A')
        self.assertEqual(items[2]['text'], 'B')
