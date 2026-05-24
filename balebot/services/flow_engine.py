"""موتور جریان /start: رندر، callback، لیبل درختی."""

from __future__ import annotations

import re
from typing import Any

from balebot.models import BotSettings, FlowMedia, Subscriber, SubscriberTag, Tag
from balebot.services import bale_api
from balebot.services.flow_sanitize import empty_start_flow, sanitize_start_flow

_FLOW_CB = re.compile(r'^f(n_[a-f0-9]{8})$')
_FLOW_BACK_CB = re.compile(r'^fb(n_[a-f0-9]{8})$')
_MAX_CB_LEN = 64
_MAX_LOOP_VISITS = 32


def get_flow(cfg: BotSettings) -> dict[str, Any]:
    raw = getattr(cfg, 'start_flow', None)
    if raw and isinstance(raw, dict) and raw.get('version') == 2:
        return sanitize_start_flow(raw)
    return empty_start_flow()


def parse_flow_callback(data: str) -> str | None:
    m = _FLOW_CB.match((data or '').strip())
    if m:
        return m.group(1)
    return None


def parse_flow_back_callback(data: str) -> str | None:
    m = _FLOW_BACK_CB.match((data or '').strip())
    if m:
        return m.group(1)
    return None


def encode_flow_callback(node_id: str) -> str:
    return f'f{node_id}'[:_MAX_CB_LEN]


def encode_flow_back_callback(node_id: str) -> str:
    return f'fb{node_id}'[:_MAX_CB_LEN]


class _ButtonRef:
    __slots__ = ('button', 'ancestors')

    def __init__(self, button: dict[str, Any], ancestors: list[dict[str, Any]]):
        self.button = button
        self.ancestors = ancestors


def _iter_buttons_in_rows(
    rows: list[Any],
    ancestors: list[dict[str, Any]],
) -> list[_ButtonRef]:
    out: list[_ButtonRef] = []
    if not isinstance(rows, list):
        return out
    for row in rows:
        if not isinstance(row, list):
            continue
        for btn in row:
            if isinstance(btn, dict) and btn.get('id'):
                out.append(_ButtonRef(btn, list(ancestors)))
    return out


def _collect_buttons_recursive(
    node: dict[str, Any],
    ancestors: list[dict[str, Any]],
) -> list[_ButtonRef]:
    refs: list[_ButtonRef] = []
    ntype = str(node.get('type', '')).lower()
    if ntype == 'sequence':
        for item in node.get('items') or []:
            if isinstance(item, dict):
                refs.extend(_collect_buttons_recursive(item, ancestors))
    elif ntype == 'buttons':
        rows = node.get('rows') or []
        refs.extend(_iter_buttons_in_rows(rows, ancestors))
        for row in rows:
            if not isinstance(row, list):
                continue
            for btn in row:
                if not isinstance(btn, dict):
                    continue
                action = btn.get('action')
                if isinstance(action, dict) and str(action.get('type', '')).lower() == 'buttons':
                    path = ancestors + [btn]
                    refs.extend(_collect_buttons_recursive(action, path))
    return refs


def find_button_by_id(cfg: BotSettings, node_id: str) -> _ButtonRef | None:
    flow = get_flow(cfg)
    root = flow.get('root') or {}
    for ref in _collect_buttons_recursive(root, []):
        if ref.button.get('id') == node_id:
            return ref
    return None


def label_slugs_for_button(ref: _ButtonRef) -> list[str]:
    slugs: list[str] = []
    for anc in ref.ancestors:
        s = (anc.get('label_slug') or '').strip()
        if s and s not in slugs:
            slugs.append(s)
    s = (ref.button.get('label_slug') or '').strip()
    if s and s not in slugs:
        slugs.append(s)
    return slugs


def get_or_create_tag_for_slug(slug: str, display_hint: str = '') -> Tag:
    slug = slug.strip()[:140]
    tag = Tag.objects.filter(slug=slug).first()
    if tag:
        return tag
    name = (display_hint or slug).strip()[:120] or slug
    return Tag.objects.create(
        name=name,
        slug=slug,
        tag_type=Tag.TagType.GENERIC,
        is_active=True,
    )


def assign_path_tags(sub: Subscriber, slugs: list[str], ref: _ButtonRef) -> None:
    hint = str(ref.button.get('text') or '')
    for slug in slugs:
        tag = get_or_create_tag_for_slug(slug, hint)
        SubscriberTag.objects.get_or_create(subscriber=sub, tag=tag)


