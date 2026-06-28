"""موتور جریان /start: رندر، callback، لیبل درختی."""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlunparse, urlparse

from django.db import IntegrityError

from balebot.models import BotSettings, FlowMedia, Platform, Subscriber, SubscriberTag, Tag, Workspace
from balebot.services import messenger_api
from balebot.services.flow_sanitize import empty_start_flow, sanitize_start_flow

logger = logging.getLogger(__name__)

_FLOW_CB = re.compile(r'^f(n_[a-f0-9]{8})$')
_FLOW_BACK_CB = re.compile(r'^fb(n_[a-f0-9]{8})$')
_MAX_CB_LEN = 64
_MAX_LOOP_VISITS = 32

_INTERACTIVE_ACTION_TYPES = frozenset({
    'webapp', 'order_status', 'my_orders', 'invoice', 'location_card', 'contact_card',
    'input', 'form', 'request_contact', 'request_location',
    'condition', 'goto', 'join_gate', 'tag', 'faq', 'coupon', 'handoff',
})


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


def category_slugs_for_button(ref: _ButtonRef) -> list[str]:
    slugs: list[str] = []
    for anc in ref.ancestors:
        s = (anc.get('category_slug') or '').strip()
        if s and s not in slugs:
            slugs.append(s)
    s = (ref.button.get('category_slug') or '').strip()
    if s and s not in slugs:
        slugs.append(s)
    return slugs


def get_or_create_tag_for_slug(
    slug: str,
    platform: str,
    workspace: Workspace,
    display_hint: str = '',
) -> Tag | None:
    slug = slug.strip()[:140]
    if not slug:
        return None

    tag = Tag.objects.filter(workspace=workspace, platform=platform, slug=slug).first()
    if tag:
        return tag

    base_name = (display_hint or slug).strip()[:120] or slug
    name = base_name
    if Tag.objects.filter(workspace=workspace, platform=platform, name=name).exists():
        suffix = f' - {slug}'
        max_base = max(1, 120 - len(suffix))
        name = f'{base_name[:max_base]}{suffix}'[:120]

    for i in range(5):
        try:
            return Tag.objects.create(
                workspace=workspace,
                name=name,
                slug=slug,
                platform=platform,
                tag_type=Tag.TagType.GENERIC,
                is_active=True,
            )
        except IntegrityError:
            tag = Tag.objects.filter(workspace=workspace, platform=platform, slug=slug).first()
            if tag:
                return tag
            name = f'{base_name[:112]}-{i + 2}'[:120]

    tag = Tag.objects.filter(workspace=workspace, platform=platform, slug=slug).first()
    if tag:
        return tag
    logger.warning(
        'Could not create tag for slug=%r workspace=%s platform=%s',
        slug,
        workspace.pk,
        platform,
    )
    return None


def assign_path_tags(sub: Subscriber, slugs: list[str], ref: _ButtonRef) -> None:
    hint = str(ref.button.get('text') or '')
    for slug in slugs:
        tag = get_or_create_tag_for_slug(slug, sub.platform, sub.workspace, hint)
        if tag is None:
            continue
        SubscriberTag.objects.get_or_create(subscriber=sub, tag=tag)


def normalize_inline_url(
    raw: str,
    *,
    cfg: BotSettings | None = None,
) -> str:
    """آدرس دکمه inline (لینک) را برای API بله/تلگرام نرمال و اعتبارسنجی می‌کند."""
    url = (raw or '').strip()
    if not url:
        return ''
    if url.startswith('/'):
        if cfg is None:
            return ''
        from balebot.services.public_url import resolve_public_base_url

        base = resolve_public_base_url(cfg).rstrip('/')
        if not base:
            return ''
        url = f'{base}{url}'
    if not url.startswith(('http://', 'https://')):
        url = f'https://{url.lstrip("/")}'

    parsed = urlparse(url)
    if not parsed.netloc:
        return ''

    host = (parsed.hostname or '').lower()
    if not host or host in {'localhost', '127.0.0.1', '0.0.0.0', '::1'}:
        return ''

    if parsed.scheme == 'http':
        parsed = parsed._replace(scheme='https')
        url = urlunparse(parsed)
    elif parsed.scheme != 'https':
        return ''

    return url[:512]


