from django.test import SimpleTestCase, TestCase, Client, override_settings
from django.contrib.auth import get_user_model
from django.utils import timezone

from balebot.models import CatalogItem, Platform
from balebot.workspace import create_panel_user
from instagram.automation.services.persian_normalize import (
    normalize_persian,
    match_text,
    safe_compile_regex,
)
from instagram.automation.services.token_crypto import encrypt_token, decrypt_token
from instagram.automation.services.meta_client import map_meta_error, MetaErrorCategory
from instagram.automation.services.link_tracking import is_url_allowed, create_tracked_link
from instagram.automation.services.permissions import user_has_instagram_perm, ROLE_PERMISSIONS
from instagram.automation.services.oauth import verify_webhook_signature, build_oauth_state, parse_oauth_state
from instagram.automation.services.webhook import ingest_webhook_payload, redact_payload
from instagram.automation.services.normalize import normalize_webhook_event
from instagram.automation.services.rule_engine import evaluate_rules
from instagram.automation.services.flow_engine import start_flow_execution, execute_flow_step, validate_flow
from instagram.automation.models import (
    InstagramConnection,
    InstagramContact,
    InstagramConversation,
    InstagramAutomationRule,
    InstagramRuleCondition,
    InstagramFlow,
    InstagramFlowNode,
    WorkspaceInstagramEntitlement,
)
from django.conf import settings


class PersianNormalizeTests(SimpleTestCase):
    def test_yeh_keh(self):
        self.assertEqual(normalize_persian('قيمت'), normalize_persian('قیمت'))

    def test_digits(self):
        self.assertEqual(normalize_persian('۱۲۳'), '123')

    def test_match_contains(self):
        self.assertTrue(match_text('سلام قیمت چنده؟', operator='contains', value='قیمت'))

    def test_any_keywords(self):
        self.assertTrue(match_text('هزینه ارسال', operator='any_of', value=['قیمت', 'هزینه']))

    def test_regex_safe(self):
        self.assertIsNone(safe_compile_regex('a' * 100))
        self.assertIsNotNone(safe_compile_regex(r'قیمت'))


@override_settings(META_TOKEN_ENCRYPTION_KEY='instagram-tests-only-key')
class TokenCryptoTests(SimpleTestCase):
    def test_roundtrip(self):
        enc = encrypt_token('secret-token-value')
        self.assertNotEqual(enc, 'secret-token-value')
        self.assertEqual(decrypt_token(enc), 'secret-token-value')


class MetaErrorMappingTests(SimpleTestCase):
    def test_rate_limit(self):
        err = map_meta_error(http_status=429, body={'error': {'code': 4}})
        self.assertEqual(err.category, MetaErrorCategory.RATE_LIMIT)

    def test_permission(self):
        err = map_meta_error(http_status=403, body={'error': {'code': 10}})
        self.assertEqual(err.category, MetaErrorCategory.PERMISSION)


class LinkAllowlistTests(SimpleTestCase):
    def test_relative_ok(self):
        self.assertTrue(is_url_allowed('/shop/item/1/'))

    def test_private_ip_blocked(self):
        self.assertFalse(is_url_allowed('http://192.168.1.1/x'))


