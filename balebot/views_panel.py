import uuid
from pathlib import Path
import tempfile

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.files.storage import default_storage
from django.db.models import Count, Q
from django.http import HttpResponseRedirect, JsonResponse
from django.urls import reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import DetailView, ListView, TemplateView
from django.views.generic.edit import CreateView, UpdateView

from balebot.forms import BotSettingsForm, CampaignForm
from balebot.platform import (
    all_platforms,
    get_active_platform,
    get_bot_settings_for_request,
    platform_label,
    require_workspace_for_request,
    set_active_platform,
)
from balebot.workspace import user_has_panel_access
from balebot.services import messenger_api
from balebot.services.webhook_setup import (
    explain_telegram_webhook_error,
    normalize_public_url,
    validate_webhook_url,
)
from balebot.services.audience import snapshot_campaign_audience
from balebot.services.campaign_runner import run_single_campaign_web
from balebot.services.keyboard_layout import keyboard_has_any_button, normalize_to_sections
from balebot.models import (
    BotSettings,
    CallbackLog,
    Campaign,
    CampaignDelivery,
    FlowMedia,
    InboundMessage,
    Platform,
    Subscriber,
    SupportTicketMessage,
    Tag,
)

CAMPAIGN_PENDING_MEDIA_SESSION_KEY = 'campaign_pending_media'

CAMPAIGN_VIDEO_UPLOAD_EXTENSIONS = frozenset(
    {'.mp4', '.webm', '.mov', '.mkv', '.mpeg', '.mpg', '.m4v', '.avi'},
)


def campaign_form_media_context(request, campaign_obj=None):
    """متغیرهای مشترک قالب فرم کمپین (آپلود ویدیو)."""
    pending_key = CAMPAIGN_PENDING_MEDIA_SESSION_KEY
    ctx = {
        'CAMPAIGN_VIDEO_MAX_UPLOAD_MB': getattr(settings, 'CAMPAIGN_VIDEO_MAX_UPLOAD_MB', 120),
        'campaign_pending_video_ready': bool(request.session.get(pending_key)),
        'campaign_media_campaign_pk': ''
        if not (campaign_obj and getattr(campaign_obj, 'pk', None))
        else str(campaign_obj.pk),
        'campaign_has_saved_media': False,
        'campaign_saved_media_url': '',
    }
    if campaign_obj and getattr(campaign_obj, 'pk', None):
        media_f = getattr(campaign_obj, 'media', None)
        name = getattr(media_f, 'name', '') if media_f else ''
        if name:
            ctx['campaign_has_saved_media'] = True
            ctx['campaign_saved_media_url'] = media_f.url
    return ctx


class PanelAccessMixin(LoginRequiredMixin, UserPassesTestMixin):
    """دسترسی پنل: staff با workspace فعال یا سوپرادمین."""

    def test_func(self):
        return user_has_panel_access(self.request.user)


class WorkspaceScopedMixin:
    """فیلتر داده‌ها بر اساس workspace و پلتفرم فعال."""

    def get_workspace(self):
        return require_workspace_for_request(self.request)

    def get_active_platform(self) -> str:
        return get_active_platform(self.request)

    def scope_filter(self) -> dict:
        return {'workspace': self.get_workspace(), 'platform': self.get_active_platform()}

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['active_platform'] = self.get_active_platform()
        ctx['active_platform_label'] = platform_label(ctx['active_platform'])
        ctx['available_platforms'] = all_platforms()
        ctx['panel_workspace'] = self.get_workspace()
        return ctx


class SwitchPlatformView(PanelAccessMixin, View):
    http_method_names = ['get', 'post']

    def get(self, request, *args, **kwargs):
        return HttpResponseRedirect(request.META.get('HTTP_REFERER') or '/')

    def post(self, request, *args, **kwargs):
        platform = (request.POST.get('platform') or '').strip()
        set_active_platform(request, platform)
        next_url = request.POST.get('next') or request.META.get('HTTP_REFERER') or '/'
        return HttpResponseRedirect(next_url)