def _button_api_entry(
    btn: dict[str, Any],
    text: str,
    *,
    cfg: BotSettings | None,
) -> dict[str, Any] | None:
    action = btn.get('action')
    if isinstance(action, dict):
        atype = str(action.get('type', '')).lower()
        raw_url = action.get('url') or ''
        if atype == 'url':
            url = normalize_inline_url(raw_url, cfg=cfg)
            if url:
                return {'text': text, 'url': url}
            logger.warning(
                'Invalid inline url button; using callback. text=%r raw=%r',
                text,
                raw_url,
            )
        if atype == 'webapp':
            from balebot.services.flow_interactive import _build_webapp_url
            target = action.get('target') if isinstance(action.get('target'), dict) else None
            url = _build_webapp_url(cfg, target) if cfg else ''
            if url:
                return {'text': text, 'web_app': {'url': url}}

    nid = btn.get('id')
    if not nid:
        return None
    cid = encode_flow_callback(str(nid))
    if len(cid) <= _MAX_CB_LEN:
        return {'text': text, 'callback_data': cid}
    return None


def build_markup_for_buttons_node(
    buttons_node: dict[str, Any],
    *,
    parent_button_id: str | None = None,
    cfg: BotSettings | None = None,
) -> dict[str, Any] | None:
    rows_api: list[list[dict[str, Any]]] = []
    for row in buttons_node.get('rows') or []:
        if not isinstance(row, list):
            continue
        out_row: list[dict[str, Any]] = []
        for btn in row:
            if not isinstance(btn, dict):
                continue
            text = (btn.get('text') or '').strip()[:64]
            if not text:
                continue
            entry = _button_api_entry(btn, text, cfg=cfg)
            if entry:
                out_row.append(entry)
        if out_row:
            rows_api.append(out_row)
    if parent_button_id:
        bk = encode_flow_back_callback(parent_button_id)
        if len(bk) <= _MAX_CB_LEN and rows_api:
            rows_api.insert(0, [{'text': '« بازگشت', 'callback_data': bk}])
    if not rows_api:
        return None
    return {'inline_keyboard': rows_api}


def _strip_url_buttons_from_markup(markup: dict[str, Any]) -> dict[str, Any] | None:
    rows_out: list[list[dict[str, Any]]] = []
    for row in markup.get('inline_keyboard') or []:
        if not isinstance(row, list):
            continue
        kept = [
            btn for btn in row
            if isinstance(btn, dict) and 'url' not in btn and 'web_app' not in btn
        ]
        if kept:
            rows_out.append(kept)
    if not rows_out:
        return None
    return {'inline_keyboard': rows_out}


def _extract_messenger_file_id(resp: dict[str, Any], media_kind: str) -> str:
    if not isinstance(resp, dict):
        return ''
    result = resp.get('result') or resp
    kind = str(media_kind or 'photo').lower()
    if kind == 'photo':
        payload = result.get('photo')
        if isinstance(payload, list):
            if payload:
                return str(payload[-1].get('file_id') or '')
            return ''
        if isinstance(payload, dict):
            return str(payload.get('file_id') or '')
        return ''
    for key in ('video', 'voice', 'document', 'audio'):
        payload = result.get(key)
        if isinstance(payload, dict):
            fid = str(payload.get('file_id') or '')
            if fid:
                return fid
    return ''


def _node_type_to_media_kind(node_type: str) -> str:
    mapping = {
        'image': FlowMedia.MediaKind.PHOTO,
        'video': FlowMedia.MediaKind.VIDEO,
        'voice': FlowMedia.MediaKind.VOICE,
        'document': FlowMedia.MediaKind.DOCUMENT,
    }
    return mapping.get(str(node_type or '').lower(), FlowMedia.MediaKind.PHOTO)


