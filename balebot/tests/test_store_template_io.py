import json

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase
from django.urls import reverse

from balebot.models import StoreTemplate
from balebot.services.store_template_io import (
    StoreTemplateImportError,
    build_export_bundle,
    delete_all_store_templates,
    delete_store_template,
    import_store_templates,
    parse_import_payload,
)

User = get_user_model()

SAMPLE_TEMPLATE = {
    'slug': 'my-custom-shop',
    'name': 'فروشگاه تست',
    'industry': 'general',
    'description': 'توضیح نمونه',
    'sort_order': 99,
    'is_active': True,
    'data': {
        'settings': {'hero_title': 'سلام'},
        'categories': [],
        'items': [],
    },
}


class StoreTemplateIOTests(TestCase):
    def test_parse_bundle_and_import(self):
        payload = {'version': 1, 'kind': 'store_templates', 'templates': [SAMPLE_TEMPLATE]}
        rows = parse_import_payload(payload)
        stats = import_store_templates(rows)
        self.assertEqual(stats['created'], 1)
        obj = StoreTemplate.objects.get(slug='my-custom-shop')
        self.assertEqual(obj.name, 'فروشگاه تست')
        self.assertEqual(obj.data['settings']['hero_title'], 'سلام')

    def test_import_updates_existing_slug(self):
        StoreTemplate.objects.create(
            slug='my-custom-shop',
            name='قدیمی',
            industry='general',
            data={},
        )
        rows = parse_import_payload({'templates': [SAMPLE_TEMPLATE]})
        stats = import_store_templates(rows)
        self.assertEqual(stats['updated'], 1)
        self.assertEqual(StoreTemplate.objects.get(slug='my-custom-shop').name, 'فروشگاه تست')

    def test_delete_store_template(self):
        StoreTemplate.objects.create(
            slug='delete-me',
            name='حذف شونده',
            industry='general',
            data={},
        )
        name = delete_store_template('delete-me')
        self.assertEqual(name, 'حذف شونده')
        self.assertFalse(StoreTemplate.objects.filter(slug='delete-me').exists())

    def test_delete_all_active_only(self):
        StoreTemplate.objects.create(slug='active-1', name='A', industry='general', is_active=True, data={})
        StoreTemplate.objects.create(slug='inactive-1', name='B', industry='general', is_active=False, data={})
        delete_all_store_templates(include_inactive=False)
        self.assertFalse(StoreTemplate.objects.filter(slug='active-1').exists())
        self.assertTrue(StoreTemplate.objects.filter(slug='inactive-1').exists())

    def test_delete_all_including_inactive(self):
        StoreTemplate.objects.create(slug='active-2', name='A', industry='general', is_active=True, data={})
        StoreTemplate.objects.create(slug='inactive-2', name='B', industry='general', is_active=False, data={})
        delete_all_store_templates(include_inactive=True)
        self.assertFalse(StoreTemplate.objects.filter(slug='active-2').exists())
        self.assertFalse(StoreTemplate.objects.filter(slug='inactive-2').exists())

    def test_invalid_slug_raises(self):
        bad = dict(SAMPLE_TEMPLATE)
        bad['slug'] = '!!!'
        with self.assertRaises(StoreTemplateImportError):
            parse_import_payload({'templates': [bad]})

    def test_export_roundtrip(self):
        StoreTemplate.objects.create(
            slug='export-me',
            name='اکسپورت',
            industry='books',
            description='',
            data={'items': [{'slug': 'x'}]},
        )
        bundle = build_export_bundle(StoreTemplate.objects.filter(slug='export-me'))
        rows = parse_import_payload(bundle)
        self.assertEqual(rows[0]['slug'], 'export-me')
        self.assertEqual(len(rows[0]['data']['items']), 1)


class StoreTemplateImportExportViewTests(TestCase):
    def setUp(self):
        self.superuser = User.objects.create_superuser('su_tpl', 'su@example.com', 'pass')
        self.user = User.objects.create_user('normal_tpl', 'u@example.com', 'pass')
        StoreTemplate.objects.create(
            slug='visible-template',
            name='قابل مشاهده',
            industry='general',
            data={},
        )

    def test_export_requires_superuser(self):
        client = Client()
        client.force_login(self.user)
        response = client.get(reverse('catalog_templates_export'))
        self.assertEqual(response.status_code, 403)

    def test_superuser_can_export(self):
        client = Client()
        client.force_login(self.superuser)
        response = client.get(reverse('catalog_templates_export'))
        self.assertEqual(response.status_code, 200)
        payload = json.loads(response.content.decode('utf-8'))
        self.assertIn('templates', payload)

    def test_superuser_can_import(self):
        client = Client()
        client.force_login(self.superuser)
        body = json.dumps(
            {'templates': [SAMPLE_TEMPLATE]},
            ensure_ascii=False,
        ).encode('utf-8')
        upload = SimpleUploadedFile('templates.json', body, content_type='application/json')
        response = client.post(
            reverse('catalog_templates_import'),
            {'file': upload},
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(StoreTemplate.objects.filter(slug='my-custom-shop').exists())

    def test_import_rejects_non_superuser(self):
        client = Client()
        client.force_login(self.user)
        body = json.dumps({'templates': [SAMPLE_TEMPLATE]}).encode('utf-8')
        upload = SimpleUploadedFile('templates.json', body, content_type='application/json')
        response = client.post(
            reverse('catalog_templates_import'),
            {'file': upload},
        )
        self.assertEqual(response.status_code, 403)

    def test_superuser_can_delete_template(self):
        client = Client()
        client.force_login(self.superuser)
        response = client.post(reverse('catalog_template_delete', kwargs={'slug': 'visible-template'}))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(StoreTemplate.objects.filter(slug='visible-template').exists())

    def test_delete_rejects_non_superuser(self):
        client = Client()
        client.force_login(self.user)
        response = client.post(reverse('catalog_template_delete', kwargs={'slug': 'visible-template'}))
        self.assertEqual(response.status_code, 403)
        self.assertTrue(StoreTemplate.objects.filter(slug='visible-template').exists())

    def test_superuser_can_delete_all_active(self):
        StoreTemplate.objects.create(slug='extra-template', name='دیگر', industry='general', data={})
        client = Client()
        client.force_login(self.superuser)
        response = client.post(reverse('catalog_templates_delete_all'), {'scope': 'active'})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(StoreTemplate.objects.filter(is_active=True).count(), 0)

    def test_delete_all_rejects_non_superuser(self):
        client = Client()
        client.force_login(self.user)
        response = client.post(reverse('catalog_templates_delete_all'), {'scope': 'all'})
        self.assertEqual(response.status_code, 403)
