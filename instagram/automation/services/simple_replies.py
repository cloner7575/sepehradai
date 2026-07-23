"""ساخت سناریوی ساده بدون بیلدر بصری — مثل پاسخ ربات به کلمه کلیدی."""

from __future__ import annotations

from django.utils import timezone

from balebot.models import CatalogItem, CatalogSettings
from instagram.automation.models import (
    InstagramAutomationRule,
    InstagramFlow,
    InstagramFlowEdge,
    InstagramFlowNode,
    InstagramRuleCondition,
)


PRESETS = [
    {
        'key': 'price',
        'title': 'پاسخ به «قیمت»',
        'description': 'وقتی مشتری قیمت پرسید، لینک فروشگاه یا محصول را بفرست.',
        'keywords': ['قیمت', 'چنده', 'چند'],
        'reply': 'سلام! برای دیدن قیمت به‌روز و ثبت سفارش از فروشگاه راحت‌سل استفاده کنید:',
        'include_store_link': True,
        'handoff': False,
    },
    {
        'key': 'order',
        'title': 'پیگیری سفارش',
        'description': 'درخواست وضعیت سفارش را به کارشناس وصل کن.',
        'keywords': ['سفارشم', 'سفارش', 'کجا سفارش'],
        'reply': 'برای پیگیری سفارش، لطفاً شماره تماس یا کد سفارش را بفرستید. یک کارشناس به‌زودی پاسخ می‌دهد.',
        'include_store_link': False,
        'handoff': True,
    },
    {
        'key': 'support',
        'title': 'پشتیبانی',
        'description': 'پیام‌های کمک/پشتیبانی را به کارشناس بسپار.',
        'keywords': ['پشتیبانی', 'کمک', 'مشاوره'],
        'reply': 'پیامتان را دریافت کردیم. یکی از کارشناسان به‌زودی پاسخ می‌دهد.',
        'include_store_link': False,
        'handoff': True,
    },
    {
        'key': 'welcome',
        'title': 'خوش‌آمدگویی',
        'description': 'اولین پیام مخاطب با معرفی کوتاه فروشگاه جواب داده شود.',
        'keywords': ['سلام', 'درود', 'hi', 'hello'],
        'reply': 'سلام! به صفحه ما خوش آمدید. می‌توانید از فروشگاه آنلاین سفارش دهید یا سؤالتان را همین‌جا بپرسید.',
        'include_store_link': True,
        'handoff': False,
        'trigger_type': 'welcome',
    },
]


def shop_public_url(workspace) -> str:
    cfg = (
        CatalogSettings.objects.filter(workspace=workspace, is_enabled=True)
        .order_by('-updated_at')
        .first()
    )
    if not cfg:
        cfg = CatalogSettings.objects.filter(workspace=workspace).order_by('-updated_at').first()
    if not cfg:
        return ''
    # مسیر نسبی فروشگاه — دامنه در پیام/لینک کوتاه کامل می‌شود
    return f'/shop/{cfg.public_id}/'


def build_simple_flow_definition(
    *,
    reply_text: str,
    store_url: str = '',
    product: CatalogItem | None = None,
    handoff: bool = False,
    use_source_product: bool = False,
) -> dict:
    nodes = []
    edges = []
    x, y = 40, 40

    def add(node_id: str, node_type: str, config: dict):
        nonlocal y
        nodes.append({'id': node_id, 'type': node_type, 'x': x, 'y': y, 'config': config})
        y += 100

    if product or use_source_product:
        template = (reply_text or '').strip()
        if '{{ product.' not in template and '{{ checkout_url }}' not in template:
            template = (f'{template}\n' if template else '') + (
                '{{ product.title }}\nقیمت: {{ product.price }} ریال\n'
                'وضعیت: {{ product.stock_status }}\n{{ checkout_url }}'
            )
        add('product', 'send_product', {
            'product_id': product.pk if product else None,
            'template': template,
            'fallback_text': 'این محصول فعلاً در دسترس نیست. از فروشگاه بازدید کنید.',
        })
        prev = entry = 'product'
    else:
        text = reply_text or 'سلام!'
        if store_url:
            text = f'{text}\nفروشگاه: {store_url}'
        add('intro', 'send_text', {'text': text})
        prev = entry = 'intro'

    if handoff:
        add('agent', 'assign_agent', {})
        edges.append({'source': prev, 'target': 'agent'})
        prev = 'agent'
        add('pause', 'pause_automation', {'permanent': True})
        edges.append({'source': prev, 'target': 'pause'})
        prev = 'pause'

    add('stop', 'stop', {})
    edges.append({'source': prev, 'target': 'stop'})

    return {'entry': entry, 'nodes': nodes, 'edges': edges}


