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
from balebot.services import bale_api
from balebot.services.campaign_runner import run_single_campaign_web
from balebot.services.keyboard_layout import keyboard_has_any_button, normalize_to_sections
from balebot.models import (
    BotSettings,
    CallbackLog,
    Campaign,
    CampaignDelivery,
    InboundMessage,
    Subscriber,
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
        qs = Subscriber.objects.all().order_by('-updated_at')
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
        return qs


class SubscriberDetailView(StaffRequiredMixin, DetailView):
    model = Subscriber
    template_name = 'balebot/subscriber_detail.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        qs = InboundMessage.objects.filter(subscriber=self.object).order_by('-created_at')
        ctx['inbound_messages'] = qs[:200]
        ctx['support_messages_count'] = qs.filter(is_support_request=True).count()
        return ctx

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        msg = (request.POST.get('personal_message') or '').strip()
        media = request.FILES.get('personal_media')
        if not msg and not media:
            messages.error(request, 'برای ارسال، متن پیام یا فایل مدیا را وارد کنید.')
            return HttpResponseRedirect(self.request.path)

        try:
            if media:
                self._send_personal_media(media, msg)
            else:
                bale_api.send_message(self.object.chat_id, msg[:4096])
        except bale_api.BaleAPIError as e:
            messages.error(request, f'ارسال پیام ناموفق بود: {e}')
            return HttpResponseRedirect(self.request.path)
        messages.success(request, 'پیام شخصی با موفقیت ارسال شد.')
        return HttpResponseRedirect(self.request.path)

    def _send_personal_media(self, media, caption_text: str) -> None:
        suffix = Path(media.name or '').suffix
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix or '.bin') as tmp:
            for chunk in media.chunks():
                tmp.write(chunk)
            temp_path = Path(tmp.name)

        caption = (caption_text or '').strip()[:1024]
        content_type = (getattr(media, 'content_type', '') or '').lower()
        try:
            if content_type.startswith('image/'):
                bale_api.send_photo(self.object.chat_id, photo_path=temp_path, caption=caption)
                return
            if content_type.startswith('video/'):
                bale_api.send_video(self.object.chat_id, video_path=temp_path, caption=caption)
                return
            if content_type in {'audio/ogg', 'audio/opus'}:
                bale_api.send_voice(self.object.chat_id, voice_path=temp_path, caption=caption)
                return
            bale_api.send_document(
                self.object.chat_id,
                document_path=temp_path,
                caption=caption,
            )
        finally:
            try:
                temp_path.unlink(missing_ok=True)
            except OSError:
                pass


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
                    messages.success(request, msg)
                else:
                    messages.error(request, msg)
            else:
                messages.success(
                    request,
                    'کمپین زمان‌بندی‌شده در صف قرار گرفت و در زمان مقرّر ارسال می‌شود.',
                )
        elif action == 'cancel':
            self.object.status = Campaign.Status.CANCELLED
            self.object.save(update_fields=['status', 'updated_at'])
            messages.warning(request, 'کمپین لغو شد.')
        return HttpResponseRedirect(self.object.get_absolute_url())


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