class DashboardView(WorkspaceScopedMixin, PanelAccessMixin, TemplateView):
    template_name = 'balebot/dashboard.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        scope = self.scope_filter()
        ctx['subscriber_active'] = Subscriber.objects.filter(
            **scope, is_active=True, is_registered=True,
        ).count()
        ctx['subscriber_total'] = Subscriber.objects.filter(**scope).count()
        ctx['campaign_recent'] = Campaign.objects.filter(**scope).order_by('-created_at')[:8]
        sent = CampaignDelivery.objects.filter(
            campaign__workspace=scope['workspace'],
            campaign__platform=scope['platform'],
            status=CampaignDelivery.DeliveryStatus.SENT,
        ).count()
        failed = CampaignDelivery.objects.filter(
            campaign__workspace=scope['workspace'],
            campaign__platform=scope['platform'],
            status=CampaignDelivery.DeliveryStatus.FAILED,
        ).count()
        ctx['delivery_sent'] = sent
        ctx['delivery_failed'] = failed
        ctx['inbound_recent'] = (
            InboundMessage.objects.filter(
                subscriber__workspace=scope['workspace'],
                subscriber__platform=scope['platform'],
            )
            .select_related('subscriber')
            .order_by('-created_at')[:15]
        )
        ctx['campaign_total'] = Campaign.objects.filter(**scope).count()
        ctx['campaign_running'] = Campaign.objects.filter(
            **scope,
            status__in=(Campaign.Status.QUEUED, Campaign.Status.SENDING),
        ).count()
        ctx['callback_recent_count'] = CallbackLog.objects.filter(
            subscriber__workspace=scope['workspace'],
            subscriber__platform=scope['platform'],
        ).count()
        return ctx


class BotSettingsView(WorkspaceScopedMixin, PanelAccessMixin, UpdateView):
    model = BotSettings
    form_class = BotSettingsForm
    template_name = 'balebot/bot_settings.html'

    def get_object(self, queryset=None):
        return get_bot_settings_for_request(self.request)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        obj = self.object
        ctx['webhook_url_preview'] = obj.build_webhook_url() if obj else ''
        ctx['connection_status'] = self._connection_status(obj)
        return ctx

    def _connection_status(self, obj: BotSettings) -> dict:
        status = {
            'has_token': obj.has_bot_token(),
            'webhook_ok': False,
            'bot_ok': False,
            'webhook_url': '',
            'bot_username': '',
            'error': '',
        }
        if not status['has_token']:
            return status
        try:
            me = messenger_api.get_me(obj.platform, settings=obj)
            result = me.get('result') or {}
            status['bot_ok'] = True
            status['bot_username'] = result.get('username') or ''
        except messenger_api.MessengerAPIError as e:
            status['error'] = str(e)
            return status
        try:
            info = messenger_api.get_webhook_info(obj.platform, settings=obj)
            result = info.get('result') or {}
            expected = obj.build_webhook_url()
            actual = (result.get('url') or '').strip()
            status['webhook_url'] = actual
            status['webhook_ok'] = bool(expected and actual == expected)
        except messenger_api.MessengerAPIError as e:
            status['error'] = str(e)
        return status

    def post(self, request, *args, **kwargs):
        action = (request.POST.get('action') or '').strip()
        if action == 'register_webhook':
            return self._register_webhook(request)
        return super().post(request, *args, **kwargs)

    def _register_webhook(self, request):
        obj = self.get_object()
        posted_url = (request.POST.get('webhook_public_url') or '').strip()
        posted_secret = (request.POST.get('webhook_secret') or '').strip()
        update_fields = ['updated_at']
        if posted_url:
            obj.webhook_public_url = normalize_public_url(posted_url, platform=obj.platform)
            update_fields.append('webhook_public_url')
        if posted_secret:
            obj.webhook_secret = posted_secret
            update_fields.append('webhook_secret')
        if len(update_fields) > 1:
            obj.save(update_fields=update_fields)

        url = obj.build_webhook_url()
        if not obj.has_bot_token():
            messages.error(request, 'ابتدا توکن ربات را ذخیره کنید.')
            return HttpResponseRedirect(reverse_lazy('bot_settings'))
        if not url:
            messages.error(request, 'آدرس عمومی سرور و رمز وب‌هوک را پر کنید.')
            return HttpResponseRedirect(reverse_lazy('bot_settings'))

        ok, err = validate_webhook_url(url, platform=obj.platform)
        if not ok:
            messages.error(request, err)
            return HttpResponseRedirect(reverse_lazy('bot_settings'))

        try:
            messenger_api.set_webhook(obj.platform, url, settings=obj)
            messages.success(request, f'وب‌هوک ثبت شد: {url}')
        except messenger_api.MessengerAPIError as e:
            detail = explain_telegram_webhook_error(str(e)) if obj.platform == Platform.TELEGRAM else str(e)
            messages.error(request, f'ثبت وب‌هوک ناموفق: {detail}')
        return HttpResponseRedirect(reverse_lazy('bot_settings'))

    def get_success_url(self):
        return reverse_lazy('bot_settings')

    def form_valid(self, form):
        messages.success(
            self.request,
            'تنظیمات بازو ذخیره شد و از طریق وب‌هوک برای پیام‌های بعدی اعمال می‌شود.',
        )
        return super().form_valid(form)