def _send_flow_media_upload(
    cfg: BotSettings,
    media: FlowMedia,
    chat_id: int,
    *,
    caption: str = '',
) -> dict[str, Any]:
    """آپلود فایل FlowMedia به پیام‌رسان (بدون وابستگی به مسیر محلی روی دیسک)."""
    if not media.file or not media.file.name:
        raise messenger_api.MessengerAPIError('فایل رسانه در سرور یافت نشد.')
    fname = Path(media.file.name).name
    with media.file.open('rb') as f:
        kind = str(media.media_kind or FlowMedia.MediaKind.PHOTO).lower()
        if kind == FlowMedia.MediaKind.VIDEO:
            return messenger_api.send_video(
                cfg.platform,
                chat_id,
                settings=cfg,
                video_file=f,
                video_filename=fname,
                caption=caption,
            )
        if kind == FlowMedia.MediaKind.VOICE:
            return messenger_api.send_voice(
                cfg.platform,
                chat_id,
                settings=cfg,
                voice_file=f,
                voice_filename=fname,
                caption=caption,
            )
        if kind == FlowMedia.MediaKind.DOCUMENT:
            return messenger_api.send_document(
                cfg.platform,
                chat_id,
                settings=cfg,
                document_file=f,
                document_filename=fname,
                caption=caption,
            )
        return messenger_api.send_photo(
            cfg.platform,
            chat_id,
            settings=cfg,
            photo_file=f,
            photo_filename=fname,
            caption=caption,
        )


def _store_messenger_file_id(media: FlowMedia, resp: dict[str, Any]) -> None:
    fid = _extract_messenger_file_id(resp, media.media_kind)
    if fid and fid != media.messenger_file_id:
        media.messenger_file_id = fid[:512]
        media.save(update_fields=['messenger_file_id'])


def _send_media_with_file_id(
    cfg: BotSettings,
    chat_id: int,
    media: FlowMedia,
    *,
    caption: str = '',
) -> None:
    platform = cfg.platform
    fid = media.messenger_file_id
    kind = str(media.media_kind or FlowMedia.MediaKind.PHOTO).lower()
    if kind == FlowMedia.MediaKind.VIDEO:
        messenger_api.send_video(
            platform, chat_id, settings=cfg, video_file_id=fid, caption=caption,
        )
    elif kind == FlowMedia.MediaKind.VOICE:
        messenger_api.send_voice(
            platform, chat_id, settings=cfg, voice_file_id=fid, caption=caption,
        )
    elif kind == FlowMedia.MediaKind.DOCUMENT:
        messenger_api.send_document(
            platform, chat_id, settings=cfg, document_file_id=fid, caption=caption,
        )
    else:
        messenger_api.send_photo(
            platform, chat_id, settings=cfg, photo_file_id=fid, caption=caption,
        )


def send_media_node(cfg: BotSettings, chat_id: int, node: dict[str, Any]) -> bool:
    platform = cfg.platform
    node_type = str(node.get('type', '') or '').lower()
    if node_type not in ('image', 'video', 'voice', 'document'):
        return False
    media_id = str(node.get('media_id', '') or '').strip()
    caption = (node.get('caption') or '').strip()[:1024]
    if not media_id:
        return False
    expected_kind = _node_type_to_media_kind(node_type)
    media = FlowMedia.objects.filter(
        pk=media_id,
        platform=platform,
        workspace=cfg.workspace,
    ).first()
    if not media or not media.file or not media.file.name:
        return False
    if media.media_kind != expected_kind:
        media.media_kind = expected_kind
        media.messenger_file_id = ''
        media.save(update_fields=['media_kind', 'messenger_file_id'])

    if media.messenger_file_id:
        try:
            _send_media_with_file_id(cfg, chat_id, media, caption=caption)
            return True
        except messenger_api.MessengerAPIError:
            media.messenger_file_id = ''
            media.save(update_fields=['messenger_file_id'])

    try:
        resp = _send_flow_media_upload(cfg, media, chat_id, caption=caption)
        _store_messenger_file_id(media, resp)
        return True
    except messenger_api.MessengerAPIError:
        return False


