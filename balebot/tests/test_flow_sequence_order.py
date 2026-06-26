"""ترتیب ارسال sequence و چسباندن دکمه‌ها."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from balebot.services.flow_engine import send_sequence_items


class SendSequenceOrderTests(SimpleTestCase):
    def test_buttons_attach_to_immediately_preceding_text(self):
        cfg = MagicMock()
        cfg.platform = 'bale'
        sequence = {
            'type': 'sequence',
            'items': [
                {'type': 'text', 'body': 'پیام اول'},
                {'type': 'text', 'body': 'پیام دوم'},
                {
                    'type': 'buttons',
                    'rows': [[{'id': 'n_12345678', 'text': 'خرید', 'action': {'type': 'text', 'body': 'ok'}}]],
                },
            ],
        }
        sent: list[tuple[str, dict | None]] = []

        def capture_text(_cfg, _chat, body, *, settings=None, reply_markup=None):
            sent.append((body, reply_markup))
            return {'ok': True}

        with patch('balebot.services.flow_engine.messenger_api.send_message', side_effect=capture_text):
            with patch(
                'balebot.services.flow_engine._send_message_with_inline_markup',
                side_effect=lambda _c, _id, body, markup: sent.append((body, markup)) or True,
            ):
                send_sequence_items(cfg, 1, sequence, merge_button_markup=True)

        self.assertEqual(len(sent), 2)
        self.assertEqual(sent[0], ('پیام اول', None))
        self.assertEqual(sent[1][0], 'پیام دوم')
        self.assertIsNotNone(sent[1][1])
        self.assertIn('inline_keyboard', sent[1][1])