def build_markup_for_buttons_node(
    buttons_node: dict[str, Any],
    *,
    parent_button_id: str | None = None,
) -> dict[str, Any] | None:
    rows_api: list[list[dict[str, str]]] = []
    for row in buttons_node.get('rows') or []:
        if not isinstance(row, list):
            continue
        out_row: list[dict[str, str]] = []
        for btn in row:
            if not isinstance(btn, dict):
                continue
            text = (btn.get('text') or '').strip()[:64]
            if not text:
                continue
            action = btn.get('action')
            if isinstance(action, dict) and str(action.get('type', '')).lower() == 'url':
                url = (action.get('url') or '').strip()
                if url:
                    out_row.append({'text': text, 'url': url[:512]})
                continue
            nid = btn.get('id')
            if not nid:
                continue
            cid = encode_flow_callback(str(nid))
            if len(cid) <= _MAX_CB_LEN:
                out_row.append({'text': text, 'callback_data': cid})
        if out_row:
            rows_api.append(out_row)
    if parent_button_id:
        bk = encode_flow_back_callback(parent_button_id)
        if len(bk) <= _MAX_CB_LEN and rows_api:
            rows_api.insert(0, [{'text': '« بازگشت', 'callback_data': bk}])
    if not rows_api:
        return None
    return {'inline_keyboard': rows_api}


def _extract_photo_file_id(resp: dict[str, Any]) -> str:
    if not isinstance(resp, dict):
        return ''
    result = resp.get('result') or resp
    photos = result.get('photo') or []
    if photos:
        return str(photos[-1].get('file_id') or '')
    return ''


def _cache_bale_file_id(media: FlowMedia, chat_id: int) -> str | None:
    if media.bale_file_id:
        return media.bale_file_id
    if not media.file or not media.file.name:
        return None
    try:
        resp = bale_api.send_photo(
            chat_id,
            photo_path=media.file.path,
            caption='',
        )
        fid = _extract_photo_file_id(resp)
        if fid:
            media.bale_file_id = fid[:512]
            media.save(update_fields=['bale_file_id'])
        return fid or None
    except bale_api.BaleAPIError:
        return media.bale_file_id or None


def send_image_node(chat_id: int, node: dict[str, Any]) -> None:
    media_id = str(node.get('media_id', '') or '')
    caption = (node.get('caption') or '').strip()[:1024]
    media = FlowMedia.objects.filter(pk=media_id).first()
    if not media or not media.file:
        return
    if media.bale_file_id:
        try:
            bale_api.send_photo(chat_id, photo_file_id=media.bale_file_id, caption=caption)
            return
        except bale_api.BaleAPIError:
            pass
    try:
        bale_api.send_photo(chat_id, photo_path=media.file.path, caption=caption)
        if not media.bale_file_id:
            _cache_bale_file_id(media, chat_id)
    except bale_api.BaleAPIError:
        pass


def send_sequence(chat_id: int, sequence: dict[str, Any]) -> dict[str, Any] | None:
    """ارسال آیتم‌های sequence؛ آخرین markup دکمه‌ها را برمی‌گرداند."""
    last_markup: dict[str, Any] | None = None
    items = sequence.get('items') or []
    for item in items:
        if not isinstance(item, dict):
            continue
        itype = str(item.get('type', '')).lower()
        if itype == 'text':
            body = (item.get('body') or '').strip()
            if body:
                try:
                    bale_api.send_message(chat_id, body[:4096])
                except bale_api.BaleAPIError:
                    pass
        elif itype == 'image':
            send_image_node(chat_id, item)
        elif itype == 'buttons':
            mk = build_markup_for_buttons_node(item)
            if mk:
                last_markup = mk
    return last_markup


def render_root_flow(cfg: BotSettings, chat_id: int) -> None:
    flow = get_flow(cfg)
    root = flow.get('root') or {}
    if str(root.get('type', '')).lower() != 'sequence':
        return
    markup = send_sequence(chat_id, root)
    if markup:
        markup = merge_support_into_markup(cfg, markup) or markup
        try:
            bale_api.send_message(chat_id, '\u2060', reply_markup=markup)
        except bale_api.BaleAPIError:
            pass
    elif cfg.enable_support:
        mk = merge_support_into_markup(cfg, None)
        if mk:
            try:
                bale_api.send_message(chat_id, '\u2060', reply_markup=mk)
            except bale_api.BaleAPIError:
                pass


def send_default_text(cfg: BotSettings, chat_id: int) -> None:
    txt = (cfg.start_flow_default_text or '').strip()
    if txt:
        try:
            bale_api.send_message(chat_id, txt[:4096])
        except bale_api.BaleAPIError:
            pass


