from __future__ import annotations

import re
import unicodedata


_ARABIC_YEH = '\u064a'
_FARSI_YEH = '\u06cc'
_ARABIC_KEH = '\u0643'
_FARSI_KEH = '\u06a9'
_TATWEEL = '\u0640'
_ZWNJ = '\u200c'

_DIACRITICS_RE = re.compile(r'[\u064B-\u065F\u0670]')
_MULTI_SPACE_RE = re.compile(r'\s+')

_FA_DIGITS = str.maketrans('۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩', '01234567890123456789')

# محدودیت ReDoS
MAX_REGEX_LENGTH = 80
MAX_REGEX_MATCH_INPUT = 2000


def normalize_persian(
    text: str,
    *,
    strip_diacritics: bool = True,
    unify_digits: bool = True,
    lower_english: bool = True,
) -> str:
    if not text:
        return ''
    s = unicodedata.normalize('NFKC', text)
    s = s.replace(_ARABIC_YEH, _FARSI_YEH).replace(_ARABIC_KEH, _FARSI_KEH)
    s = s.replace(_TATWEEL, '')
    s = s.replace(_ZWNJ, ' ')
    if strip_diacritics:
        s = _DIACRITICS_RE.sub('', s)
    if unify_digits:
        s = s.translate(_FA_DIGITS)
    if lower_english:
        s = s.lower()
    s = _MULTI_SPACE_RE.sub(' ', s).strip()
    return s


def safe_compile_regex(pattern: str) -> re.Pattern | None:
    if not pattern or len(pattern) > MAX_REGEX_LENGTH:
        return None
    # الگوهای خطرناک ساده
    if '(?!' in pattern or '(?=' in pattern or '{,' in pattern:
        return None
    if re.search(r'[\*\+\?]{2,}|\{\d{3,}', pattern):
        return None
    try:
        return re.compile(pattern, re.UNICODE)
    except re.error:
        return None


def match_text(
    text: str,
    *,
    operator: str,
    value,
    case_sensitive: bool = False,
    normalize: bool = True,
) -> bool:
    hay = text or ''
    if normalize:
        hay = normalize_persian(hay, lower_english=not case_sensitive)
    elif not case_sensitive:
        hay = hay.lower()

    def norm_needle(n: str) -> str:
        if normalize:
            return normalize_persian(n, lower_english=not case_sensitive)
        return n if case_sensitive else n.lower()

    if operator == 'eq':
        return hay == norm_needle(str(value))
    if operator == 'contains':
        return norm_needle(str(value)) in hay
    if operator == 'starts_with':
        return hay.startswith(norm_needle(str(value)))
    if operator == 'ends_with':
        return hay.endswith(norm_needle(str(value)))
    if operator in ('any_of', 'all_of', 'not_contains'):
        items = value if isinstance(value, list) else [value]
        needles = [norm_needle(str(x)) for x in items if str(x).strip()]
        if operator == 'any_of':
            return any(n in hay for n in needles)
        if operator == 'all_of':
            return all(n in hay for n in needles) if needles else False
        if operator == 'not_contains':
            return all(n not in hay for n in needles)
    if operator == 'regex':
        compiled = safe_compile_regex(str(value))
        if not compiled:
            return False
        return bool(compiled.search(hay[:MAX_REGEX_MATCH_INPUT]))
    return False
