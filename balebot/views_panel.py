import uuid
from pathlib import Path
import tempfile

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.files.storage import default_storage
from django.db.models import Count, Q
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import DetailView, ListView, TemplateView
from django.views.generic.edit import CreateView, UpdateView

from balebot.forms import BotSettingsForm, CampaignForm, FlowEngineForm, TagForm
from balebot.platform import (
    allowed_platforms_for_workspace,
    get_active_platform,
    get_bot_settings_for_request,
    has_miniapp_access_for_request,
    platform_label,
    require_workspace_for_request,
    set_active_platform,
)
from balebot.workspace import user_has_panel_access
from balebot.services import messenger_api
from balebot.services.webhook_setup import (
    explain_telegram_webhook_error,
    validate_webhook_url,
)
from balebot.services.public_url import ensure_webhook_config
from balebot.services.campaign_runner import (
    campaign_delivery_progress,
    run_campaign_delivery_batch,
    transition_queued_to_sending_if_due,
)
from balebot.services.audience import snapshot_campaign_audience
from balebot.services.workspace_subscription import workspace_block_reason
from balebot.models import (
    BotSettings,
    CallbackLog,
    Campaign,
    CampaignDelivery,
    CatalogItem,
    CatalogOrder,
    CatalogSettings,
    FlowMedia,
    InboundMessage,
    Platform,
    Subscriber,
    SubscriberTag,
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
        return get_active_platform(self.request, self.get_workspace())

    def scope_filter(self) -> dict:
        return {'workspace': self.get_workspace(), 'platform': self.get_active_platform()}

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        workspace = self.get_workspace()
        ctx['active_platform'] = self.get_active_platform()
        ctx['active_platform_label'] = platform_label(ctx['active_platform'])
        ctx['available_platforms'] = allowed_platforms_for_workspace(workspace)
        ctx['panel_workspace'] = workspace
        return ctx


class SwitchPlatformView(PanelAccessMixin, View):
    http_method_names = ['get', 'post']

    def get(self, request, *args, **kwargs):
        return HttpResponseRedirect(request.META.get('HTTP_REFERER') or '/')

    def post(self, request, *args, **kwargs):
        workspace = require_workspace_for_request(request)
        platform = (request.POST.get('platform') or '').strip()
        set_active_platform(request, platform, workspace)
        next_url = request.POST.get('next') or request.META.get('HTTP_REFERER') or '/'
        return HttpResponseRedirect(next_url)


class PlatformSyncView(WorkspaceScopedMixin, PanelAccessMixin, View):
    """کپی تنظیمات پلتفرم فعال به پلتفرم دیگر (بله ↔ تلگرام)."""

    http_method_names = ['post']

    def post(self, request, *args, **kwargs):
        from balebot.services.platform_sync import sync_platform_data

        workspace = self.get_workspace()
        source = self.get_active_platform()
        target = (request.POST.get('target_platform') or '').strip()
        allowed = {value for value, _ in allowed_platforms_for_workspace(workspace)}
        if target not in allowed or target == source:
            messages.error(request, 'پلتفرم مقصد نامعتبر است.')
            return HttpResponseRedirect(request.POST.get('next') or request.META.get('HTTP_REFERER') or '/')

        copy_bot = request.POST.get('copy_bot') == '1'
        copy_catalog = request.POST.get('copy_catalog') == '1'
        copy_tags = request.POST.get('copy_tags') == '1'
        copy_campaigns = request.POST.get('copy_campaigns') == '1'
        if not any((copy_bot, copy_catalog, copy_tags, copy_campaigns)):
            messages.error(request, 'حداقل یک بخش را برای انتقال انتخاب کنید.')
            return HttpResponseRedirect(request.POST.get('next') or '/')

        try:
            result = sync_platform_data(
                workspace,
                source,
                target,
                copy_bot=copy_bot,
                copy_catalog=copy_catalog,
                copy_tags=copy_tags,
                copy_campaigns=copy_campaigns,
            )
        except Exception as exc:
            messages.error(request, f'انتقال ناموفق: {exc}')
            return HttpResponseRedirect(request.POST.get('next') or '/')

        parts = []
        if result.bot_settings:
            parts.append('تنظیمات و جریان ربات')
        if result.flow_media:
            parts.append(f'{result.flow_media} رسانهٔ جریان')
        if result.catalog_settings:
            parts.append('مینی‌اپ')
        if result.categories:
            parts.append(f'{result.categories} دسته')
        if result.items:
            parts.append(f'{result.items} محصول')
        if result.tags:
            parts.append(f'{result.tags} برچسب')
        if result.campaigns:
            parts.append(f'{result.campaigns} کمپین')
        summary = '، '.join(parts) if parts else 'بدون تغییر'
        messages.success(
            request,
            f'از {platform_label(source)} به {platform_label(target)} منتقل شد: {summary}. '
            f'توکن و چت‌آیدی ادمین هر پلتفرم دست‌نخورده ماند.',
        )
        return HttpResponseRedirect(request.POST.get('next') or '/')


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
        delivery_total = sent + failed
        ctx['delivery_rate_pct'] = round(sent * 100 / delivery_total, 1) if delivery_total else None
        week_ago = timezone.now() - timezone.timedelta(days=7)
        ctx['subscriber_new_week'] = Subscriber.objects.filter(
            **scope, created_at__gte=week_ago,
        ).count()
        ctx['inbound_recent'] = (
            InboundMessage.objects.filter(
                subscriber__workspace=scope['workspace'],
                subscriber__platform=scope['platform'],
            )
            .select_related('subscriber')
            .order_by('-created_at')[:15]
        )
        ctx['support_tickets_recent'] = (
            InboundMessage.objects.filter(
                subscriber__workspace=scope['workspace'],
                subscriber__platform=scope['platform'],
                is_support_request=True,
            )
            .select_related('subscriber')
            .order_by('-created_at')[:6]
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
        ctx['has_miniapp_access'] = has_miniapp_access_for_request(self.request, scope['workspace'])
        if ctx['has_miniapp_access']:
            catalog = CatalogSettings.get_for_platform(scope['workspace'], scope['platform'])
            bot = get_bot_settings_for_request(self.request)
            ctx['catalog'] = catalog
            ctx['catalog_theme'] = catalog.theme_config or {}
            ctx['catalog_item_count'] = CatalogItem.objects.filter(**scope).count()
            ctx['catalog_order_pending'] = CatalogOrder.objects.filter(
                **scope,
                status=CatalogOrder.Status.PENDING,
            ).count()
            ctx['mini_app_url'] = catalog.build_mini_app_url(bot)
        return ctx


class FlowEngineView(WorkspaceScopedMixin, PanelAccessMixin, TemplateView):
    template_name = 'balebot/flow_engine.html'

    def _bot(self):
        return get_bot_settings_for_request(self.request)

    def _context(self, bot_form=None):
        scope = self.scope_filter()
        bot = self._bot()
        ctx = {
            'bot_form': bot_form or FlowEngineForm(instance=bot),
            'has_miniapp_access': has_miniapp_access_for_request(self.request, scope['workspace']),
        }
        if ctx['has_miniapp_access']:
            catalog = CatalogSettings.get_for_platform(scope['workspace'], scope['platform'])
            ctx['mini_app_url'] = catalog.build_mini_app_url(bot)
        return ctx

    def get_context_data(self, **kwargs):
        return {**super().get_context_data(**kwargs), **self._context()}

    def post(self, request, *args, **kwargs):
        bot = self._bot()
        form = FlowEngineForm(request.POST, instance=bot)
        if form.is_valid():
            form.save()
            messages.success(
                request,
                f'جریان /start برای {platform_label(bot.platform)} ذخیره شد.',
            )
            return HttpResponseRedirect(reverse_lazy('bot_flow_engine'))
        messages.error(request, 'ذخیره نشد. خطاهای فرم را برطرف کنید.')
        return self.render_to_response(self._context(bot_form=form))


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
        posted_token = (request.POST.get('bot_token') or '').strip()
        update_fields = ensure_webhook_config(obj)
        if posted_token:
            obj.bot_token = posted_token
            update_fields.append('bot_token')
        if update_fields:
            update_fields.append('updated_at')
            obj.save(update_fields=list(dict.fromkeys(update_fields)))

        url = obj.build_webhook_url()
        if not obj.has_bot_token():
            messages.error(request, 'ابتدا توکن ربات را وارد کنید.')
            return self._redirect_after_webhook(request)
        if not url:
            messages.error(
                request,
                'آدرس عمومی سرور (BASE_URL) در تنظیمات سرور پیکربندی نشده است.',
            )
            return self._redirect_after_webhook(request)

        ok, err = validate_webhook_url(url, platform=obj.platform)
        if not ok:
            messages.error(request, err)
            return self._redirect_after_webhook(request)

        try:
            messenger_api.set_webhook(obj.platform, url, settings=obj)
            messages.success(request, f'وب‌هوک ثبت شد: {url}')
        except messenger_api.MessengerAPIError as e:
            detail = explain_telegram_webhook_error(str(e)) if obj.platform == Platform.TELEGRAM else str(e)
            messages.error(request, f'ثبت وب‌هوک ناموفق: {detail}')
        return self._redirect_after_webhook(request)

    def _redirect_after_webhook(self, request):
        next_url = (request.POST.get('next') or '').strip()
        if next_url:
            return HttpResponseRedirect(next_url)
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
        qs = qs.prefetch_related('tags')
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


class TagListView(WorkspaceScopedMixin, PanelAccessMixin, ListView):
    model = Tag
    template_name = 'balebot/tag_list.html'
    context_object_name = 'tags'

    def get_queryset(self):
        return (
            Tag.objects.filter(**self.scope_filter())
            .annotate(subscriber_count=Count('subscribers', distinct=True))
            .order_by('name')
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['tag_form'] = kwargs.get('tag_form') or TagForm(
            workspace=self.get_workspace(),
            platform=self.get_active_platform(),
        )
        return ctx

    def post(self, request, *args, **kwargs):
        form = TagForm(
            request.POST,
            workspace=self.get_workspace(),
            platform=self.get_active_platform(),
        )
        if form.is_valid():
            form.save()
            messages.success(request, f'دسته‌بندی «{form.instance.name}» ایجاد شد.')
            return HttpResponseRedirect(reverse('tag_list'))
        self.object_list = self.get_queryset()
        ctx = self.get_context_data(tag_form=form)
        return self.render_to_response(ctx)


class TagDeleteView(WorkspaceScopedMixin, PanelAccessMixin, View):
    def post(self, request, *args, **kwargs):
        tag = get_object_or_404(Tag, pk=kwargs['pk'], **self.scope_filter())
        name = tag.name
        tag.delete()
        messages.success(request, f'دسته‌بندی «{name}» حذف شد.')
        return HttpResponseRedirect(reverse('tag_list'))


class SubscriberDetailView(WorkspaceScopedMixin, PanelAccessMixin, DetailView):
    model = Subscriber
    template_name = 'balebot/subscriber_detail.html'

    def get_queryset(self):
        return Subscriber.objects.filter(**self.scope_filter()).prefetch_related('tags')

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
        ctx['subscriber_tags'] = list(self.object.tags.filter(is_active=True).order_by('name'))
        ctx['available_tags'] = Tag.objects.filter(
            **self.scope_filter(), is_active=True,
        ).exclude(pk__in=[t.pk for t in ctx['subscriber_tags']]).order_by('name')
        return ctx

    def _redirect_subscriber(self, request):
        ticket = (request.GET.get('ticket') or request.POST.get('ticket_id') or '').strip()
        if ticket.isdigit():
            return HttpResponseRedirect(f'{request.path}?ticket={ticket}')
        return HttpResponseRedirect(request.path)

    def _assign_tag(self, request, tag: Tag) -> None:
        link, created = SubscriberTag.objects.get_or_create(
            subscriber=self.object,
            tag=tag,
        )
        if created or link.assigned_by_id is None:
            link.assigned_by = request.user
            link.save(update_fields=['assigned_by'])
        messages.success(request, f'دسته‌بندی «{tag.name}» به کاربر اضافه شد.')

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        action = (request.POST.get('action') or '').strip()

        if action == 'assign_tag':
            tag_raw = (request.POST.get('tag_id') or '').strip()
            if not tag_raw.isdigit():
                messages.error(request, 'دسته‌بندی انتخاب‌شده نامعتبر است.')
                return self._redirect_subscriber(request)
            tag = Tag.objects.filter(
                pk=int(tag_raw), **self.scope_filter(), is_active=True,
            ).first()
            if tag is None:
                messages.error(request, 'دسته‌بندی پیدا نشد.')
                return self._redirect_subscriber(request)
            self._assign_tag(request, tag)
            return self._redirect_subscriber(request)

        if action == 'create_assign_tag':
            from django.utils.text import slugify

            name = (request.POST.get('tag_name') or '').strip()[:120]
            if not name:
                messages.error(request, 'نام دسته‌بندی را وارد کنید.')
                return self._redirect_subscriber(request)
            scope = self.scope_filter()
            slug = slugify(name, allow_unicode=False)[:140]
            if not slug:
                slug = f'tag-{uuid.uuid4().hex[:8]}'
            tag, _ = Tag.objects.get_or_create(
                workspace=scope['workspace'],
                platform=scope['platform'],
                slug=slug,
                defaults={
                    'name': name,
                    'tag_type': Tag.TagType.GENERIC,
                    'is_active': True,
                },
            )
            self._assign_tag(request, tag)
            return self._redirect_subscriber(request)

        if action == 'remove_tag':
            tag_raw = (request.POST.get('tag_id') or '').strip()
            if tag_raw.isdigit():
                deleted, _ = SubscriberTag.objects.filter(
                    subscriber=self.object,
                    tag_id=int(tag_raw),
                    tag__workspace=self.object.workspace,
                    tag__platform=self.object.platform,
                ).delete()
                if deleted:
                    messages.success(request, 'دسته‌بندی از کاربر حذف شد.')
                else:
                    messages.warning(request, 'این دسته‌بندی روی کاربر نبود.')
            return self._redirect_subscriber(request)

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
        ctx.update(campaign_form_media_context(self.request, self.object))
        return ctx

    def get_queryset(self):
        return Campaign.objects.filter(**self.scope_filter())

    def get_success_url(self):
        return reverse_lazy('campaign_detail', kwargs={'pk': self.object.pk})


class CampaignDeleteView(WorkspaceScopedMixin, PanelAccessMixin, View):
    http_method_names = ['post']

    def post(self, request, pk, *args, **kwargs):
        campaign = get_object_or_404(
            Campaign.objects.filter(**self.scope_filter()),
            pk=pk,
        )
        if campaign.status == Campaign.Status.SENDING:
            messages.error(
                request,
                'کمپین در حال ارسال است و قابل حذف نیست. ابتدا از صفحهٔ جزئیات آن را لغو کنید.',
            )
            return HttpResponseRedirect(reverse('campaign_list'))

        title = campaign.title
        campaign.delete()
        messages.success(request, f'کمپین «{title}» حذف شد.')
        return HttpResponseRedirect(reverse('campaign_list'))


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
FLOW_VIDEO_EXTENSIONS = frozenset({'.mp4', '.mov', '.mkv', '.webm'})
FLOW_VOICE_EXTENSIONS = frozenset({'.ogg', '.oga', '.mp3', '.m4a', '.wav', '.opus'})
FLOW_DOCUMENT_EXTENSIONS = frozenset(
    {'.pdf', '.zip', '.rar', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.txt'},
)
FLOW_MEDIA_MAX_BYTES = {
    'photo': 10 * 1024 * 1024,
    'video': 50 * 1024 * 1024,
    'voice': 10 * 1024 * 1024,
    'document': 20 * 1024 * 1024,
}


def _detect_flow_media_kind(ext: str, content_type: str) -> str | None:
    ext = (ext or '').lower()
    ct = (content_type or '').lower()
    if ext in FLOW_IMAGE_EXTENSIONS or ct.startswith('image/'):
        return FlowMedia.MediaKind.PHOTO
    if ext in FLOW_VIDEO_EXTENSIONS or ct.startswith('video/'):
        return FlowMedia.MediaKind.VIDEO
    if ext in FLOW_VOICE_EXTENSIONS or ct.startswith('audio/'):
        return FlowMedia.MediaKind.VOICE
    if ext in FLOW_DOCUMENT_EXTENSIONS or ct in (
        'application/pdf',
        'application/zip',
        'application/x-zip-compressed',
        'application/msword',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'application/vnd.ms-excel',
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'application/vnd.ms-powerpoint',
        'application/vnd.openxmlformats-officedocument.presentationml.presentation',
        'text/plain',
    ):
        return FlowMedia.MediaKind.DOCUMENT
    if ext and ext not in FLOW_IMAGE_EXTENSIONS | FLOW_VIDEO_EXTENSIONS | FLOW_VOICE_EXTENSIONS:
        return FlowMedia.MediaKind.DOCUMENT
    return None


class FlowMediaUploadView(WorkspaceScopedMixin, PanelAccessMixin, View):
    """آپلود رسانه برای نودهای جریان /start."""

    http_method_names = ['post']

    def post(self, request, *args, **kwargs):
        upload = request.FILES.get('file')
        if not upload:
            return JsonResponse({'ok': False, 'error': 'فایلی ارسال نشد.'}, status=400)

        ext = Path(upload.name).suffix.lower()
        media_kind = _detect_flow_media_kind(ext, upload.content_type or '')
        if not media_kind:
            return JsonResponse(
                {
                    'ok': False,
                    'error': 'نوع فایل پشتیبانی نمی‌شود. عکس، ویدیو، صدا یا فایل مجاز است.',
                },
                status=400,
            )

        max_bytes = FLOW_MEDIA_MAX_BYTES.get(media_kind, 10 * 1024 * 1024)
        if getattr(upload, 'size', 0) and upload.size > max_bytes:
            mb = max(1, max_bytes // (1024 * 1024))
            return JsonResponse(
                {'ok': False, 'error': f'حجم فایل از {mb} مگابایت بیشتر است.'},
                status=400,
            )

        media = FlowMedia.objects.create(
            file=upload,
            media_kind=media_kind,
            platform=self.get_active_platform(),
            workspace=self.get_workspace(),
        )
        return JsonResponse(
            {
                'ok': True,
                'media_id': str(media.pk),
                'media_kind': media_kind,
                'name': Path(upload.name).name,
                'url': media.file.url if media.file else '',
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
        progress = campaign_delivery_progress(self.object)
        ctx['send_progress'] = progress
        ctx['campaign_send_autostart'] = (
            self.request.GET.get('autostart') == '1'
            or (
                self.object.status == Campaign.Status.SENDING
                and progress['pending'] > 0
            )
        )
        ctx['campaign_send_batch_url'] = reverse(
            'campaign_send_batch',
            kwargs={'pk': self.object.pk},
        )
        ctx['campaign_send_batch_size'] = getattr(settings, 'CAMPAIGN_SEND_BATCH_SIZE', 5)
        return ctx

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        action = request.POST.get('action')
        if action == 'queue':
            block_reason = workspace_block_reason(self.object.workspace)
            if block_reason:
                messages.error(request, block_reason)
                return HttpResponseRedirect(self.object.get_absolute_url())
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
                transition_queued_to_sending_if_due(self.object, timezone.now())
                messages.success(
                    request,
                    f'ارسال آغاز شد (Snapshot: {len(snapshot_ids)} نفر). پیام‌ها دسته‌ای ارسال می‌شوند.',
                )
                return HttpResponseRedirect(
                    self.object.get_absolute_url() + '?autostart=1',
                )
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


class CampaignSendBatchView(WorkspaceScopedMixin, PanelAccessMixin, View):
    """ارسال دسته‌ای کمپین (AJAX از صفحهٔ جزئیات)."""

    http_method_names = ['post']

    def post(self, request, pk, *args, **kwargs):
        campaign = get_object_or_404(
            Campaign.objects.filter(**self.scope_filter()),
            pk=pk,
        )
        result = run_campaign_delivery_batch(campaign.pk)
        if not result.get('ok'):
            return JsonResponse(result, status=400)
        return JsonResponse(result)


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