class SubscriberListView(WorkspaceScopedMixin, PanelAccessMixin, ListView):
    model = Subscriber
    template_name = 'balebot/subscriber_list.html'
    paginate_by = 40

    def get_queryset(self):
        qs = Subscriber.objects.filter(**self.scope_filter()).annotate(
            unread_support_count=Count(
                'inbound_messages',
                filter=Q(
                    inbound_messages__is_support_request=True,
                    inbound_messages__is_support_read=False,
                ),
            ),
        ).order_by('-updated_at')
        q = self.request.GET.get('q', '').strip()
        if q:
            cond = (
                Q(phone_number__icontains=q)
                | Q(first_name__icontains=q)
                | Q(username__icontains=q)
            )
            if q.isdigit():
                n = int(q)
                cond |= Q(messenger_user_id=n) | Q(chat_id=n)
            qs = qs.filter(cond)
        tag_raw = (self.request.GET.get('tag') or '').strip()
        if tag_raw.isdigit():
            qs = qs.filter(tags__id=int(tag_raw)).distinct()
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['available_tags'] = Tag.objects.filter(
            **self.scope_filter(), is_active=True,
        ).order_by('name')
        ctx['selected_tag_id'] = (self.request.GET.get('tag') or '').strip()
        return ctx


class SubscriberDetailView(WorkspaceScopedMixin, PanelAccessMixin, DetailView):
    model = Subscriber
    template_name = 'balebot/subscriber_detail.html'

    def get_queryset(self):
        return Subscriber.objects.filter(**self.scope_filter())

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        selected_filter = (self.request.GET.get('kind') or 'support').strip().lower()
        if selected_filter not in {'support', 'normal', 'all'}:
            selected_filter = 'support'

        base_qs = InboundMessage.objects.filter(subscriber=self.object)
        support_qs = base_qs.filter(is_support_request=True)
        if selected_filter == 'support':
            filtered_qs = support_qs
        elif selected_filter == 'normal':
            filtered_qs = base_qs.filter(is_support_request=False)
        else:
            filtered_qs = base_qs

        if selected_filter in {'support', 'all'}:
            support_qs.filter(is_support_read=False).update(is_support_read=True)
            self._sync_support_inbound_into_ticket(support_qs)

        ctx['inbound_messages'] = filtered_qs.order_by('-created_at')[:200]
        user_tickets = list(
            SupportTicketMessage.objects.filter(
                subscriber=self.object,
                sender=SupportTicketMessage.Sender.USER,
            ).order_by('-created_at')[:120]
        )
        ticket_ids = [row.id for row in user_tickets]
        reply_counts = {}
        if ticket_ids:
            grouped = (
                SupportTicketMessage.objects.filter(
                    subscriber=self.object,
                    sender=SupportTicketMessage.Sender.ADMIN,
                    parent_user_message_id__in=ticket_ids,
                )
                .values('parent_user_message_id')
                .annotate(c=Count('id'))
            )
            reply_counts = {int(row['parent_user_message_id']): int(row['c']) for row in grouped}
        selected_ticket_id_raw = (self.request.GET.get('ticket') or '').strip()
        selected_ticket_id = int(selected_ticket_id_raw) if selected_ticket_id_raw.isdigit() else None
        selected_ticket = None
        if selected_ticket_id:
            selected_ticket = next((row for row in user_tickets if row.id == selected_ticket_id), None)
        if selected_ticket is None and user_tickets:
            selected_ticket = user_tickets[0]

        chat_messages = []
        if selected_ticket is not None:
            chat_messages = [selected_ticket] + list(
                SupportTicketMessage.objects.filter(
                    subscriber=self.object,
                    sender=SupportTicketMessage.Sender.ADMIN,
                    parent_user_message=selected_ticket,
                ).order_by('created_at')[:200]
            )
            inbound = selected_ticket.inbound_message
            if inbound and inbound.is_support_request and not inbound.is_support_read:
                inbound.is_support_read = True
                inbound.save(update_fields=['is_support_read'])

        ctx['ticket_list'] = user_tickets
        ctx['ticket_reply_counts'] = reply_counts
        ctx['selected_ticket'] = selected_ticket
        ctx['ticket_chat_messages'] = chat_messages
        ctx['normal_outbound_messages'] = SupportTicketMessage.objects.filter(
            subscriber=self.object,
            sender=SupportTicketMessage.Sender.ADMIN,
            parent_user_message__isnull=True,
        ).order_by('-created_at')[:120]
        ctx['support_messages_count'] = support_qs.count()
        ctx['normal_messages_count'] = base_qs.filter(is_support_request=False).count()
        ctx['all_messages_count'] = base_qs.count()
        ctx['message_kind'] = selected_filter
        return ctx

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        action = (request.POST.get('action') or '').strip()
        msg = (request.POST.get('personal_message') or '').strip()
        media = request.FILES.get('personal_media')
        if not msg and not media:
            messages.error(request, 'برای ارسال، متن پیام یا فایل مدیا را وارد کنید.')
            return HttpResponseRedirect(self.request.path)

        try:
            platform = self.object.platform
            bot_settings = BotSettings.get_for_platform(self.object.workspace, platform)
            if media:
                kind, text_body, file_id = self._send_personal_media(
                    platform, media, msg, bot_settings,
                )
            else:
                messenger_api.send_message(
                    platform, self.object.chat_id, msg[:4096], settings=bot_settings,
                )
                kind = SupportTicketMessage.MessageKind.TEXT
                text_body = msg[:4096]
                file_id = ''
        except messenger_api.MessengerAPIError as e:
            messages.error(request, f'ارسال پیام ناموفق بود: {e}')
            return HttpResponseRedirect(self.request.path)

        parent_user_message = None
        redirect_url = self.request.path
        if action == 'reply_ticket':
            ticket_raw = (request.POST.get('ticket_id') or '').strip()
            if not ticket_raw.isdigit():
                messages.error(request, 'تیکت انتخاب‌شده نامعتبر است.')
                return HttpResponseRedirect(self.request.path)
            parent_user_message = SupportTicketMessage.objects.filter(
                id=int(ticket_raw),
                subscriber=self.object,
                sender=SupportTicketMessage.Sender.USER,
            ).first()
            if parent_user_message is None:
                messages.error(request, 'تیکت انتخاب‌شده پیدا نشد.')
                return HttpResponseRedirect(self.request.path)
            redirect_url = f'{self.request.path}?ticket={parent_user_message.id}'

        SupportTicketMessage.objects.create(
            subscriber=self.object,
            sender=SupportTicketMessage.Sender.ADMIN,
            kind=kind,
            text=text_body,
            file_id=file_id,
            parent_user_message=parent_user_message,
        )
        if action == 'reply_ticket':
            messages.success(request, 'پاسخ تیکت با موفقیت ارسال شد.')
        else:
            messages.success(request, 'پیام عادی با موفقیت ارسال شد.')
        return HttpResponseRedirect(redirect_url)

    def _send_personal_media(
        self, platform: str, media, caption_text: str, bot_settings: BotSettings,
    ) -> tuple[str, str, str]:
        suffix = Path(media.name or '').suffix
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix or '.bin') as tmp:
            for chunk in media.chunks():
                tmp.write(chunk)
            temp_path = Path(tmp.name)

        caption = (caption_text or '').strip()[:1024]
        content_type = (getattr(media, 'content_type', '') or '').lower()
        try:
            if content_type.startswith('image/'):
                resp = messenger_api.send_photo(
                    platform,
                    self.object.chat_id,
                    settings=bot_settings,
                    photo_path=temp_path,
                    caption=caption,
                )
                return (
                    SupportTicketMessage.MessageKind.PHOTO,
                    caption,
                    self._extract_file_id(resp, 'photo'),
                )
            if content_type.startswith('video/'):
                resp = messenger_api.send_video(
                    platform,
                    self.object.chat_id,
                    settings=bot_settings,
                    video_path=temp_path,
                    caption=caption,
                )
                return (
                    SupportTicketMessage.MessageKind.VIDEO,
                    caption,
                    self._extract_file_id(resp, 'video'),
                )
            if content_type in {'audio/ogg', 'audio/opus'}:
                resp = messenger_api.send_voice(
                    platform,
                    self.object.chat_id,
                    settings=bot_settings,
                    voice_path=temp_path,
                    caption=caption,
                )
                return (
                    SupportTicketMessage.MessageKind.VOICE,
                    caption,
                    self._extract_file_id(resp, 'voice'),
                )
            resp = messenger_api.send_document(
                platform,
                self.object.chat_id,
                settings=bot_settings,
                document_path=temp_path,
                caption=caption,
            )
            return (
                SupportTicketMessage.MessageKind.DOCUMENT,
                caption,
                self._extract_file_id(resp, 'document'),
            )
        finally:
            try:
                temp_path.unlink(missing_ok=True)
            except OSError:
                pass

    @staticmethod
    def _extract_file_id(api_response: dict, key: str) -> str:
        result = (api_response or {}).get('result') or {}
        payload = result.get(key)
        if isinstance(payload, list):
            last = payload[-1] if payload else {}
            return str((last or {}).get('file_id') or '')
        if isinstance(payload, dict):
            return str(payload.get('file_id') or '')
        return ''

    def _sync_support_inbound_into_ticket(self, support_qs) -> None:
        inbound_ids = set(
            SupportTicketMessage.objects.filter(
                subscriber=self.object,
                sender=SupportTicketMessage.Sender.USER,
                inbound_message__isnull=False,
            ).values_list('inbound_message_id', flat=True)
        )
        missing = support_qs.exclude(id__in=inbound_ids).order_by('created_at')[:300]
        if not missing:
            return
        SupportTicketMessage.objects.bulk_create(
            [
                SupportTicketMessage(
                    subscriber=self.object,
                    sender=SupportTicketMessage.Sender.USER,
                    kind=row.kind,
                    text=row.text,
                    file_id=row.file_id,
                    inbound_message=row,
                    created_at=row.created_at,
                )
                for row in missing
            ]
        )



