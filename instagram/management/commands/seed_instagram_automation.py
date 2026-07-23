from django.core.management.base import BaseCommand
from django.db import transaction

from balebot.models import Workspace, Tag
from instagram.automation.models import (
    InstagramFlow,
    InstagramFlowNode,
    InstagramFlowEdge,
    InstagramAutomationRule,
    InstagramRuleCondition,
    WorkspaceInstagramEntitlement,
)


class Command(BaseCommand):
    help = 'Seed نمونه غیرفعال فلو/قانون «قیمت» برای workspace'

    def add_arguments(self, parser):
        parser.add_argument('--workspace-id', type=int, required=True)

    @transaction.atomic
    def handle(self, *args, **options):
        ws = Workspace.objects.get(pk=options['workspace_id'])
        WorkspaceInstagramEntitlement.objects.get_or_create(workspace=ws)
        tag, _ = Tag.objects.get_or_create(
            workspace=ws,
            slug='ig-product-interest',
            defaults={'name': 'علاقه‌مند به محصول', 'platform': 'bale'},
        )

        flow, created = InstagramFlow.objects.get_or_create(
            workspace=ws,
            name='ارسال اطلاعات محصول از روی کلمه قیمت',
            defaults={
                'description': 'نمونه غیرفعال — پیام/کامنت شامل قیمت',
                'status': InstagramFlow.Status.DRAFT,
                'definition': {},
            },
        )
        if created or not flow.nodes.exists():
            InstagramFlowNode.objects.filter(flow=flow).delete()
            n1 = InstagramFlowNode.objects.create(
                flow=flow,
                node_key='tag',
                node_type='add_tag',
                position_x=40,
                position_y=40,
                config={'tag_id': tag.id},
            )
            n2 = InstagramFlowNode.objects.create(
                flow=flow,
                node_key='intro',
                node_type='send_text',
                position_x=40,
                position_y=140,
                config={'text': 'سلام! برای مشاهده جزئیات و قیمت به‌روز، لینک محصول را ببینید.'},
            )
            n3 = InstagramFlowNode.objects.create(
                flow=flow,
                node_key='product',
                node_type='send_product',
                position_x=40,
                position_y=240,
                config={'product_id': None, 'fallback_text': 'محصول به‌زودی موجود می‌شود.'},
            )
            n4 = InstagramFlowNode.objects.create(
                flow=flow,
                node_key='ask',
                node_type='ask_question',
                position_x=40,
                position_y=340,
                config={'text': 'راهنمایی بیشتری لازم داری؟'},
            )
            n5 = InstagramFlowNode.objects.create(
                flow=flow,
                node_key='agent',
                node_type='assign_agent',
                position_x=40,
                position_y=440,
                config={},
            )
            n6 = InstagramFlowNode.objects.create(
                flow=flow,
                node_key='stop',
                node_type='stop',
                position_x=40,
                position_y=540,
                config={},
            )
            for a, b in ((n1, n2), (n2, n3), (n3, n4), (n4, n5), (n5, n6)):
                InstagramFlowEdge.objects.create(flow=flow, source_node=a, target_node=b)
            flow.entry_node_id = 'tag'
            flow.definition = {
                'entry': 'tag',
                'nodes': [
                    {'id': n.node_key, 'type': n.node_type, 'x': n.position_x, 'y': n.position_y, 'config': n.config}
                    for n in (n1, n2, n3, n4, n5, n6)
                ],
                'edges': [
                    {'source': 'tag', 'target': 'intro'},
                    {'source': 'intro', 'target': 'product'},
                    {'source': 'product', 'target': 'ask'},
                    {'source': 'ask', 'target': 'agent'},
                    {'source': 'agent', 'target': 'stop'},
                ],
            }
            flow.save()

        rule, _ = InstagramAutomationRule.objects.get_or_create(
            workspace=ws,
            name='نمونه کلمه قیمت',
            defaults={
                'description': 'نمونه — در production فعال نشود',
                'trigger_type': InstagramAutomationRule.TriggerType.KEYWORD,
                'priority': 50,
                'is_active': False,
                'flow': flow,
                'schedule': {'keywords': ['قیمت']},
                'stop_after_match': True,
            },
        )
        if not rule.conditions.exists():
            InstagramRuleCondition.objects.create(
                rule=rule,
                field='text',
                operator='any_of',
                value=['قیمت'],
                normalize_persian=True,
            )

        self.stdout.write(self.style.SUCCESS(f'Seeded draft flow={flow.id} rule={rule.id} (inactive)'))
