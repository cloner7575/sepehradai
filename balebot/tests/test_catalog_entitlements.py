from django.test import Client, TestCase

import json

from balebot.models import (
    CatalogEntitlement,
    CatalogItem,
    CatalogItemMember,
    CatalogOrder,
    CatalogOrderLine,
    CatalogSettings,
    Platform,
    Subscriber,
)
from balebot.services.catalog_access import subscriber_has_item_access
from balebot.services.catalog_access_tokens import issue_media_token, verify_media_token
from balebot.services.catalog_payment import mark_order_paid
from balebot.workspace import create_panel_user


class CatalogEntitlementTests(TestCase):
    def setUp(self):
        _user, self.workspace = create_panel_user(
            username='entitlement_test_user',
            password='testpass123',
            workspace_name='Entitlement Panel',
        )
        self.platform = Platform.BALE
        self.catalog = CatalogSettings.get_for_platform(self.workspace, self.platform)
        self.sub = Subscriber.objects.create(
            workspace=self.workspace,
            platform=self.platform,
            messenger_user_id=9001,
            chat_id=9001,
            is_registered=True,
        )
        self.client = Client()
        self.video = CatalogItem.objects.create(
            workspace=self.workspace,
            platform=self.platform,
            title='Paid Video',
            slug='paid-video',
            item_type=CatalogItem.ItemType.VIDEO,
            price=500_000,
            sale_mode=CatalogItem.SaleMode.BUYABLE,
        )
        self.free_download = CatalogItem.objects.create(
            workspace=self.workspace,
            platform=self.platform,
            title='Free File',
            slug='free-file',
            item_type=CatalogItem.ItemType.DOWNLOAD,
            download_link='https://example.com/file.zip',
        )
        self.paid_download = CatalogItem.objects.create(
            workspace=self.workspace,
            platform=self.platform,
            title='Paid File',
            slug='paid-file',
            item_type=CatalogItem.ItemType.DOWNLOAD,
            price=200_000,
            sale_mode=CatalogItem.SaleMode.BUYABLE,
            download_link='https://example.com/paid.zip',
        )
        self.lesson = CatalogItem.objects.create(
            workspace=self.workspace,
            platform=self.platform,
            title='Lesson 1',
            slug='lesson-1',
            item_type=CatalogItem.ItemType.VIDEO,
            price=100_000,
            sale_mode=CatalogItem.SaleMode.BUYABLE,
        )
        self.course = CatalogItem.objects.create(
            workspace=self.workspace,
            platform=self.platform,
            title='Full Course',
            slug='full-course',
            item_type=CatalogItem.ItemType.COURSE,
            price=1_000_000,
            sale_mode=CatalogItem.SaleMode.BUYABLE,
        )
        CatalogItemMember.objects.create(parent=self.course, child=self.lesson, sort_order=0)

    def test_free_content_accessible_without_subscriber(self):
        self.assertTrue(subscriber_has_item_access(None, self.free_download))

    def test_paid_content_locked_without_entitlement(self):
        self.assertFalse(subscriber_has_item_access(self.sub, self.video))
        self.assertFalse(subscriber_has_item_access(self.sub, self.paid_download))

    def test_mark_order_paid_grants_single_item(self):
        order = CatalogOrder.objects.create(
            workspace=self.workspace,
            platform=self.platform,
            subscriber=self.sub,
            status=CatalogOrder.Status.PENDING,
            total_amount=500_000,
        )
        CatalogOrderLine.objects.create(
            order=order,
            item=self.video,
            title_snapshot=self.video.title,
            price_snapshot=self.video.price,
        )
        mark_order_paid(order)
        self.assertTrue(subscriber_has_item_access(self.sub, self.video))
        self.assertTrue(
            CatalogEntitlement.objects.filter(subscriber=self.sub, item=self.video).exists()
        )

    def test_course_purchase_grants_member_access(self):
        order = CatalogOrder.objects.create(
            workspace=self.workspace,
            platform=self.platform,
            subscriber=self.sub,
            status=CatalogOrder.Status.PENDING,
            total_amount=1_000_000,
        )
        CatalogOrderLine.objects.create(
            order=order,
            item=self.course,
            title_snapshot=self.course.title,
            price_snapshot=self.course.price,
        )
        mark_order_paid(order)
        self.assertTrue(subscriber_has_item_access(self.sub, self.lesson))

    def test_mark_order_paid_grants_when_order_already_paid(self):
        """شبیه‌سازی تأیید از پنل: وضعیت قبل از mark_order_paid روی paid ذخیره شده."""
        order = CatalogOrder.objects.create(
            workspace=self.workspace,
            platform=self.platform,
            subscriber=self.sub,
            status=CatalogOrder.Status.PAID,
            total_amount=1_000_000,
        )
        CatalogOrderLine.objects.create(
            order=order,
            item=self.course,
            title_snapshot=self.course.title,
            price_snapshot=self.course.price,
        )
        mark_order_paid(order)
        self.assertTrue(subscriber_has_item_access(self.sub, self.course))
        self.assertTrue(subscriber_has_item_access(self.sub, self.lesson))
        self.assertTrue(
            CatalogEntitlement.objects.filter(subscriber=self.sub, item=self.course).exists()
        )

    def test_paid_course_hides_buy_action_in_api(self):
        order = CatalogOrder.objects.create(
            workspace=self.workspace,
            platform=self.platform,
            subscriber=self.sub,
            status=CatalogOrder.Status.PAID,
            total_amount=1_000_000,
        )
        CatalogOrderLine.objects.create(
            order=order,
            item=self.course,
            title_snapshot=self.course.title,
            price_snapshot=self.course.price,
        )
        from balebot.views_miniapp_api import _item_dict

        data = _item_dict(self.course, catalog=self.catalog, subscriber=self.sub)
        self.assertTrue(data['has_access'])
        self.assertFalse(data['is_buyable'])

    def test_paid_order_grants_access_without_entitlement_row(self):
        """دسترسی از روی سفارش پرداخت‌شده حتی بدون رکورد entitlement."""
        order = CatalogOrder.objects.create(
            workspace=self.workspace,
            platform=self.platform,
            subscriber=self.sub,
            status=CatalogOrder.Status.PAID,
            total_amount=1_000_000,
        )
        CatalogOrderLine.objects.create(
            order=order,
            item=self.course,
            title_snapshot=self.course.title,
            price_snapshot=self.course.price,
        )
        CatalogEntitlement.objects.filter(subscriber=self.sub).delete()
        self.assertTrue(subscriber_has_item_access(self.sub, self.course))
        self.assertTrue(subscriber_has_item_access(self.sub, self.lesson))

    def test_media_token_roundtrip(self):
        token = issue_media_token(subscriber_id=self.sub.pk, media_id=42)
        self.assertTrue(verify_media_token(token, subscriber_id=self.sub.pk, media_id=42))
        self.assertFalse(verify_media_token(token, subscriber_id=self.sub.pk, media_id=99))

    def test_item_detail_hides_paid_download_url(self):
        url = f'/api/shop/{self.catalog.public_id}/items/{self.paid_download.slug}/'
        res = self.client.get(url)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data['item']['download_url'], '')
        self.assertTrue(data['item']['requires_access'])

    def test_content_endpoint_requires_auth(self):
        url = f'/api/shop/{self.catalog.public_id}/items/{self.video.slug}/content/'
        res = self.client.post(url, data='{}', content_type='application/json')
        self.assertEqual(res.status_code, 401)

    def test_catalog_request_without_customer_data_when_form_disabled(self):
        self.catalog.checkout_form = {'enabled': False, 'title': '', 'fields': []}
        self.catalog.save(update_fields=['checkout_form'])
        showcase = CatalogItem.objects.create(
            workspace=self.workspace,
            platform=self.platform,
            title='Showcase Item',
            slug='showcase-item',
            item_type=CatalogItem.ItemType.SHOWCASE,
        )
        url = f'/api/shop/{self.catalog.public_id}/request/'
        res = self.client.post(
            url,
            data='{"initData":"invalid","item_id":%d}' % showcase.pk,
            content_type='application/json',
        )
        self.assertEqual(res.status_code, 401)

    def test_catalog_request_rejects_missing_checkout_fields(self):
        showcase = CatalogItem.objects.create(
            workspace=self.workspace,
            platform=self.platform,
            title='Showcase 2',
            slug='showcase-2',
            item_type=CatalogItem.ItemType.SHOWCASE,
        )
        url = f'/api/shop/{self.catalog.public_id}/request/'
        res = self.client.post(
            url,
            data=json.dumps({'initData': 'x', 'item_id': showcase.pk}),
            content_type='application/json',
        )
        self.assertIn(res.status_code, (400, 401))
