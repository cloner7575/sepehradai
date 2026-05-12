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

from balebot.forms import BotSettingsForm, CampaignForm, ClassTagForm
from balebot.services import bale_api
from balebot.services.audience import snapshot_campaign_audience
from balebot.services.campaign_runner import run_single_campaign_web
from balebot.services.keyboard_layout import keyboard_has_any_button, normalize_to_sections
from balebot.models import (
    BotSettings,
    CallbackLog,
    Campaign,
    CampaignDelivery,
    ClassEnrollmentRequest,
    InboundMessage,
    Subscriber,
    SubscriberTag,
    SupportTicketMessage,
    Tag,
)

CAMPAIGN_PENDING_MEDIA_SESSION_KEY = 'campaign_pending_media'

CAMPAIGN_VIDEO_UPLOAD_EXTENSIONS = frozenset(
    {'.mp4', '.webm', '.mov', '.mkv', '.mpeg', '.mpg', '.m4v', '.avi'},
)


class StaffRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """فقط کاربران staff."""

    def test_func(self):
        return self.request.user.is_staff


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


class DashboardView(StaffRequiredMixin, TemplateView):
    template_name = 'balebot/dashboard.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['subscriber_active'] = Subscriber.objects.filter(is_active=True, is_registered=True).count()
        ctx['subscriber_total'] = Subscriber.objects.count()
        ctx['campaign_recent'] = Campaign.objects.order_by('-created_at')[:8]
        sent = CampaignDelivery.objects.filter(status=CampaignDelivery.DeliveryStatus.SENT).count()
        failed = CampaignDelivery.objects.filter(status=CampaignDelivery.DeliveryStatus.FAILED).count()
        ctx['delivery_sent'] = sent
        ctx['delivery_failed'] = failed
        ctx['inbound_recent'] = InboundMessage.objects.select_related('subscriber').order_by('-created_at')[:15]
        ctx['campaign_total'] = Campaign.objects.count()
        ctx['campaign_running'] = Campaign.objects.filter(
            status__in=(Campaign.Status.QUEUED, Campaign.Status.SENDING),
        ).count()
        ctx['callback_recent_count'] = CallbackLog.objects.count()
        return ctx


class BotSettingsView(StaffRequiredMixin, UpdateView):
    model = BotSettings
    form_class = BotSettingsForm
    template_name = 'balebot/bot_settings.html'

    def get_object(self, queryset=None):
        return BotSettings.get_solo()

    def get_success_url(self):
        return reverse_lazy('bot_settings')

    def form_valid(self, form):
        messages.success(
            self.request,
            'تنظیمات بازو ذخیره شد و از طریق وب‌هوک برای پیام‌های بعدی اعمال می‌شود.',
        )
        return super().form_valid(form)