class CampaignListView(WorkspaceScopedMixin, PanelAccessMixin, ListView):
    model = Campaign
    template_name = 'balebot/campaign_list.html'
    paginate_by = 30

    def get_queryset(self):
        return Campaign.objects.filter(**self.scope_filter()).order_by('-created_at')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        qs = Campaign.objects.filter(**self.scope_filter())
        ctx['campaign_stat_total'] = qs.count()
        ctx['campaign_stat_draft'] = qs.filter(status=Campaign.Status.DRAFT).count()
        ctx['campaign_stat_running'] = qs.filter(
            status__in=(Campaign.Status.QUEUED, Campaign.Status.SENDING),
        ).count()
        ctx['campaign_stat_done'] = qs.filter(status=Campaign.Status.COMPLETED).count()
        return ctx


class CampaignCreateView(WorkspaceScopedMixin, PanelAccessMixin, CreateView):
    model = Campaign
    form_class = CampaignForm
    template_name = 'balebot/campaign_form.html'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        kwargs['platform'] = self.get_active_platform()
        kwargs['workspace'] = self.get_workspace()
        return kwargs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['campaign_keyboard_expanded'] = False
        ctx.update(campaign_form_media_context(self.request, None))
        return ctx

    def form_valid(self, form):
        form.instance.status = Campaign.Status.DRAFT
        form.instance.platform = self.get_active_platform()
        form.instance.workspace = self.get_workspace()
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('campaign_detail', kwargs={'pk': self.object.pk})


