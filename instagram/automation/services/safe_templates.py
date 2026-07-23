from __future__ import annotations

import re


VARIABLE_RE = re.compile(r'{{\s*([a-zA-Z0-9_.]+)\s*}}')
ALLOWED_VARIABLES = {
    'product.title',
    'product.price',
    'product.stock_status',
    'checkout_url',
    'store_url',
}


def validate_template(template: str) -> list[str]:
    unknown = sorted({name for name in VARIABLE_RE.findall(template or '') if name not in ALLOWED_VARIABLES})
    return [f'unsupported template variable: {name}' for name in unknown]


def render_template(template: str, context: dict) -> str:
    errors = validate_template(template)
    if errors:
        raise ValueError('; '.join(errors))

    def replace(match):
        name = match.group(1)
        current = context
        for part in name.split('.'):
            if isinstance(current, dict):
                current = current.get(part, '')
            else:
                current = getattr(current, part, '')
        return str(current if current is not None else '')

    return VARIABLE_RE.sub(replace, template or '')


def product_template_context(item, *, checkout_url: str, store_url: str) -> dict:
    status = 'available' if item.stock is None or item.stock > 0 else 'out_of_stock'
    return {
        'product': {
            'title': item.title,
            'price': f'{int(item.price or 0):,}',
            'stock_status': status,
        },
        'checkout_url': checkout_url,
        'store_url': store_url,
    }
