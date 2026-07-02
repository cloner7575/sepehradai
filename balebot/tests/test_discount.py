from django.test import TestCase

from balebot.models import (
    CatalogOrder,
    CatalogSettings,
    DiscountCode,
    Platform,
    Subscriber,
)
from balebot.services.catalog_payment import mark_order_paid
from balebot.services.discount import (
    DiscountError,
    apply_coupon_resolution_to_flow,
    calculate_discount_amount,
    resolve_coupon_node,
    validate_discount_code,
)
from balebot.workspace import create_panel_user


class DiscountCodeValidationTests(TestCase):
    def setUp(self):
        _user, self.workspace = create_panel_user(
            username='discount_test_user',
            password='testpass123',
            workspace_name='Discount Panel',
        )
        self.platform = Platform.BALE
        self.catalog = CatalogSettings.get_for_platform(self.workspace, self.platform)
        self.sub = Subscriber.objects.create(
            workspace=self.workspace,
            platform=self.platform,
            messenger_user_id=501,
            chat_id=501,
            is_registered=True,
        )
        self.dc = DiscountCode.objects.create(
            workspace=self.workspace,
            platform=self.platform,
            code='SAVE10',
            kind=DiscountCode.Kind.PERCENT,
            value=10,
            max_uses=2,
            min_order_amount=100_000,
            max_discount_amount=50_000,
            first_purchase_only=True,
        )

    def test_min_order_amount_rejected(self):
        with self.assertRaises(DiscountError):
            validate_discount_code(
                self.catalog,
                'SAVE10',
                subtotal=50_000,
                subscriber=self.sub,
            )

    def test_max_discount_amount_caps_percent(self):
        amount = calculate_discount_amount(self.dc, 1_000_000)
        self.assertEqual(amount, 50_000)

    def test_first_purchase_only_rejected_for_repeat_buyer(self):
        order = CatalogOrder.objects.create(
            workspace=self.workspace,
            platform=self.platform,
            subscriber=self.sub,
            status=CatalogOrder.Status.PAID,
            total_amount=200_000,
        )
        order.save()
        with self.assertRaises(DiscountError) as ctx:
            validate_discount_code(
                self.catalog,
                'SAVE10',
                subtotal=200_000,
                subscriber=self.sub,
            )
        self.assertIn('اولین خرید', str(ctx.exception))

    def test_max_uses_incremented_on_paid(self):
        order = CatalogOrder.objects.create(
            workspace=self.workspace,
            platform=self.platform,
            subscriber=self.sub,
            status=CatalogOrder.Status.PENDING,
            total_amount=200_000,
            discount_code='SAVE10',
        )
        self.dc.first_purchase_only = False
        self.dc.save(update_fields=['first_purchase_only'])
        mark_order_paid(order)
        self.dc.refresh_from_db()
        self.assertEqual(self.dc.used_count, 1)

    def test_max_uses_blocks_after_limit(self):
        self.dc.used_count = 2
        self.dc.first_purchase_only = False
        self.dc.save(update_fields=['used_count', 'first_purchase_only'])
        with self.assertRaises(DiscountError):
            validate_discount_code(
                self.catalog,
                'SAVE10',
                subtotal=200_000,
                subscriber=self.sub,
            )

    def test_resolve_coupon_node_by_discount_id(self):
        node = resolve_coupon_node(
            {'type': 'coupon', 'discount_id': self.dc.pk, 'message': 'سلام'},
            self.workspace,
            self.platform,
        )
        self.assertEqual(node['code'], 'SAVE10')
        self.assertEqual(node['discount_id'], self.dc.pk)

    def test_apply_coupon_resolution_to_flow_links_code(self):
        flow = apply_coupon_resolution_to_flow(
            {
                'version': 2,
                'root': {
                    'type': 'sequence',
                    'items': [
                        {'type': 'coupon', 'code': 'save10', 'message': 'تست'},
                    ],
                },
            },
            self.workspace,
            self.platform,
        )
        item = flow['root']['items'][0]
        self.assertEqual(item['code'], 'SAVE10')
        self.assertEqual(item['discount_id'], self.dc.pk)
