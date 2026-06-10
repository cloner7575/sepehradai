"""موتور جریان /start: رندر، callback، لیبل درختی."""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

from django.db import IntegrityError

from balebot.models import BotSettings, FlowMedia, Platform, Subscriber, SubscriberTag, Tag
from balebot.services import messenger_api
from balebot.services.flow_sanitize import empty_start_flow, sanitize_start_flow

logger = logging.getLogger(__name__)

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
    base_name = (display_hint or slug).strip()[:120] or slug
    name = base_name

    # نام تگ روی (platform, name) یکتا است؛ اگر label تکراری باشد،
    # نام کاندید را با slug متمایز می‌کنیم تا خطای unique رخ ندهد.
    existing_same_name = Tag.objects.filter(platform=platform, name=name).exclude(slug=slug).exists()
    if existing_same_name:
        suffix = f' - {slug}'
        max_base = max(1, 120 - len(suffix))
        name = f'{base_name[:max_base]}{suffix}'[:120]

    for i in range(3):
        try:
            return Tag.objects.create(
                name=name,
                slug=slug,
                platform=platform,
                tag_type=Tag.TagType.GENERIC,
                is_active=True,
            )
        except IntegrityError:
            # اگر در همین لحظه توسط یک درخواست دیگر ساخته شده باشد.
            tag = Tag.objects.filter(platform=platform, slug=slug).first()
            if tag:
                return tag

            # در برخورد روی name، suffix پایدار اضافه می‌کنیم.
            name = f'{base_name[:112]}-{i + 2}'[:120]

    # fallback نهایی: اگر هنوز نساخته‌ایم، احتمالاً slug همزمان ساخته شده است.
    tag = Tag.objects.filter(platform=platform, slug=slug).first()
    if tag:
        return tag
    raise IntegrityError('Could not create tag without violating unique constraints')


def assign_path_tags(sub: Subscriber, slugs: list[str], ref: _ButtonRef) -> None:
    hint = str(ref.button.get('text') or '')
    for slug in slugs:
        tag = get_or_create_tag_for_slug(slug, sub.platform, hint)
        SubscriberTag.objects.get_or_create(subscriber=sub, tag=tag)


def resolve_web_app_url(raw: str, cfg: BotSettings | None = None) -> str:
    """آدرس مینی‌اپ را برای WebAppInfo نرمال می‌کند (HTTPS الزامی است)."""
    url = (raw or '').strip()
    if not url:
        return ''
    if url.startswith('/'):
        if cfg is None:
            return ''
        base = (cfg.webhook_public_url or '').strip().rstrip('/')
        if not base:
            return ''
        url = f'{base}{url}'
    if url.startswith('http://'):
        url = f'https://{url[7:]}'
    elif not url.startswith('https://'):
        url = f'https://{url.lstrip("/")}'
    return url[:512]


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
            action = btn.get('action')
            if isinstance(action, dict):
                atype = str(action.get('type', '')).lower()
                if atype == 'url':
                    url = (action.get('url') or '').strip()
                    if url:
                        out_row.append({'text': text, 'url': url[:512]})
                    continue
                if atype == 'web_app':
                    url = resolve_web_app_url(action.get('url') or '', cfg)
                    if url:
                        out_row.append({'text': text, 'web_app': {'url': url}})
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


def send_sequence_items(
    cfg: BotSettings,
    chat_id: int,
    sequence: dict[str, Any],
    *,
    merge_button_markup: bool = False,
) -> dict[str, Any] | None:
    """ارسال آیتم‌های sequence؛ در صورت merge_button_markup ردیف‌های دکمه ادغام می‌شوند."""
    platform = cfg.platform
    items = sequence.get('items') or []
    merged_rows: list[list[dict[str, Any]]] = []

    if merge_button_markup:
        for item in items:
            if not isinstance(item, dict):
                continue
            if str(item.get('type', '')).lower() == 'buttons':
                _append_markup_rows(
                    merged_rows,
                    build_markup_for_buttons_node(item, cfg=cfg),
                )

    pending_markup: dict[str, Any] | None = None
    if merge_button_markup and merged_rows:
        pending_markup = {'inline_keyboard': merged_rows}

    last_text_idx = -1
    for idx, item in enumerate(items):
        if not isinstance(item, dict):
            continue
        if str(item.get('type', '')).lower() == 'text' and (item.get('body') or '').strip():
            last_text_idx = idx

    for idx, item in enumerate(items):
        if not isinstance(item, dict):
            continue
        itype = str(item.get('type', '')).lower()
        if itype == 'text':
            body = (item.get('body') or '').strip()
            if not body:
                continue
            reply_markup = pending_markup if merge_button_markup and idx == last_text_idx else None
            try:
                messenger_api.send_message(
                    platform,
                    chat_id,
                    body[:4096],
                    settings=cfg,
                    reply_markup=reply_markup,
                )
            except messenger_api.MessengerAPIError:
                if reply_markup:
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
                if reply_markup:
                    pending_markup = None
        elif itype in ('image', 'video', 'voice', 'document'):
            send_media_node(cfg, chat_id, item)

    return pending_markup


def _send_inline_keyboard_message(
    cfg: BotSettings,
    chat_id: int,
    markup: dict[str, Any],
) -> bool:
    """پیام حامل دکمه‌های inline؛ متن باید برای API بله قابل‌قبول باشد."""
    platform = cfg.platform
    for anchor in ('.', '·', ' '):
        try:
            messenger_api.send_message(
                platform,
                chat_id,
                anchor,
                settings=cfg,
                reply_markup=markup,
            )
            return True
        except messenger_api.MessengerAPIError as exc:
            logger.warning(
                'ارسال پیام دکمه‌های inline ناموفق (anchor=%r): %s',
                anchor,
                exc,
            )
    return False


def send_sequence(cfg: BotSettings, chat_id: int, sequence: dict[str, Any]) -> dict[str, Any] | None:
    """ارسال آیتم‌های sequence؛ ردیف‌های همهٔ بلوک‌های دکمه را ادغام و برمی‌گرداند."""
    return send_sequence_items(cfg, chat_id, sequence, merge_button_markup=True)


def render_root_flow(cfg: BotSettings, chat_id: int) -> None:
    flow = get_flow(cfg)
    root = flow.get('root') or {}
    if str(root.get('type', '')).lower() != 'sequence':
        return
    markup = send_sequence(cfg, chat_id, root)
    if markup:
        markup = merge_support_into_markup(cfg, markup) or markup
        _send_inline_keyboard_message(cfg, chat_id, markup)
    elif cfg.enable_support:
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
        send_sequence_items(cfg, chat_id, action, merge_button_markup=False)
        return 'sequence'

    if atype in ('url', 'web_app'):
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