class CampaignUpdateView(WorkspaceScopedMixin, PanelAccessMixin, UpdateView):
    model = Campaign
    form_class = CampaignForm
    template_name = 'balebot/campaign_form.html'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        kwargs['platform'] = self.get_active_platform()
        kwargs['workspace'] = self.get_workspace()
        return kwargs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['campaign_keyboard_expanded'] = keyboard_has_any_button(
            normalize_to_sections(self.object.inline_keyboard),
        )
        ctx.update(campaign_form_media_context(self.request, self.object))
        return ctx

    def get_queryset(self):
        return Campaign.objects.filter(**self.scope_filter())

    def get_success_url(self):
        return reverse_lazy('campaign_detail', kwargs={'pk': self.object.pk})


class CampaignMediaUploadView(PanelAccessMixin, View):
    """آپلود جداگانهٔ ویدیو برای کمپین؛ فایل موقت در MEDIA و کلید در سشن."""

    http_method_names = ['post']

    def post(self, request, *args, **kwargs):
        upload = request.FILES.get('file')
        if not upload:
            return JsonResponse({'ok': False, 'error': 'فایلی ارسال نشد.'}, status=400)

        ext = Path(upload.name).suffix.lower()
        if ext not in CAMPAIGN_VIDEO_UPLOAD_EXTENSIONS:
            return JsonResponse(
                {'ok': False, 'error': 'پسوند ویدیو مجاز نیست.'},
                status=400,
            )

        ct = (upload.content_type or '').lower()
        if ct and not ct.startswith('video/') and ct != 'application/octet-stream':
            return JsonResponse(
                {'ok': False, 'error': 'نوع فایل به‌عنوان ویدیو شناخته نشد.'},
                status=400,
            )

        max_bytes = max(1, int(getattr(settings, 'CAMPAIGN_VIDEO_MAX_UPLOAD_MB', 120))) * 1024 * 1024
        if getattr(upload, 'size', 0) and upload.size > max_bytes:
            return JsonResponse(
                {
                    'ok': False,
                    'error': f'حجم فایل از حد مجاز ({settings.CAMPAIGN_VIDEO_MAX_UPLOAD_MB} مگابایت) بیشتر است.',
                },
                status=400,
            )

        uid = uuid.uuid4().hex
        rel_path = f'campaigns/tmp/{uid}{ext}'
        save_name = default_storage.save(rel_path, upload)

        cid_raw = (request.POST.get('campaign_id') or '').strip()
        campaign_id = int(cid_raw) if cid_raw.isdigit() else None

        request.session[CAMPAIGN_PENDING_MEDIA_SESSION_KEY] = {
            'path': save_name,
            'original_name': Path(upload.name).name[:255],
            'size': getattr(upload, 'size', 0),
            'campaign_id': campaign_id,
        }

        return JsonResponse(
            {
                'ok': True,
                'name': Path(upload.name).name,
                'size': getattr(upload, 'size', 0),
            },
        )


