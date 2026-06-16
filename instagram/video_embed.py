"""Helpers for Instagram app UI."""

import re
from urllib.parse import parse_qs, urlparse

_YOUTUBE_RE = re.compile(
    r'(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/)([\w-]{11})',
)
_APARAT_RE = re.compile(r'aparat\.com/v/([\w-]+)')


def video_url_to_embed(url: str) -> str:
    """Convert common video page URLs to iframe embed URLs."""
    url = (url or '').strip()
    if not url:
        return ''

    if 'youtube.com/embed/' in url or 'aparat.com/video/video/embed' in url:
        return url

    yt = _YOUTUBE_RE.search(url)
    if yt:
        return f'https://www.youtube.com/embed/{yt.group(1)}?rel=0'

    ap = _APARAT_RE.search(url)
    if ap:
        return f'https://www.aparat.com/video/video/embed/videohash/{ap.group(1)}/vt/frame'

    parsed = urlparse(url)
    if parsed.scheme in ('http', 'https') and parsed.netloc:
        return url

    return ''
