"""موتور جریان /start: رندر، callback، لیبل درختی."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from balebot.models import BotSettings, FlowMedia, Platform, Subscriber, SubscriberTag, Tag
from balebot.services import messenger_api
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


def get_or_create_tag_for_slug(slug: str, platform: str, display_hint: str = '') -> Tag:
    slug = slug.strip()[:140]
    tag = Tag.objects.filter(platform=platform, slug=slug).first()
    if tag:
        return tag
    name = (display_hint or slug).strip()[:120] or slug
    return Tag.objects.create(
        name=name,
        slug=slug,
        platform=platform,
        tag_type=Tag.TagType.GENERIC,
        is_active=True,
    )


def assign_path_tags(sub: Subscriber, slugs: list[str], ref: _ButtonRef) -> None:
    hint = str(ref.button.get('text') or '')
    for slug in slugs:
        tag = get_or_create_tag_for_slug(slug, sub.platform, hint)
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
    payload = result.get('photo')
    if isinstance(payload, list):
        if payload:
            return str(payload[-1].get('file_id') or '')
        return ''
    if isinstance(payload, dict):
        return str(payload.get('file_id') or '')
    return ''


def _send_flow_media_upload(
    platform: str,
    media: FlowMedia,
    chat_id: int,
    *,
    caption: str = '',
) -> dict[str, Any]:
    """آپلود فایل FlowMedia به بله (بدون وابستگی به مسیر محلی روی دیسک)."""
    if not media.file or not media.file.name:
        raise messenger_api.MessengerAPIError('فایل عکس در سرور یافت نشد.')
    with media.file.open('rb') as f:
        return messenger_api.send_photo(
            platform,
            chat_id,
            photo_file=f,
            photo_filename=Path(media.file.name).name,
            caption=caption,
        )


def _store_messenger_file_id(media: FlowMedia, resp: dict[str, Any]) -> None:
    fid = _extract_photo_file_id(resp)
    if fid and fid != media.messenger_file_id:
        media.messenger_file_id = fid[:512]
        media.save(update_fields=['messenger_file_id'])


def send_image_node(cfg: BotSettings, chat_id: int, node: dict[str, Any]) -> bool:
    platform = cfg.platform
    media_id = str(node.get('media_id', '') or '').strip()
    caption = (node.get('caption') or '').strip()[:1024]
    if not media_id:
        return False
    media = FlowMedia.objects.filter(pk=media_id, platform=platform).first()
    if not media or not media.file or not media.file.name:
        return False

    if media.messenger_file_id:
        try:
            messenger_api.send_photo(
                platform,
                chat_id,
                photo_file_id=media.messenger_file_id,
                caption=caption,
            )
            return True
        except messenger_api.MessengerAPIError:
            media.messenger_file_id = ''
            media.save(update_fields=['messenger_file_id'])

    try:
        resp = _send_flow_media_upload(platform, media, chat_id, caption=caption)
        _store_messenger_file_id(media, resp)
        return True
    except messenger_api.MessengerAPIError:
        return False


def _append_markup_rows(
    merged_rows: list[list[dict[str, str]]],
    markup: dict[str, Any] | None,
) -> None:
    if not markup:
        return
    for row in markup.get('inline_keyboard') or []:
        if row:
            merged_rows.append(row)


def send_sequence(cfg: BotSettings, chat_id: int, sequence: dict[str, Any]) -> dict[str, Any] | None:
    """ارسال آیتم‌های sequence؛ ردیف‌های همهٔ بلوک‌های دکمه را ادغام و برمی‌گرداند."""
    platform = cfg.platform
    merged_rows: list[list[dict[str, str]]] = []
    items = sequence.get('items') or []
    for item in items:
        if not isinstance(item, dict):
            continue
        itype = str(item.get('type', '')).lower()
        if itype == 'text':
            body = (item.get('body') or '').strip()
            if body:
                try:
                    messenger_api.send_message(platform, chat_id, body[:4096])
                except messenger_api.MessengerAPIError:
                    pass
        elif itype == 'image':
            send_image_node(cfg, chat_id, item)
        elif itype == 'buttons':
            _append_markup_rows(merged_rows, build_markup_for_buttons_node(item))
    if merged_rows:
        return {'inline_keyboard': merged_rows}
    return None


def render_root_flow(cfg: BotSettings, chat_id: int) -> None:
    platform = cfg.platform
    flow = get_flow(cfg)
    root = flow.get('root') or {}
    if str(root.get('type', '')).lower() != 'sequence':
        return
    markup = send_sequence(cfg, chat_id, root)
    if markup:
        markup = merge_support_into_markup(cfg, markup) or markup
        try:
            messenger_api.send_message(platform, chat_id, '\u2060', reply_markup=markup)
        except messenger_api.MessengerAPIError:
            pass
    elif cfg.enable_support:
        mk = merge_support_into_markup(cfg, None)
        if mk:
            try:
                messenger_api.send_message(platform, chat_id, '\u2060', reply_markup=mk)
            except messenger_api.MessengerAPIError:
                pass


def send_default_text(cfg: BotSettings, chat_id: int) -> None:
    platform = cfg.platform
    txt = (cfg.start_flow_default_text or '').strip()
    if txt:
        try:
            messenger_api.send_message(platform, chat_id, txt[:4096])
        except messenger_api.MessengerAPIError:
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
    platform = cfg.platform
    if atype == 'text':
        body = (action.get('body') or btn.get('text') or '').strip()
        if body:
            try:
                messenger_api.send_message(platform, chat_id, body[:4096])
            except messenger_api.MessengerAPIError:
                pass
        else:
            send_default_text(cfg, chat_id)
        return 'text'

    if atype == 'image':
        if not send_image_node(cfg, chat_id, action):
            send_default_text(cfg, chat_id)
            return 'image_failed'
        return 'image'

    if atype == 'url':
        return 'url'

    if atype == 'buttons':
        mk = build_markup_for_buttons_node(action, parent_button_id=btn_id)
        if mk and message_id:
            try:
                messenger_api.edit_message_reply_markup(
                    platform, chat_id, int(message_id), reply_markup=mk,
                )
                return 'buttons_edit'
            except messenger_api.MessengerAPIError:
                pass
        if mk:
            try:
                messenger_api.send_message(platform, chat_id, '\u2060', reply_markup=mk)
                return 'buttons'
            except messenger_api.MessengerAPIError:
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
                        messenger_api.edit_message_reply_markup(
                            cfg.platform, chat_id, int(message_id), reply_markup=mk,
                        )
                    except messenger_api.MessengerAPIError:
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
