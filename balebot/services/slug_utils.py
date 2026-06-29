"""ساخت نامک انگلیسی یکتا از عنوان فارسی/لاتین."""

from __future__ import annotations

from django.db.models import QuerySet
from django.utils.text import slugify

_PERSIAN_TO_LATIN: dict[str, str] = {
    'آ': 'a', 'ا': 'a', 'أ': 'a', 'إ': 'a', 'ء': '',
    'ب': 'b', 'پ': 'p', 'ت': 't', 'ث': 's', 'ج': 'j', 'چ': 'ch',
    'ح': 'h', 'خ': 'kh', 'د': 'd', 'ذ': 'z', 'ر': 'r', 'ز': 'z', 'ژ': 'zh',
    'س': 's', 'ش': 'sh', 'ص': 's', 'ض': 'z', 'ط': 't', 'ظ': 'z',
    'ع': 'a', 'غ': 'gh', 'ف': 'f', 'ق': 'gh', 'ک': 'k', 'ك': 'k',
    'گ': 'g', 'ل': 'l', 'م': 'm', 'ن': 'n', 'و': 'v', 'ؤ': 'o',
    'ه': 'h', 'ة': 'h', 'ی': 'y', 'ي': 'y', 'ئ': 'y', '‌': '-',
}
for idx, digit in enumerate('۰۱۲۳۴۵۶۷۸۹'):
    _PERSIAN_TO_LATIN[digit] = str(idx)
for idx, digit in enumerate('٠١٢٣٤٥٦٧٨٩'):
    _PERSIAN_TO_LATIN[digit] = str(idx)


def transliterate_to_latin(text: str) -> str:
    if not text:
        return ''
    parts: list[str] = []
    for ch in str(text):
        if ch in _PERSIAN_TO_LATIN:
            parts.append(_PERSIAN_TO_LATIN[ch])
        else:
            parts.append(ch)
    return ''.join(parts)


def slug_from_text(text: str, *, fallback: str = 'item', max_length: int = 140) -> str:
    raw = transliterate_to_latin(text or '')
    slug = slugify(raw, allow_unicode=False) or ''
    if not slug:
        slug = fallback
    return slug[:max_length]


def ensure_unique_slug(
    queryset: QuerySet,
    base_slug: str,
    *,
    exclude_pk=None,
    max_length: int = 140,
) -> str:
    base = (base_slug or 'item')[:max_length]
    slug = base
    counter = 2
    qs = queryset
    if exclude_pk is not None:
        qs = qs.exclude(pk=exclude_pk)
    while qs.filter(slug=slug).exists():
        suffix = f'-{counter}'
        slug = f'{base[: max_length - len(suffix)]}{suffix}'
        counter += 1
    return slug


def resolve_model_slug(
    model,
    source_text: str,
    *,
    manual_slug: str = '',
    workspace=None,
    platform=None,
    exclude_pk=None,
    fallback: str = 'item',
    max_length: int = 140,
) -> str:
    manual = (manual_slug or '').strip()
    if manual:
        base = slug_from_text(manual, fallback=fallback, max_length=max_length)
    else:
        base = slug_from_text(source_text, fallback=fallback, max_length=max_length)
    qs = model.objects.filter(workspace=workspace, platform=platform)
    return ensure_unique_slug(qs, base, exclude_pk=exclude_pk, max_length=max_length)
