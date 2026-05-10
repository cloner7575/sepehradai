from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Count, Q
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import DetailView, ListView, TemplateView
from django.views.generic.edit import CreateView, UpdateView

from balebot.forms import BotSettingsForm, CampaignForm
from balebot.models import (
    BotSettings,
    CallbackLog,
    Campaign,
    CampaignDelivery,
    InboundMessage,
    Subscriber,
)


class StaffRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """فقط کاربران staff."""

    def test_func(self):
        return self.request.user.is_staff


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


class CampaignListView(StaffRequiredMixin, ListView):
    model = Campaign
    template_name = 'balebot/campaign_list.html'
    paginate_by = 30


class CampaignCreateView(StaffRequiredMixin, CreateView):
    model = Campaign
    form_class = CampaignForm
    template_name = 'balebot/campaign_form.html'

    def form_valid(self, form):
        form.instance.status = Campaign.Status.DRAFT
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('campaign_detail', kwargs={'pk': self.object.pk})


class CampaignUpdateView(StaffRequiredMixin, UpdateView):
    model = Campaign
    form_class = CampaignForm
    template_name = 'balebot/campaign_form.html'

    def get_success_url(self):
        return reverse_lazy('campaign_detail', kwargs={'pk': self.object.pk})


class CampaignDetailView(StaffRequiredMixin, DetailView):
    model = Campaign
    template_name = 'balebot/campaign_detail.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        d = self.object.deliveries.select_related('subscriber').order_by('-created_at')
        ctx['deliveries'] = d[:500]
        ctx['delivery_stats'] = self.object.deliveries.values('status').annotate(c=Count('id'))
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
            if self.object.scheduled_at is None:
                self.object.scheduled_at = timezone.now()
            self.object.save(update_fields=['status', 'scheduled_at', 'updated_at'])
            messages.success(
                request,
                'کمپین در صف قرار گرفت. ارسال با cron و دستور process_campaigns انجام می‌شود.',
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