def send_image_node(cfg: BotSettings, chat_id: int, node: dict[str, Any]) -> bool:
    return send_media_node(cfg, chat_id, node)


def _append_markup_rows(
    merged_rows: list[list[dict[str, Any]]],
    markup: dict[str, Any] | None,
) -> None:
    if not markup:
        return
    for row in markup.get('inline_keyboard') or []:
        if row:
            merged_rows.append(row)


def build_root_flow_markup(cfg: BotSettings) -> dict[str, Any] | None:
    """ردیف‌های دکمهٔ جریان /start بدون ارسال."""
    flow = get_flow(cfg)
    root = flow.get('root') or {}
    if str(root.get('type', '')).lower() != 'sequence':
        return None
    merged_rows: list[list[dict[str, Any]]] = []
    for item in root.get('items') or []:
        if not isinstance(item, dict):
            continue
        if str(item.get('type', '')).lower() == 'buttons':
            _append_markup_rows(
                merged_rows,
                build_markup_for_buttons_node(item, cfg=cfg),
            )
    if not merged_rows:
        return None
    return {'inline_keyboard': merged_rows}


def _send_message_with_inline_markup(
    cfg: BotSettings,
    chat_id: int,
    text: str,
    markup: dict[str, Any],
) -> bool:
    """ارسال متن همراه کیبورد؛ True اگر reply_markup با موفقیت پیوست شد."""
    platform = cfg.platform
    body = (text or '').strip()
    if not body:
        return False
    for candidate in (markup, _strip_url_buttons_from_markup(markup)):
        if not candidate:
            continue
        try:
            messenger_api.send_message(
                platform,
                chat_id,
                body[:4096],
                settings=cfg,
                reply_markup=candidate,
            )
            return True
        except messenger_api.MessengerAPIError:
            continue
    try:
        messenger_api.send_message(platform, chat_id, body[:4096], settings=cfg)
    except messenger_api.MessengerAPIError:
        pass
    return False


def _collect_consecutive_buttons_markup(
    items: list[Any],
    start_idx: int,
    cfg: BotSettings,
) -> tuple[dict[str, Any] | None, int]:
    """Markup from one or more consecutive buttons items; returns (markup, index after last buttons)."""
    merged_rows: list[list[dict[str, Any]]] = []
    j = start_idx
    while j < len(items):
        item = items[j]
        if not isinstance(item, dict):
            break
        if str(item.get('type', '')).lower() != 'buttons':
            break
        _append_markup_rows(
            merged_rows,
            build_markup_for_buttons_node(item, cfg=cfg),
        )
        j += 1
    if not merged_rows:
        return None, start_idx
    return {'inline_keyboard': merged_rows}, j


def send_sequence_items(
    cfg: BotSettings,
    chat_id: int,
    sequence: dict[str, Any],
    *,
    sub: Subscriber | None = None,
    merge_button_markup: bool = False,
    pending_markup: dict[str, Any] | None = None,
    attach_markup_to: str = 'first',
) -> dict[str, Any] | None:
    """ارسال آیتم‌های sequence به ترتیب؛ دکمه‌ها به متن بلافاصله قبل از خود می‌چسبند."""
    platform = cfg.platform
    items = sequence.get('items') or []

    i = 0
    while i < len(items):
        item = items[i]
        if not isinstance(item, dict):
            i += 1
            continue
        itype = str(item.get('type', '')).lower()

        if itype == 'text':
            body = (item.get('body') or '').strip()
            if not body:
                i += 1
                continue
            reply_markup = pending_markup
            next_i = i + 1
            pending_markup = None
            if reply_markup is None and merge_button_markup:
                mk, after_buttons = _collect_consecutive_buttons_markup(items, i + 1, cfg)
                if mk:
                    reply_markup = mk
                    next_i = after_buttons

            if reply_markup:
                if not _send_message_with_inline_markup(cfg, chat_id, body, reply_markup):
                    try:
                        messenger_api.send_message(
                            platform,
                            chat_id,
                            body[:4096],
                            settings=cfg,
                        )
                    except messenger_api.MessengerAPIError:
                        pass
            else:
                try:
                    messenger_api.send_message(
                        platform,
                        chat_id,
                        body[:4096],
                        settings=cfg,
                    )
                except messenger_api.MessengerAPIError:
                    pass
            i = next_i
            continue

        if itype == 'buttons':
            if merge_button_markup:
                mk = build_markup_for_buttons_node(item, cfg=cfg)
                if mk:
                    _send_inline_keyboard_message(cfg, chat_id, mk)
            i += 1
            continue

        if itype in ('image', 'video', 'voice', 'document'):
            send_media_node(cfg, chat_id, item)
        elif itype in _INTERACTIVE_ACTION_TYPES and sub is not None:
            from balebot.services.flow_interactive import _execute_node

            _execute_node(cfg, sub, chat_id, item)
        i += 1

    return pending_markup