class CampaignMediaClearView(PanelAccessMixin, View):
    """حذف آپلود موقت ویدیو از سشن و دیسک."""

    http_method_names = ['post']

    def post(self, request, *args, **kwargs):
        pending = request.session.pop(CAMPAIGN_PENDING_MEDIA_SESSION_KEY, None)
        path = (pending or {}).get('path')
        if path and default_storage.exists(path):
            try:
                default_storage.delete(path)
            except OSError:
                pass
        return JsonResponse({'ok': True})


FLOW_IMAGE_EXTENSIONS = frozenset({'.jpg', '.jpeg', '.png', '.gif', '.webp'})


class FlowMediaUploadView(WorkspaceScopedMixin, PanelAccessMixin, View):
    """آپلود عکس برای نودهای جریان /start."""

    http_method_names = ['post']

    def post(self, request, *args, **kwargs):
        upload = request.FILES.get('file')
        if not upload:
            return JsonResponse({'ok': False, 'error': 'فایلی ارسال نشد.'}, status=400)

        ext = Path(upload.name).suffix.lower()
        if ext not in FLOW_IMAGE_EXTENSIONS:
            return JsonResponse(
                {'ok': False, 'error': 'فقط تصویر (jpg, png, gif, webp) مجاز است.'},
                status=400,
            )

        ct = (upload.content_type or '').lower()
        if ct and not ct.startswith('image/') and ct != 'application/octet-stream':
            return JsonResponse(
                {'ok': False, 'error': 'نوع فایل به‌عنوان تصویر شناخته نشد.'},
                status=400,
            )

        max_bytes = 10 * 1024 * 1024
        if getattr(upload, 'size', 0) and upload.size > max_bytes:
            return JsonResponse(
                {'ok': False, 'error': 'حجم فایل از ۱۰ مگابایت بیشتر است.'},
                status=400,
            )

        media = FlowMedia.objects.create(
            file=upload,
            platform=self.get_active_platform(),
            workspace=self.get_workspace(),
        )
        return JsonResponse(
            {
                'ok': True,
                'media_id': str(media.pk),
                'name': Path(upload.name).name,
            },
        )


