"""نمایش و تبدیل قیمت کاتالوگ — ذخیره‌سازی داخلی به ریال، نمایش به تومان."""

from __future__ import annotations

RIAL_PER_TOMAN = 10


def rial_to_toman(amount: int | None) -> int | None:
    if amount is None:
        return None
    return int(amount) // RIAL_PER_TOMAN


def toman_to_rial(amount: int | None) -> int | None:
    if amount is None:
        return None
    return int(amount) * RIAL_PER_TOMAN


def format_toman(amount_rial, *, empty: str = '—') -> str:
    """مقدار ریال را به رشتهٔ تومان با جداکننده هزارگان برمی‌گرداند."""
    if amount_rial is None or amount_rial == '':
        return empty
    try:
        toman = rial_to_toman(int(amount_rial))
    except (TypeError, ValueError):
        return str(amount_rial)
    return f'{toman:,}'


def format_toman_label(amount_rial, *, empty: str = '—') -> str:
    text = format_toman(amount_rial, empty=empty)
    if text == empty:
        return text
    return f'{text} تومان'


def format_number(value, *, empty: str = '—') -> str:
    """عدد خام (بدون تبدیل واحد) با جداکننده هزارگان."""
    if value is None or value == '':
        return empty
    try:
        return f'{int(value):,}'
    except (TypeError, ValueError):
        return str(value)