def _send_inline_keyboard_message(
    cfg: BotSettings,
    chat_id: int,
    markup: dict[str, Any],
) -> bool:
    """پیام حامل دکمه‌های inline."""
    platform = cfg.platform
    candidates = [markup]
    stripped = _strip_url_buttons_from_markup(markup)
    if stripped and stripped != markup:
        candidates.append(stripped)

    for candidate in candidates:
        for anchor in ('.', '·', ' '):
            try:
                messenger_api.send_message(
                    platform,
                    chat_id,
                    anchor,
                    settings=cfg,
                    reply_markup=candidate,
                )
                return True
            except messenger_api.MessengerAPIError as exc:
                logger.warning(
                    'ارسال پیام دکمه‌های inline ناموفق (anchor=%r): %s',
                    anchor,
                    exc,
                )
    return False


def send_sequence(
    cfg: BotSettings,
    chat_id: int,
    sequence: dict[str, Any],
    *,
    sub: Subscriber | None = None,
    markup_already_sent: bool = False,
) -> dict[str, Any] | None:
    """ارسال آیتم‌های sequence؛ دکمه‌ها به اولین بلوک متن می‌چسبند."""
    return send_sequence_items(
        cfg,
        chat_id,
        sequence,
        sub=sub,
        merge_button_markup=not markup_already_sent,
        attach_markup_to='first',
    )


def render_root_flow(
    cfg: BotSettings,
    chat_id: int,
    *,
    sub: Subscriber | None = None,
    markup_already_sent: bool = False,
) -> None:
    flow = get_flow(cfg)
    root = flow.get('root') or {}
    if str(root.get('type', '')).lower() != 'sequence':
        return
    markup = send_sequence(cfg, chat_id, root, sub=sub, markup_already_sent=markup_already_sent)
    if markup and not markup_already_sent:
        markup = merge_support_into_markup(cfg, markup) or markup
        _send_inline_keyboard_message(cfg, chat_id, markup)
    elif not markup_already_sent and cfg.enable_support:
        mk = merge_support_into_markup(cfg, None)
        if mk:
            _send_inline_keyboard_message(cfg, chat_id, mk)


def send_default_text(cfg: BotSettings, chat_id: int) -> None:
    platform = cfg.platform
    txt = (cfg.start_flow_default_text or '').strip()
    if txt:
        try:
            messenger_api.send_message(platform, chat_id, txt[:4096], settings=cfg)
        except messenger_api.MessengerAPIError:
            pass


def resume_flow(cfg: BotSettings, sub: Subscriber, msg: dict[str, Any], state: dict[str, Any]) -> bool:
    from balebot.services.flow_interactive import resume_flow as _resume
    return _resume(cfg, sub, msg, state)