class CampaignDetailView(WorkspaceScopedMixin, PanelAccessMixin, DetailView):
    model = Campaign
    template_name = 'balebot/campaign_detail.html'

    def get_queryset(self):
        return Campaign.objects.filter(**self.scope_filter())

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        d = self.object.deliveries.select_related('subscriber').order_by('-created_at')
        ctx['deliveries'] = d[:500]
        ctx['delivery_stats'] = self.object.deliveries.values('status').annotate(c=Count('id'))
        obj = self.object
        ctx['campaign_waiting_future_schedule'] = (
            obj.status == Campaign.Status.QUEUED
            and obj.schedule_kind == Campaign.ScheduleKind.SCHEDULED
            and obj.scheduled_at is not None
            and obj.scheduled_at > timezone.now()
        )
        ctx['target_tags'] = self.object.target_tags.order_by('name')
        ctx['audience_snapshot_count'] = len(self.object.audience_snapshot or [])
        return ctx

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        action = request.POST.get('action')
        if action == 'queue':
            if self.object.status not in (
                Campaign.Status.DRAFT,
                Campaign.Status.CANCELLED,
            ):
                messages.warning(request, 'این وضعیت کمپین قابل صف‌بندی نیست.')
                return HttpResponseRedirect(self.object.get_absolute_url())
            self.object.status = Campaign.Status.QUEUED
            if self.object.schedule_kind == Campaign.ScheduleKind.SCHEDULED:
                if not self.object.scheduled_at:
                    messages.warning(
                        request,
                        'برای کمپین زمان‌بندی‌شده ابتدا تاریخ و ساعت شمسی را در ویرایش کمپین ذخیره کنید.',
                    )
                    return HttpResponseRedirect(self.object.get_absolute_url())
            else:
                self.object.scheduled_at = timezone.now()
            self.object.save(update_fields=['status', 'scheduled_at', 'updated_at'])
            snapshot_ids = snapshot_campaign_audience(self.object)

            should_send_now = (
                self.object.schedule_kind == Campaign.ScheduleKind.INSTANT
                or (
                    self.object.schedule_kind == Campaign.ScheduleKind.SCHEDULED
                    and self.object.scheduled_at
                    and self.object.scheduled_at <= timezone.now()
                )
            )

            if should_send_now:
                ok, msg = run_single_campaign_web(self.object.pk)
                if ok:
                    messages.success(request, f'{msg} (مخاطب Snapshot: {len(snapshot_ids)} نفر)')
                else:
                    messages.error(request, msg)
            else:
                messages.success(
                    request,
                    f'کمپین زمان‌بندی‌شده در صف قرار گرفت (Snapshot: {len(snapshot_ids)} نفر).',
                )
        elif action == 'cancel':
            self.object.status = Campaign.Status.CANCELLED
            self.object.save(update_fields=['status', 'updated_at'])
            messages.warning(request, 'کمپین لغو شد.')
        return HttpResponseRedirect(self.object.get_absolute_url())


class CallbackLogListView(WorkspaceScopedMixin, PanelAccessMixin, ListView):
    model = CallbackLog
    template_name = 'balebot/callback_log_list.html'
    paginate_by = 50

    def get_queryset(self):
        scope = self.scope_filter()
        return (
            CallbackLog.objects.filter(
                subscriber__workspace=scope['workspace'],
                subscriber__platform=scope['platform'],
            )
            .select_related('subscriber', 'campaign')
            .order_by('-created_at')
        )


class InboundListView(WorkspaceScopedMixin, PanelAccessMixin, ListView):
    model = InboundMessage
    template_name = 'balebot/inbound_list.html'
    paginate_by = 50

    def get_queryset(self):
        scope = self.scope_filter()
        return (
            InboundMessage.objects.filter(
                subscriber__workspace=scope['workspace'],
                subscriber__platform=scope['platform'],
            )
            .select_related('subscriber')
            .order_by('-created_at')
        )
