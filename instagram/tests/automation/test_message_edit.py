from unittest.mock import Mock, patch

from django.test import SimpleTestCase, TestCase, override_settings

from balebot.models import CatalogSettings, Platform
from balebot.workspace import create_panel_user
from instagram.automation.models import (
    InstagramConnection,
    InstagramContact,
    InstagramMessage,
    InstagramWebhookEvent,
    WorkspaceInstagramEntitlement,
)
from instagram.automation.services.event_processor import process_webhook_event
from instagram.automation.services.flow_engine import _absolute_public_urls
from instagram.automation.services.normalize import normalize_webhook_event
from instagram.automation.services.simple_replies import shop_public_url
from instagram.automation.services.webhook import ingest_webhook_payload


class MessageEditNormalizationTests(SimpleTestCase):
    def test_message_edit_metadata_is_normalized_as_received_message(self):
        event = normalize_webhook_event(
            event_type='message.unknown',
            payload={
                'sender': {'id': 'igsid-customer'},
                'recipient': {'id': 'ig-account'},
                'message_edit': {'mid': 'mid-1', 'text': 'قیمت', 'num_edit': 0},
            },
            connection_id=1,
            workspace_id=2,
            correlation_id='cid',
        )

        self.assertEqual(event.event_type, 'message.received')
        self.assertEqual(event.external_message_id, 'mid-1')
        self.assertEqual(event.text, 'قیمت')
        self.assertEqual(event.extra['message_edit']['num_edit'], 0)

    @override_settings(BASE_URL='https://rahatsellf.runflare.run/')
    def test_existing_relative_shop_links_are_made_absolute(self):
        text = 'فروشگاه: /shop/catalog-id/'
        self.assertEqual(
            _absolute_public_urls(text),
            'فروشگاه: https://rahatsellf.runflare.run/shop/catalog-id/',
        )
        self.assertEqual(
            _absolute_public_urls('https://example.com/shop/catalog-id/'),
            'https://example.com/shop/catalog-id/',
        )


@override_settings(META_TOKEN_ENCRYPTION_KEY='instagram-message-edit-tests')
class MessageEditProcessingTests(TestCase):
    def setUp(self):
        self.user, self.workspace = create_panel_user(
            username='ig-message-edit-owner',
            password='pass12345',
            workspace_name='IG Message Edit',
            allow_instagram=True,
        )
        WorkspaceInstagramEntitlement.objects.get_or_create(workspace=self.workspace)
        self.connection = InstagramConnection.objects.create(
            workspace=self.workspace,
            connected_by=self.user,
            instagram_account_id='ig-account',
            facebook_page_id='page-account',
            username='store',
            connection_status=InstagramConnection.ConnectionStatus.CONNECTED,
        )

    def _event(self, *, mid: str, sender: str = 'igsid-customer'):
        return InstagramWebhookEvent.objects.create(
            connection=self.connection,
            workspace=self.workspace,
            external_event_id=mid,
            event_type='message.received',
            fingerprint=f'fp-{InstagramWebhookEvent.objects.count()}-{mid[-12:]}',
            payload_redacted={
                'sender': {'id': sender},
                'recipient': {'id': self.connection.instagram_account_id},
                'timestamp': 1784840000000,
                'message_edit': {'mid': mid, 'num_edit': 0},
            },
            processing_status=InstagramWebhookEvent.ProcessingStatus.QUEUED,
            correlation_id='cid-message-edit',
        )

    def test_ingest_preserves_long_message_edit_mid(self):
        long_mid = 'mid-' + ('x' * 300)
        events = ingest_webhook_payload({
            'object': 'instagram',
            'entry': [{
                'id': self.connection.instagram_account_id,
                'messaging': [{
                    'sender': {'id': 'igsid-ingest'},
                    'recipient': {'id': self.connection.instagram_account_id},
                    'message_edit': {'mid': long_mid, 'num_edit': 0},
                    'timestamp': 1784840000000,
                }],
            }],
        })

        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].event_type, 'message.received')
        self.assertEqual(events[0].external_event_id, long_mid)

    def test_missing_edit_text_is_hydrated_and_saved(self):
        long_mid = 'mid-' + ('y' * 300)
        event = self._event(mid=long_mid)
        client = Mock()
        client.get.return_value = {
            'id': long_mid,
            'message': 'قیمت لطفاً',
            'from': {'id': 'meta-customer-id'},
            'to': {'data': [{'id': self.connection.instagram_account_id}]},
        }

        with patch(
            'instagram.automation.services.oauth.client_for_connection',
            return_value=client,
        ):
            process_webhook_event(event.pk)

        event.refresh_from_db()
        message = InstagramMessage.objects.get()
        self.assertEqual(event.processing_status, InstagramWebhookEvent.ProcessingStatus.PROCESSED)
        self.assertEqual(message.external_message_id, long_mid)
        self.assertEqual(message.text, 'قیمت لطفاً')
        self.assertEqual(message.conversation.contact.instagram_scoped_user_id, 'igsid-customer')
        client.get.assert_called_once_with(
            long_mid,
            params={'fields': 'id,message,from,to,created_time'},
            correlation_id='cid-message-edit',
        )

    def test_outbound_message_edit_is_skipped_as_echo(self):
        event = self._event(mid='mid-outbound', sender='webhook-scoped-sender')
        client = Mock()
        client.get.return_value = {
            'id': 'mid-outbound',
            'message': 'پاسخ فروشگاه',
            'from': {'id': self.connection.instagram_account_id},
        }

        with patch(
            'instagram.automation.services.oauth.client_for_connection',
            return_value=client,
        ):
            process_webhook_event(event.pk)

        event.refresh_from_db()
        self.assertEqual(event.processing_status, InstagramWebhookEvent.ProcessingStatus.SKIPPED)
        self.assertEqual(event.last_error_sanitized, 'message_echo')
        self.assertFalse(InstagramContact.objects.exists())
        self.assertFalse(InstagramMessage.objects.exists())

    @override_settings(BASE_URL='https://rahatsellf.runflare.run/')
    def test_simple_store_url_uses_public_base_url(self):
        catalog = CatalogSettings.objects.create(
            workspace=self.workspace,
            platform=Platform.BALE,
            is_enabled=True,
        )

        self.assertEqual(
            shop_public_url(self.workspace),
            f'https://rahatsellf.runflare.run/shop/{catalog.public_id}/',
        )

    def test_message_and_event_ids_allow_meta_length(self):
        self.assertEqual(InstagramMessage._meta.get_field('external_message_id').max_length, 512)
        self.assertEqual(InstagramMessage._meta.get_field('reply_to_external_message_id').max_length, 512)
        self.assertEqual(InstagramWebhookEvent._meta.get_field('external_event_id').max_length, 512)