def execute_button_action(
    cfg: BotSettings,
    ref: _ButtonRef,
    chat_id: int,
    *,
    message_id: int | None = None,
    visited: set[str] | None = None,
) -> str:
    """اجرای اکشن دکمه؛ flow_kind برای لاگ."""
    visited = visited or set()
    btn = ref.button
    btn_id = str(btn.get('id') or '')
    if btn_id in visited:
        send_default_text(cfg, chat_id)
        return 'loop_default'
    if btn_id:
        visited.add(btn_id)

    action = btn.get('action')
    if not action or not isinstance(action, dict):
        send_default_text(cfg, chat_id)
        return 'default'

    atype = str(action.get('type', '')).lower()
    if atype == 'text':
        body = (action.get('body') or btn.get('text') or '').strip()
        if body:
            try:
                bale_api.send_message(chat_id, body[:4096])
            except bale_api.BaleAPIError:
                pass
        else:
            send_default_text(cfg, chat_id)
        return 'text'

    if atype == 'image':
        send_image_node(chat_id, action)
        return 'image'

    if atype == 'url':
        return 'url'

    if atype == 'buttons':
        mk = build_markup_for_buttons_node(action, parent_button_id=btn_id)
        if mk and message_id:
            try:
                bale_api.edit_message_reply_markup(chat_id, int(message_id), reply_markup=mk)
                return 'buttons_edit'
            except bale_api.BaleAPIError:
                pass
        if mk:
            try:
                bale_api.send_message(chat_id, '\u2060', reply_markup=mk)
                return 'buttons'
            except bale_api.BaleAPIError:
                pass
        send_default_text(cfg, chat_id)
        return 'default'

    send_default_text(cfg, chat_id)
    return 'default'


def handle_flow_callback(
    cfg: BotSettings,
    sub: Subscriber,
    data: str,
    chat_id: int,
    message_id: int | None,
) -> tuple[str, str]:
    """پردازش f* / fb*؛ برمی‌گرداند (flow_kind, flow_label)."""
    back_id = parse_flow_back_callback(data)
    if back_id:
        ref = find_button_by_id(cfg, back_id)
        if ref is None:
            render_root_flow(cfg, chat_id)
            return 'back_root', ''
        parent = ref.ancestors[-1] if ref.ancestors else None
        if parent:
            pact = parent.get('action')
            if isinstance(pact, dict) and str(pact.get('type', '')).lower() == 'buttons':
                mk = build_markup_for_buttons_node(
                    pact,
                    parent_button_id=str(parent.get('id') or '') or None,
                )
                if mk and message_id:
                    try:
                        bale_api.edit_message_reply_markup(
                            chat_id, int(message_id), reply_markup=mk,
                        )
                    except bale_api.BaleAPIError:
                        pass
                return 'back', str(parent.get('text') or '')[:128]
        render_root_flow(cfg, chat_id)
        return 'back_root', ''

    node_id = parse_flow_callback(data)
    if not node_id:
        return 'invalid', ''

    ref = find_button_by_id(cfg, node_id)
    if ref is None:
        send_default_text(cfg, chat_id)
        return 'unknown_button', ''

    slugs = label_slugs_for_button(ref)
    if slugs:
        assign_path_tags(sub, slugs, ref)

    if len(slugs) > _MAX_LOOP_VISITS:
        send_default_text(cfg, chat_id)
        return 'loop_default', str(ref.button.get('text') or '')[:128]

    kind = execute_button_action(
        cfg, ref, chat_id, message_id=message_id, visited=set(),
    )
    return kind, str(ref.button.get('text') or '')[:128]


def build_support_row(settings_obj: BotSettings) -> list[dict[str, str]] | None:
    if not settings_obj.enable_support:
        return None
    support_label = (settings_obj.support_button_label or 'پیام به پشتیبانی').strip()[:64]
    if not support_label:
        return None
    return [{'text': support_label, 'callback_data': 'bsup'}]


def merge_support_into_markup(
    settings_obj: BotSettings,
    base_markup: dict[str, Any] | None,
) -> dict[str, Any] | None:
    support_row = build_support_row(settings_obj)
    if not support_row:
        return base_markup
    if base_markup and isinstance(base_markup, dict):
        rows = list(base_markup.get('inline_keyboard') or [])
        rows.append(support_row)
        return {'inline_keyboard': rows}
    return {'inline_keyboard': [support_row]}