def sync_rule_simple_flow(
    *,
    rule: InstagramAutomationRule,
    reply_text: str,
    include_store_link: bool = False,
    product_id: int | None = None,
    handoff: bool = False,
    user=None,
) -> InstagramFlow:
    ws = rule.workspace
    store_url = shop_public_url(ws) if include_store_link else ''
    product = None
    if product_id:
        product = CatalogItem.objects.filter(pk=product_id, workspace=ws, is_active=True).first()

    definition = build_simple_flow_definition(
        reply_text=reply_text,
        store_url=store_url,
        product=product,
        handoff=handoff,
        use_source_product=(rule.schedule or {}).get('content_scope') == 'product_bound',
    )

    flow = rule.flow
    if flow is None:
        flow = InstagramFlow.objects.create(
            workspace=ws,
            name=f'پاسخ: {rule.name}'[:200],
            description='ساخته‌شده خودکار از پاسخ ساده',
            status=InstagramFlow.Status.ACTIVE,
            entry_node_id=definition['entry'],
            definition=definition,
            created_by=user,
            published_at=timezone.now(),
        )
        rule.flow = flow
    else:
        flow.name = f'پاسخ: {rule.name}'[:200]
        flow.definition = definition
        flow.entry_node_id = definition['entry']
        flow.status = InstagramFlow.Status.ACTIVE
        flow.published_at = timezone.now()
        flow.save()

    InstagramFlowNode.objects.filter(flow=flow).delete()
    key_map = {}
    for n in definition['nodes']:
        node = InstagramFlowNode.objects.create(
            flow=flow,
            node_key=n['id'],
            node_type=n['type'],
            position_x=n.get('x') or 0,
            position_y=n.get('y') or 0,
            config=n.get('config') or {},
        )
        key_map[n['id']] = node
    for e in definition['edges']:
        InstagramFlowEdge.objects.create(
            flow=flow,
            source_node=key_map[e['source']],
            target_node=key_map[e['target']],
        )

    rule.schedule = {
        **(rule.schedule or {}),
        'reply_text': reply_text,
        'include_store_link': include_store_link,
        'product_id': product.pk if product else None,
        'handoff': handoff,
        'simple_mode': True,
    }
    rule.save(update_fields=['flow', 'schedule', 'updated_at'])
    return flow


def apply_preset(*, workspace, user, preset_key: str, connection=None) -> InstagramAutomationRule:
    preset = next((p for p in PRESETS if p['key'] == preset_key), None)
    if not preset:
        raise ValueError('سناریوی آماده یافت نشد.')

    name = preset['title']
    rule, created = InstagramAutomationRule.objects.get_or_create(
        workspace=workspace,
        name=name,
        defaults={
            'description': preset['description'],
            'trigger_type': preset.get('trigger_type') or InstagramAutomationRule.TriggerType.KEYWORD,
            'priority': 40,
            'is_active': True,
            'stop_after_match': True,
            'cooldown_seconds': 120,
            'created_by': user,
            'connection': connection,
            'schedule': {'keywords': preset['keywords']},
        },
    )
    if not created:
        rule.description = preset['description']
        rule.is_active = True
        rule.schedule = {**(rule.schedule or {}), 'keywords': preset['keywords']}
        rule.save()

    InstagramRuleCondition.objects.filter(rule=rule).delete()
    InstagramRuleCondition.objects.create(
        rule=rule,
        field='text',
        operator='any_of',
        value=preset['keywords'],
        normalize_persian=True,
    )
    sync_rule_simple_flow(
        rule=rule,
        reply_text=preset['reply'],
        include_store_link=bool(preset.get('include_store_link')),
        handoff=bool(preset.get('handoff')),
        user=user,
    )
    return rule