@override_settings(
    META_APP_SECRET='test-secret',
    META_TOKEN_ENCRYPTION_KEY='instagram-tests-only-key',
    CELERY_TASK_ALWAYS_EAGER=True,
)
class InstagramAutomationIntegrationTests(TestCase):
    def setUp(self):
        self.user, self.workspace = create_panel_user(
            username='igowner',
            password='pass12345',
            workspace_name='IG WS',
            allow_instagram=True,
        )
        WorkspaceInstagramEntitlement.objects.get_or_create(workspace=self.workspace)
        self.conn = InstagramConnection.objects.create(
            workspace=self.workspace,
            connected_by=self.user,
            instagram_account_id='ig-1',
            facebook_page_id='page-1',
            username='shop',
            encrypted_access_token=encrypt_token('tok'),
            connection_status=InstagramConnection.ConnectionStatus.CONNECTED,
            scopes=['instagram_manage_messages'],
        )
        self.client = Client()
        self.client.force_login(self.user)

    def test_permission_owner(self):
        self.assertTrue(user_has_instagram_perm(self.user, self.workspace, 'instagram.connect'))

    def test_oauth_state(self):
        state = build_oauth_state(workspace_id=self.workspace.id, user_id=self.user.id)
        data = parse_oauth_state(state)
        self.assertEqual(data['workspace_id'], self.workspace.id)

    def test_webhook_verify(self):
        with self.settings(META_WEBHOOK_VERIFY_TOKEN='verify-me'):
            r = self.client.get(
                '/instagram/webhook/',
                {
                    'hub.mode': 'subscribe',
                    'hub.verify_token': 'verify-me',
                    'hub.challenge': '12345',
                },
            )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.content.decode(), '12345')

    def test_webhook_signature_and_ingest(self):
        import hashlib
        import hmac
        import json

        payload = {
            'object': 'instagram',
            'entry': [
                {
                    'id': 'page-1',
                    'messaging': [
                        {
                            'sender': {'id': 'u1'},
                            'recipient': {'id': 'ig-1'},
                            'message': {'mid': 'm1', 'text': 'قیمت'},
                        }
                    ],
                }
            ],
        }
        body = json.dumps(payload).encode()
        sig = 'sha256=' + hmac.new(b'test-secret', body, hashlib.sha256).hexdigest()
        r = self.client.post(
            '/instagram/webhook/',
            data=body,
            content_type='application/json',
            HTTP_X_HUB_SIGNATURE_256=sig,
        )
        self.assertEqual(r.status_code, 200)
        self.assertTrue(InstagramContact.objects.filter(instagram_scoped_user_id='u1').exists())

    def test_duplicate_fingerprint(self):
        payload = {
            'object': 'instagram',
            'entry': [
                {
                    'id': 'page-1',
                    'messaging': [
                        {
                            'sender': {'id': 'u2'},
                            'recipient': {'id': 'ig-1'},
                            'message': {'mid': 'm-dup', 'text': 'hi'},
                        }
                    ],
                }
            ],
        }
        a = ingest_webhook_payload(payload)
        b = ingest_webhook_payload(payload)
        self.assertEqual(len(a), 1)
        self.assertEqual(len(b), 0)

    def test_rule_priority_and_flow(self):
        flow = InstagramFlow.objects.create(
            workspace=self.workspace,
            name='قیمت',
            status=InstagramFlow.Status.ACTIVE,
            entry_node_id='t1',
            definition={
                'entry': 't1',
                'nodes': [{'id': 't1', 'type': 'send_text', 'config': {'text': 'سلام'}}],
                'edges': [],
            },
        )
        InstagramFlowNode.objects.create(
            flow=flow, node_key='t1', node_type='send_text', config={'text': 'سلام'}
        )
        rule = InstagramAutomationRule.objects.create(
            workspace=self.workspace,
            connection=self.conn,
            name='kw',
            trigger_type=InstagramAutomationRule.TriggerType.KEYWORD,
            priority=10,
            is_active=True,
            flow=flow,
            schedule={'keywords': ['قیمت']},
            stop_after_match=True,
        )
        InstagramRuleCondition.objects.create(
            rule=rule, field='text', operator='contains', value='قیمت', normalize_persian=True
        )
        event = normalize_webhook_event(
            event_type='message.received',
            payload={'sender': {'id': 'u9'}, 'message': {'text': 'قیمت لطفا', 'mid': 'mx'}},
            connection_id=self.conn.id,
            workspace_id=self.workspace.id,
            correlation_id='c1',
        )
        contact = InstagramContact.objects.create(
            workspace=self.workspace,
            connection=self.conn,
            instagram_scoped_user_id='u9',
        )
        result = evaluate_rules(
            workspace_id=self.workspace.id,
            connection_id=self.conn.id,
            contact_id=contact.id,
            event=event,
        )
        self.assertEqual(result.rule.id, rule.id)

        # test mode flow — no real Meta send
        execution = start_flow_execution(flow=flow, contact=contact, is_test_mode=True)
        execution = execute_flow_step(execution)
        self.assertIn(execution.status, ('completed', 'running', 'waiting'))

    def test_human_takeover_flag(self):
        contact = InstagramContact.objects.create(
            workspace=self.workspace,
            connection=self.conn,
            instagram_scoped_user_id='u3',
        )
        conv = InstagramConversation.objects.create(
            workspace=self.workspace,
            connection=self.conn,
            contact=contact,
            mode=InstagramConversation.Mode.HUMAN,
            automation_paused_permanent=True,
        )
        self.assertFalse(conv.is_automation_active())

    def test_tenant_isolation_inbox(self):
        other, other_ws = create_panel_user(
            username='otherig', password='pass12345', workspace_name='Other', allow_instagram=True
        )
        contact = InstagramContact.objects.create(
            workspace=self.workspace,
            connection=self.conn,
            instagram_scoped_user_id='u4',
        )
        conv = InstagramConversation.objects.create(
            workspace=self.workspace,
            connection=self.conn,
            contact=contact,
        )
        c2 = Client()
        c2.force_login(other)
        r = c2.get(f'/instagram/inbox/{conv.pk}/')
        self.assertIn(r.status_code, (404, 302))

    def test_connection_page(self):
        r = self.client.get('/instagram/connect/')
        self.assertEqual(r.status_code, 200)

    def test_redact_payload(self):
        out = redact_payload({'access_token': 'abc', 'text': 'hi'})
        self.assertEqual(out['access_token'], '[REDACTED]')
        self.assertEqual(out['text'], 'hi')