class SubscriberListView(StaffRequiredMixin, ListView):
    model = Subscriber
    template_name = 'balebot/subscriber_list.html'
    paginate_by = 40

    def get_queryset(self):
        qs = Subscriber.objects.annotate(
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
                cond |= Q(bale_user_id=n) | Q(chat_id=n)
            qs = qs.filter(cond)
        tag_raw = (self.request.GET.get('tag') or '').strip()
        if tag_raw.isdigit():
            qs = qs.filter(tags__id=int(tag_raw)).distinct()
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['available_tags'] = Tag.objects.filter(is_active=True).order_by('name')
        ctx['selected_tag_id'] = (self.request.GET.get('tag') or '').strip()
        return ctx


class SubscriberDetailView(StaffRequiredMixin, DetailView):
    model = Subscriber
    template_name = 'balebot/subscriber_detail.html'

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
            if media:
                kind, text_body, file_id = self._send_personal_media(media, msg)
            else:
                bale_api.send_message(self.object.chat_id, msg[:4096])
                kind = SupportTicketMessage.MessageKind.TEXT
                text_body = msg[:4096]
                file_id = ''
        except bale_api.BaleAPIError as e:
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

    def _send_personal_media(self, media, caption_text: str) -> tuple[str, str, str]:
        suffix = Path(media.name or '').suffix
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix or '.bin') as tmp:
            for chunk in media.chunks():
                tmp.write(chunk)
            temp_path = Path(tmp.name)

        caption = (caption_text or '').strip()[:1024]
        content_type = (getattr(media, 'content_type', '') or '').lower()
        try:
            if content_type.startswith('image/'):
                resp = bale_api.send_photo(self.object.chat_id, photo_path=temp_path, caption=caption)
                return (
                    SupportTicketMessage.MessageKind.PHOTO,
                    caption,
                    self._extract_file_id(resp, 'photo'),
                )
            if content_type.startswith('video/'):
                resp = bale_api.send_video(self.object.chat_id, video_path=temp_path, caption=caption)
                return (
                    SupportTicketMessage.MessageKind.VIDEO,
                    caption,
                    self._extract_file_id(resp, 'video'),
                )
            if content_type in {'audio/ogg', 'audio/opus'}:
                resp = bale_api.send_voice(self.object.chat_id, voice_path=temp_path, caption=caption)
                return (
                    SupportTicketMessage.MessageKind.VOICE,
                    caption,
                    self._extract_file_id(resp, 'voice'),
                )
            resp = bale_api.send_document(
                self.object.chat_id,
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



class CampaignListView(StaffRequiredMixin, ListView):
    model = Campaign
    template_name = 'balebot/campaign_list.html'
    paginate_by = 30

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        qs = Campaign.objects.all()
        ctx['campaign_stat_total'] = qs.count()
        ctx['campaign_stat_draft'] = qs.filter(status=Campaign.Status.DRAFT).count()
        ctx['campaign_stat_running'] = qs.filter(
            status__in=(Campaign.Status.QUEUED, Campaign.Status.SENDING),
        ).count()
        ctx['campaign_stat_done'] = qs.filter(status=Campaign.Status.COMPLETED).count()
        return ctx


class CampaignCreateView(StaffRequiredMixin, CreateView):
    model = Campaign
    form_class = CampaignForm
    template_name = 'balebot/campaign_form.html'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['campaign_keyboard_expanded'] = False
        ctx.update(campaign_form_media_context(self.request, None))
        return ctx

    def form_valid(self, form):
        form.instance.status = Campaign.Status.DRAFT
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('campaign_detail', kwargs={'pk': self.object.pk})


class CampaignUpdateView(StaffRequiredMixin, UpdateView):
    model = Campaign
    form_class = CampaignForm
    template_name = 'balebot/campaign_form.html'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['campaign_keyboard_expanded'] = keyboard_has_any_button(
            normalize_to_sections(self.object.inline_keyboard),
        )
        ctx.update(campaign_form_media_context(self.request, self.object))
        return ctx

    def get_success_url(self):
        return reverse_lazy('campaign_detail', kwargs={'pk': self.object.pk})


class CampaignMediaUploadView(StaffRequiredMixin, View):
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


class CampaignMediaClearView(StaffRequiredMixin, View):
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


class CampaignDetailView(StaffRequiredMixin, DetailView):
    model = Campaign
    template_name = 'balebot/campaign_detail.html'

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


class EnrollmentRequestListView(StaffRequiredMixin, ListView):
    model = ClassEnrollmentRequest
    template_name = 'balebot/enrollment_request_list.html'
    paginate_by = 40

    def get_queryset(self):
        qs = ClassEnrollmentRequest.objects.select_related('subscriber', 'tag', 'reviewed_by')
        status_q = (self.request.GET.get('status') or '').strip().lower()
        if status_q in {
            ClassEnrollmentRequest.Status.PENDING,
            ClassEnrollmentRequest.Status.APPROVED,
            ClassEnrollmentRequest.Status.REJECTED,
        }:
            qs = qs.filter(status=status_q)
        return qs.order_by('-requested_at')

    def post(self, request, *args, **kwargs):
        action = (request.POST.get('action') or '').strip().lower()
        req_id = (request.POST.get('request_id') or '').strip()
        if not req_id.isdigit():
            messages.error(request, 'درخواست نامعتبر است.')
            return HttpResponseRedirect(request.path)
        enrollment = ClassEnrollmentRequest.objects.select_related('subscriber', 'tag').filter(
            id=int(req_id)
        ).first()
        if enrollment is None:
            messages.error(request, 'درخواست پیدا نشد.')
            return HttpResponseRedirect(request.path)
        if enrollment.status != ClassEnrollmentRequest.Status.PENDING:
            messages.warning(request, 'این درخواست قبلا بررسی شده است.')
            return HttpResponseRedirect(request.path)

        if action == 'approve':
            SubscriberTag.objects.get_or_create(
                subscriber=enrollment.subscriber,
                tag=enrollment.tag,
                defaults={'assigned_by': request.user},
            )
            enrollment.status = ClassEnrollmentRequest.Status.APPROVED
            enrollment.reviewed_at = timezone.now()
            enrollment.reviewed_by = request.user
            enrollment.save(update_fields=['status', 'reviewed_at', 'reviewed_by'])
            try:
                bale_api.send_message(
                    enrollment.subscriber.chat_id,
                    f'ثبت‌نام شما در کلاس «{enrollment.tag.name}» تایید شد.',
                )
            except bale_api.BaleAPIError:
                pass
            messages.success(request, 'درخواست ثبت‌نام تایید شد.')
        elif action == 'reject':
            enrollment.status = ClassEnrollmentRequest.Status.REJECTED
            enrollment.reviewed_at = timezone.now()
            enrollment.reviewed_by = request.user
            enrollment.save(update_fields=['status', 'reviewed_at', 'reviewed_by'])
            try:
                bale_api.send_message(
                    enrollment.subscriber.chat_id,
                    f'درخواست ثبت‌نام شما برای کلاس «{enrollment.tag.name}» رد شد.',
                )
            except bale_api.BaleAPIError:
                pass
            messages.warning(request, 'درخواست ثبت‌نام رد شد.')
        return HttpResponseRedirect(request.path)


class ClassTagListView(StaffRequiredMixin, ListView):
    model = Tag
    template_name = 'balebot/class_tag_list.html'
    paginate_by = 30

    def get_queryset(self):
        return Tag.objects.filter(tag_type=Tag.TagType.CLASS).order_by('name')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['class_form'] = ClassTagForm()
        return ctx

    def post(self, request, *args, **kwargs):
        action = (request.POST.get('action') or '').strip().lower()
        if action == 'create':
            form = ClassTagForm(request.POST)
            if form.is_valid():
                form.save()
                messages.success(request, 'کلاس جدید ساخته شد.')
                return HttpResponseRedirect(request.path)
            ctx = self.get_context_data()
            ctx['class_form'] = form
            return self.render_to_response(ctx)
        if action in {'toggle_active', 'toggle_inactive'}:
            tag_id = (request.POST.get('tag_id') or '').strip()
            if not tag_id.isdigit():
                messages.error(request, 'شناسه کلاس نامعتبر است.')
                return HttpResponseRedirect(request.path)
            tag = Tag.objects.filter(id=int(tag_id), tag_type=Tag.TagType.CLASS).first()
            if tag is None:
                messages.error(request, 'کلاس پیدا نشد.')
                return HttpResponseRedirect(request.path)
            tag.is_active = action == 'toggle_active'
            tag.save(update_fields=['is_active', 'updated_at'])
            messages.success(
                request,
                'کلاس فعال شد.' if tag.is_active else 'کلاس غیرفعال شد.',
            )
        return HttpResponseRedirect(request.path)


class CallbackLogListView(StaffRequiredMixin, ListView):
    model = CallbackLog
    template_name = 'balebot/callback_log_list.html'
    paginate_by = 50

    def get_queryset(self):
        return CallbackLog.objects.select_related('subscriber', 'campaign').order_by('-created_at')


class InboundListView(StaffRequiredMixin, ListView):
    model = InboundMessage
    template_name = 'balebot/inbound_list.html'
    paginate_by = 50

    def get_queryset(self):
        return InboundMessage.objects.select_related('subscriber').order_by('-created_at')
