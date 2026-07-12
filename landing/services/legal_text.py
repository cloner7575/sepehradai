import re

from django.utils.html import escape, mark_safe
from django.utils.safestring import SafeString

_HEADING_RE = re.compile(r'^(#{1,3})\s+(.+)$')
_BULLET_RE = re.compile(r'^[-*•–—]\s+(.+)$')


def normalize_legal_text(value: str | None) -> str:
    """یکسان‌سازی خط‌شکن‌ها برای ذخیره و نمایش."""
    text = str(value or '')
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    text = text.replace('\u2028', '\n').replace('\u2029', '\n\n')
    text = text.replace('\u00a0', ' ')
    lines = [line.rstrip() for line in text.split('\n')]
    return '\n'.join(lines).strip()


def format_legal_text_html(value: str | SafeString | None) -> str:
    """تبدیل متن قوانین به HTML — هر خط جدا نمایش داده می‌شود."""
    text = normalize_legal_text(str(value or ''))
    if not text:
        return ''

    parts: list[str] = []
    bullet_items: list[str] = []

    def flush_bullets() -> None:
        if bullet_items:
            items = ''.join(f'<li>{escape(item)}</li>' for item in bullet_items)
            parts.append(f'<ul>{items}</ul>')
            bullet_items.clear()

    for raw_line in text.split('\n'):
        line = raw_line.strip()
        if not line:
            flush_bullets()
            continue

        heading = _HEADING_RE.match(line)
        if heading:
            flush_bullets()
            level = len(heading.group(1))
            tag = 'h2' if level <= 2 else 'h3'
            parts.append(f'<{tag}>{escape(heading.group(2))}</{tag}>')
            continue

        bullet = _BULLET_RE.match(line)
        if bullet:
            bullet_items.append(bullet.group(1))
            continue

        flush_bullets()
        parts.append(f'<p>{escape(line)}</p>')

    flush_bullets()
    return mark_safe(''.join(parts))
