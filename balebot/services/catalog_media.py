"""ابزارهای رسانه کاتالوگ."""

from __future__ import annotations

import os

IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg', '.bmp', '.avif'}
VIDEO_EXTENSIONS = {'.mp4', '.webm', '.mov', '.avi', '.mkv', '.m4v', '.ogv'}


def detect_media_type(filename: str) -> str:
    ext = os.path.splitext(filename or '')[1].lower()
    if ext in IMAGE_EXTENSIONS:
        return 'image'
    if ext in VIDEO_EXTENSIONS:
        return 'video'
    return 'file'


def absolute_media_url(request, url: str) -> str:
    if not url:
        return ''
    if url.startswith('http://') or url.startswith('https://'):
        return url
    return request.build_absolute_uri(url)
