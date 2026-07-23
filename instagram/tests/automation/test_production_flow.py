import json
from datetime import timedelta

from django.test import Client, SimpleTestCase, TestCase
from django.urls import reverse
from django.utils import timezone

from balebot.models import (
    BotSettings,
    CatalogEntitlement,
    CatalogItem,
    CatalogOrder,
    CatalogOrderLine,
    CatalogSettings,
    CustomerProfile,
    Platform,
    Subscriber,
)
from balebot.workspace import create_panel_user
from instagram.automation.models import (
    InstagramConnection,
    InstagramContact,
    InstagramStorefrontConfig,
)
from instagram.automation.services.link_tracking import create_tracked_link
from instagram.automation.services.normalize import normalize_webhook_event


class WebhookContextTests(SimpleTestCase):
    def test_story_reply_preserves_origin_context(self):
        event = normalize_webhook_event(
            event_type='message.story_reply',
            payload={
                'sender': {'id': 'customer-1'},
                'recipient': {'id': 'ig-1'},
                'message': {
                    'mid': 'mid-1',
                    'text': 'قیمت',
                    'reply_to': {'story': {'id': 'story-42', 'url': 'https://instagram.com/stories/x/42'}},
                },
            },
            connection_id=1,
            workspace_id=2,
            correlation_id='cid',
        )
        self.assertEqual(event.event_type, 'story_reply')
        self.assertEqual(event.story_id, 'story-42')
        self.assertEqual(event.media_id, 'story-42')
        self.assertEqual(event.story_url, 'https://instagram.com/stories/x/42')
        self.assertEqual(event.extra['reply_to']['story']['id'], 'story-42')


class InstagramWebCheckoutTests(TestCase):
    def setUp(self):
        self.user, self.workspace = create_panel_user(
            username='ig-checkout-owner',
            password='pass12345',
            workspace_name='IG Checkout',
            allow_instagram=True,
        )
        self.catalog = CatalogSettings.objects.create(
            workspace=self.workspace,
            platform=Platform.BALE,
            is_enabled=True,
            payment_card_to_card_enabled=True,
            card_to_card_number='6037997512345678',
            card_to_card_sheba='IR120170000000123456789012',
            card_to_card_holder='Test Store',
            checkout_form=[],
        )
        InstagramStorefrontConfig.objects.create(
            workspace=self.workspace,
            catalog=self.catalog,
            is_enabled=True,
            secure_link_hours=24,
        )
        self.connection = InstagramConnection.objects.create(
            workspace=self.workspace,
            connected_by=self.user,
            instagram_account_id='ig-checkout-account',
            username='store',
            connection_status=InstagramConnection.ConnectionStatus.CONNECTED,
        )
        self.customer = CustomerProfile.objects.create(workspace=self.workspace, display_name='IG Customer')
        self.contact = InstagramContact.objects.create(
            workspace=self.workspace,
            connection=self.connection,
            customer=self.customer,
            instagram_scoped_user_id='igsid-customer',
            username='buyer',
        )
        self.item = CatalogItem.objects.create(
            workspace=self.workspace,
            platform=self.catalog.platform,
            title='Story Product',
            slug='story-product',
            price=250000,
            stock=3,
            is_active=True,
        )

    def _new_link(self):
        return create_tracked_link(
            workspace=self.workspace,
            target_url=f'/shop/{self.catalog.public_id}/?product={self.item.slug}',
            contact=self.contact,
            product_id=self.item.pk,
        )

    def test_claim_is_bound_to_first_browser_and_expiry_is_enforced(self):
        link = self._new_link()
        url = reverse('instagram:tracked_link', kwargs={'code': link.short_code})
        first = Client()
        self.assertEqual(first.get(url).status_code, 302)
        self.assertEqual(first.get(url).status_code, 302)
        self.assertEqual(Client().get(url).status_code, 403)

        expired = self._new_link()
        expired.expires_at = timezone.now() - timedelta(seconds=1)
        expired.save(update_fields=['expires_at'])
        expired_url = reverse('instagram:tracked_link', kwargs={'code': expired.short_code})
        self.assertEqual(Client().get(expired_url).status_code, 403)

    def test_checkout_creates_instagram_attributed_c2c_order(self):
        link = self._new_link()
        client = Client()
        client.get(reverse('instagram:tracked_link', kwargs={'code': link.short_code}))
        response = client.post(
            reverse('api_catalog_checkout', kwargs={'public_id': self.catalog.public_id}),
            data=json.dumps({
                'item_id': self.item.pk,
                'quantity': 1,
                'payment_method': 'card_to_card',
                'customer_data': {'full_name': 'Test Buyer', 'phone': '09120000000', 'address': 'Test address'},
            }),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200, response.content)
        order = CatalogOrder.objects.get(pk=response.json()['order_id'])
        self.assertIsNone(order.subscriber_id)
        self.assertEqual(order.customer_id, self.customer.pk)
        self.assertEqual(order.instagram_contact_id, self.contact.pk)
        self.assertEqual(order.instagram_tracked_link_id, link.pk)
        self.assertEqual(order.source_channel, CatalogOrder.SourceChannel.INSTAGRAM)
        self.assertEqual(order.payment_method, CatalogSettings.PaymentMethod.CARD_TO_CARD)
        self.assertEqual(order.lines.get().price_snapshot, 250000)

    def test_paid_order_delivery_token_grants_canonical_entitlement_once(self):
        target = CatalogItem.objects.create(
            workspace=self.workspace,
            platform=Platform.TELEGRAM,
            canonical_key=self.item.canonical_key,
            title=self.item.title,
            slug=self.item.slug,
            price=self.item.price,
            is_active=True,
        )
        BotSettings.objects.update_or_create(
            workspace=self.workspace,
            platform=Platform.TELEGRAM,
            defaults={
                'bot_token': 'test-token',
                'webhook_secret': 'delivery-secret',
                'bot_public_username': 'test_delivery_bot',
                'is_enabled': True,
            },
        )
        order = CatalogOrder.objects.create(
            workspace=self.workspace,
            customer=self.customer,
            source_channel=CatalogOrder.SourceChannel.INSTAGRAM,
            platform=self.catalog.platform,
            status=CatalogOrder.Status.PAID,
            total_amount=self.item.price,
        )
        CatalogOrderLine.objects.create(
            order=order,
            item=self.item,
            title_snapshot=self.item.title,
            price_snapshot=self.item.price,
            quantity=1,
        )
        subscriber = Subscriber.objects.create(
            workspace=self.workspace,
            platform=Platform.TELEGRAM,
            messenger_user_id=9001,
            chat_id=9001,
        )
        from balebot.services.instagram_delivery import consume_delivery_token, issue_delivery_link

        delivery = issue_delivery_link(order, Platform.TELEGRAM)
        self.assertIsNotNone(delivery)
        raw = delivery['url'].split('igd_', 1)[1]
        self.assertEqual(consume_delivery_token(raw, subscriber), 1)
        subscriber.refresh_from_db()
        self.assertEqual(subscriber.customer_id, self.customer.pk)
        self.assertTrue(CatalogEntitlement.objects.filter(subscriber=subscriber, item=target).exists())
        with self.assertRaisesMessage(ValueError, 'delivery_token_invalid'):
            consume_delivery_token(raw, subscriber)