class FlowValidateTests(TestCase):
    def setUp(self):
        self.user, self.workspace = create_panel_user(
            username='flowu', password='pass12345', workspace_name='F', allow_instagram=True
        )

    def test_empty_flow(self):
        flow = InstagramFlow.objects.create(workspace=self.workspace, name='e')
        errs = validate_flow(flow)
        self.assertTrue(errs)

    def test_definition_flow_rejects_unknown_node(self):
        flow = InstagramFlow.objects.create(
            workspace=self.workspace,
            name='unknown',
            entry_node_id='ai',
            definition={
                'entry': 'ai',
                'nodes': [{'id': 'ai', 'type': 'ai_reply', 'config': {}}],
                'edges': [],
            },
        )
        self.assertTrue(any('پشتیبانی‌نشده' in error for error in validate_flow(flow)))


class SimpleReplyTests(TestCase):
    def setUp(self):
        self.user, self.workspace = create_panel_user(
            username='simpleig', password='pass12345', workspace_name='S', allow_instagram=True
        )

    def test_preset_creates_active_rule_with_reply(self):
        from instagram.automation.services.simple_replies import apply_preset

        rule = apply_preset(workspace=self.workspace, user=self.user, preset_key='price')
        self.assertTrue(rule.is_active)
        self.assertIn('قیمت', rule.schedule.get('keywords') or [])
        self.assertTrue(rule.schedule.get('reply_text'))
        self.assertIsNotNone(rule.flow_id)
        self.assertEqual(rule.flow.status, InstagramFlow.Status.ACTIVE)
        self.assertTrue(rule.flow.nodes.filter(node_type='send_text').exists())

    def test_product_reply_has_exactly_one_sending_node(self):
        from instagram.automation.services.simple_replies import build_simple_flow_definition

        product = CatalogItem.objects.create(
            workspace=self.workspace,
            platform=Platform.BALE,
            title='محصول استوری',
            slug='story-product',
            price=125000,
            stock=2,
            is_active=True,
        )
        definition = build_simple_flow_definition(
            reply_text='قیمت و لینک خرید:',
            product=product,
        )
        sending_nodes = [
            node for node in definition['nodes']
            if node['type'] in ('send_text', 'send_product')
        ]
        self.assertEqual(definition['entry'], 'product')
        self.assertEqual(len(sending_nodes), 1)
        self.assertEqual(sending_nodes[0]['type'], 'send_product')

    def test_product_bound_rule_uses_product_resolved_from_story(self):
        from instagram.automation.services.simple_replies import build_simple_flow_definition

        definition = build_simple_flow_definition(
            reply_text='قیمت لحظه‌ای:',
            use_source_product=True,
        )
        self.assertEqual(definition['entry'], 'product')
        product_node = definition['nodes'][0]
        self.assertEqual(product_node['type'], 'send_product')
        self.assertIsNone(product_node['config']['product_id'])
