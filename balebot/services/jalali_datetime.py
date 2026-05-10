"""تبدیل تاریخ/زمان شمسی به datetime آگاه از منطقهٔ زمانی (پیش‌فرض تهران)."""

from __future__ import annotations

import re
from datetime import datetime

import jdatetime
from django.conf import settings
from django.utils import timezone
from zoneinfo import ZoneInfo

_FA_DIGITS = str.maketrans('۰۱۲۳۴۵۶۷۸۹', '0123456789')


def normalize_digits(s: str) -> str:
    return (s or '').translate(_FA_DIGITS).strip()


def parse_jalali_date_time(date_str: str, time_str: str) -> datetime:
    """
    رشتهٔ تاریخ شمسی (سال/ماه/روز) و زمان (ساعت:دقیقه) را به datetime آگاه از منطقه
    برمی‌گرداند.
    """
    tz_name = getattr(settings, 'TIME_ZONE', None) or 'Asia/Tehran'
    tz = ZoneInfo(tz_name)

    ds = normalize_digits(date_str).replace('-', '/')
    parts = [p.strip() for p in ds.split('/') if p.strip()]
    if len(parts) != 3:
        raise ValueError('تاریخ را به صورت سال/ماه/روز شمسی وارد کنید (مثلاً ۱۴۰۳/۰۸/۱۵).')
    y, m, d = int(parts[0]), int(parts[1]), int(parts[2])

    ts = normalize_digits(time_str)
    tm = re.match(r'^(\d{1,2}):(\d{2})(?::(\d{2}))?$', ts)
    if not tm:
        raise ValueError('زمان را به صورت ساعت:دقیقه وارد کنید (مثلاً ۱۴:۳۰).')
    hh, mm = int(tm.group(1)), int(tm.group(2))
    ss = int(tm.group(3) or 0)

    jdt = jdatetime.datetime(y, m, d, hh, mm, ss)
    g = jdt.togregorian()
    return timezone.make_aware(
        datetime(g.year, g.month, g.day, g.hour, g.minute, g.second),
        tz,
    )


def aware_to_jalali_parts(dt: datetime | None) -> tuple[str, str]:
    """datetime آگاه را به (تاریخ شمسی Y/m/d، زمان H:M) تبدیل می‌کند."""
    if dt is None:
        return '', ''
    local = timezone.localtime(dt)
    jd = jdatetime.datetime.fromgregorian(datetime=local.replace(tzinfo=None))
    return jd.strftime('%Y/%m/%d'), jd.strftime('%H:%M')