def execute_button_action(
    cfg: BotSettings,
    ref: _ButtonRef,
    chat_id: int,
    *,
    sub: Subscriber | None = None,
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
                messenger_api.send_message(platform, chat_id, body[:4096], settings=cfg)
            except messenger_api.MessengerAPIError:
                pass
        else:
            send_default_text(cfg, chat_id)
        return 'text'

    if atype == 'image':
        if not send_media_node(cfg, chat_id, action):
            send_default_text(cfg, chat_id)
            return 'image_failed'
        return 'image'

    if atype == 'sequence':
        send_sequence_items(cfg, chat_id, action, sub=sub, merge_button_markup=False)
        return 'sequence'

    if atype == 'url':
        return atype

    if atype == 'buttons':
        mk = build_markup_for_buttons_node(action, parent_button_id=btn_id, cfg=cfg)
        if mk and message_id:
            try:
                messenger_api.edit_message_reply_markup(
                    platform, chat_id, int(message_id), settings=cfg, reply_markup=mk,
                )
                return 'buttons_edit'
            except messenger_api.MessengerAPIError:
                pass
        if mk:
            _send_inline_keyboard_message(cfg, chat_id, mk)
            return 'buttons'
        send_default_text(cfg, chat_id)
        return 'default'

    if atype in _INTERACTIVE_ACTION_TYPES and sub is not None:
        from balebot.services.flow_interactive import execute_interactive_action
        return execute_interactive_action(
            cfg, sub, ref, chat_id, message_id=message_id, visited=visited,
        )

    send_default_text(cfg, chat_id)
    return 'default'


def handle_flow_callback(
    cfg: BotSettings,
    sub: Subscriber,
    data: str,
    chat_id: int,
    message_id: int | None,
) -> tuple[str, str]:
    """پردازش f* / fb* / fr*؛ برمی‌گرداند (flow_kind, flow_label)."""
    from balebot.services.flow_interactive import (
        handle_faq_answer_callback,
        handle_join_gate_recheck,
        parse_flow_recheck_callback,
    )

    recheck_id = parse_flow_recheck_callback(data)
    if recheck_id:
        return handle_join_gate_recheck(cfg, sub, recheck_id, chat_id)

    back_id = parse_flow_back_callback(data)
    if back_id:
        ref = find_button_by_id(cfg, back_id)
        if ref is None:
            render_root_flow(cfg, chat_id, sub=sub)
            return 'back_root', ''
        parent = ref.ancestors[-1] if ref.ancestors else None
        if parent:
            pact = parent.get('action')
            if isinstance(pact, dict) and str(pact.get('type', '')).lower() == 'buttons':
                mk = build_markup_for_buttons_node(
                    pact,
                    parent_button_id=str(parent.get('id') or '') or None,
                    cfg=cfg,
                )
                if mk and message_id:
                    try:
                        messenger_api.edit_message_reply_markup(
                            cfg.platform, chat_id, int(message_id), settings=cfg, reply_markup=mk,
                        )
                    except messenger_api.MessengerAPIError:
                        pass
                return 'back', str(parent.get('text') or '')[:128]
        render_root_flow(cfg, chat_id, sub=sub)
        return 'back_root', ''

    node_id = parse_flow_callback(data)
    if not node_id:
        return 'invalid', ''

    state = sub.flow_state or {}
    faq_map = state.get('faq_answers') or {}
    if node_id in faq_map:
        if handle_faq_answer_callback(cfg, sub, node_id, chat_id):
            return 'faq_answer', ''

    ref = find_button_by_id(cfg, node_id)
    if ref is None:
        send_default_text(cfg, chat_id)
        return 'unknown_button', ''

    slugs = category_slugs_for_button(ref)
    if slugs:
        try:
            assign_path_tags(sub, slugs, ref)
        except IntegrityError:
            logger.exception(
                'assign_path_tags failed for subscriber=%s slugs=%s',
                sub.pk,
                slugs,
            )

    if len(slugs) > _MAX_LOOP_VISITS:
        send_default_text(cfg, chat_id)
        return 'loop_default', str(ref.button.get('text') or '')[:128]

    kind = execute_button_action(
        cfg, ref, chat_id, sub=sub, message_id=message_id, visited=set(),
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
