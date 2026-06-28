from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from balebot.models import (
    BotSettings,
    Campaign,
    CatalogCategory,
    CatalogItem,
    CatalogSettings,
    Platform,
    StoreTemplate,
)
from balebot.services.store_template import apply_template
from balebot.workspace import create_panel_user

User = get_user_model()

FULL_TEMPLATE_DATA = {
    'settings': {
        'hero_title': 'ویترین نمونه',
        'hero_subtitle': 'زیرعنوان',
        'theme': {'primary': '#ff0000'},
    },
    'categories': [{'slug': 'cat-a', 'name': 'دسته A'}],
    'items': [{'slug': 'item-a', 'name': 'محصول A', 'category': 'cat-a', 'price': 1000}],
    'start_flow': {
        'version': 2,
        'root': {
            'type': 'sequence',
            'items': [{'type': 'text', 'body': 'سلام'}],
        },
    },
    'bot_settings': {'collect_contact_on_start': True},
    'marketing': {
        'welcome_discount': {'code': 'WELCOME10', 'kind': 'percent', 'value': 10},
        'campaigns': [{'title': 'کمپین نمونه', 'body': 'متن'}],
    },
}


class ApplyTemplateScopeTests(TestCase):
    def setUp(self):
        self.user, self.workspace = create_panel_user(
            username='scope_tpl_user',
            password='testpass123',
            workspace_name='Scope Panel',
            allow_bale_miniapp=True,
        )
        self.template = StoreTemplate.objects.create(
            slug='scope-test',
            name='قالب تست',
            industry='general',
            data=FULL_TEMPLATE_DATA,
        )
        self.platform = Platform.BALE

    def test_miniapp_scope_applies_catalog_not_bot(self):
        bot = BotSettings.get_for_platform(self.workspace, self.platform)
        bot.start_flow = {}
        bot.save(update_fields=['start_flow'])

        stats = apply_template(
            self.template,
            self.workspace,
            self.platform,
            mode='replace',
            scope='miniapp',
        )

        self.assertEqual(stats['categories_created'], 1)
        self.assertEqual(stats['items_created'], 1)
        self.assertEqual(stats['bot_flow_applied'], 0)
        catalog = CatalogSettings.get_for_platform(self.workspace, self.platform)
        self.assertEqual(catalog.hero_title, 'ویترین نمونه')
        bot.refresh_from_db()
        self.assertEqual(bot.start_flow, {})
        self.assertFalse(Campaign.objects.filter(workspace=self.workspace, title='کمپین نمونه').exists())

    def test_bot_scope_applies_bot_not_catalog(self):
        CatalogCategory.objects.create(
            workspace=self.workspace,
            platform=self.platform,
            slug='existing-cat',
            name='Existing',
        )

        stats = apply_template(
            self.template,
            self.workspace,
            self.platform,
            mode='append',
            scope='bot',
        )

        self.assertEqual(stats['bot_flow_applied'], 1)
        self.assertEqual(stats['bot_settings_applied'], 1)
        self.assertEqual(stats['campaign_created'], 1)
        self.assertEqual(stats['categories_created'], 0)
        self.assertEqual(stats['items_created'], 0)
        self.assertTrue(CatalogCategory.objects.filter(slug='existing-cat').exists())
        self.assertFalse(CatalogItem.objects.filter(workspace=self.workspace).exists())
        bot = BotSettings.get_for_platform(self.workspace, self.platform)
        self.assertTrue(bot.start_flow.get('root'))


class StoreTemplateViewScopeTests(TestCase):
    def setUp(self):
        self.client = Client()
        StoreTemplate.objects.create(
            slug='view-test',
            name='View Test',
            industry='general',
            data=FULL_TEMPLATE_DATA,
        )

    def test_bot_templates_accessible_without_miniapp(self):
        user, _ws = create_panel_user(
            username='bot_only_user',
            password='testpass123',
            workspace_name='Bot Only',
            allow_bale_miniapp=False,
        )
        self.client.login(username='bot_only_user', password='testpass123')
        response = self.client.get(reverse('bot_templates'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'قالب‌های آماده ربات')

    def test_catalog_templates_requires_miniapp(self):
        user, _ws = create_panel_user(
            username='bot_only_user2',
            password='testpass123',
            workspace_name='Bot Only 2',
            allow_bale_miniapp=False,
        )
        self.client.login(username='bot_only_user2', password='testpass123')
        response = self.client.get(reverse('catalog_templates'))
        self.assertEqual(response.status_code, 302)

    def test_regular_user_cannot_see_admin_tools(self):
        user, _ws = create_panel_user(
            username='regular_user',
            password='testpass123',
            workspace_name='Regular',
            allow_bale_miniapp=True,
        )
        self.client.login(username='regular_user', password='testpass123')
        response = self.client.get(reverse('catalog_templates'))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'مدیریت قالب‌ها')
        self.assertNotContains(response, 'catalog_template_export')

    def test_bot_apply_redirects_to_flow_engine(self):
        user, _ws = create_panel_user(
            username='apply_bot_user',
            password='testpass123',
            workspace_name='Apply Bot',
            allow_bale_miniapp=False,
        )
        self.client.login(username='apply_bot_user', password='testpass123')
        response = self.client.post(
            reverse('bot_template_apply', kwargs={'slug': 'view-test'}),
            {'mode': 'append', 'apply_scope': 'bot'},
        )
        self.assertRedirects(response, reverse('bot_flow_engine'))
