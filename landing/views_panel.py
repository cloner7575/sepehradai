from django.contrib import messages
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views.generic import DetailView, FormView, ListView, TemplateView, View

from balebot.mixins import SuperuserRequiredMixin
from balebot.models import Workspace
from landing.forms_panel import BrandSettingsForm, BusinessCategoryForm, LandingSettingsForm, SubscriptionPlanForm
from landing.models import BusinessCategory, LandingSettings, Lead, SubscriptionPlan

User = get_user_model()


def _panel_user_queryset():
    return User.objects.filter(is_staff=True, is_superuser=False).select_related('workspace')


def _subscription_stats(workspaces):
    unlimited = 0
    active = 0
    expiring = 0
    expired = 0
    now = timezone.now()
    soon = now + timezone.timedelta(days=7)
    for ws in workspaces:
        if ws is None:
            continue
        if ws.subscription_expires_at is None:
            unlimited += 1
            active += 1
            continue
        if ws.subscription_expires_at <= now:
            expired += 1
        elif ws.subscription_expires_at <= soon:
            expiring += 1
            active += 1
        else:
            active += 1
    return {
        'sub_unlimited': unlimited,
        'sub_active': active,
        'sub_expiring': expiring,
        'sub_expired': expired,
    }


class SuperAdminDashboardView(SuperuserRequiredMixin, TemplateView):
    template_name = 'balebot/superadmin/dashboard.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        panel_users = list(_panel_user_queryset())
        workspaces = []
        for user in panel_users:
            try:
                workspaces.append(user.workspace)
            except Workspace.DoesNotExist:
                workspaces.append(None)
        ctx.update({
            'lead_total': Lead.objects.count(),
            'lead_uncontacted': Lead.objects.filter(is_contacted=False).count(),
            'lead_today': Lead.objects.filter(
                created_at__date=timezone.localdate(),
            ).count(),
            'panel_user_total': len(panel_users),
            'plan_total': SubscriptionPlan.objects.count(),
            'plan_active': SubscriptionPlan.objects.filter(is_active=True).count(),
            'category_total': BusinessCategory.objects.count(),
            'category_active': BusinessCategory.objects.filter(is_active=True).count(),
            'recent_leads': Lead.objects.order_by('-created_at')[:8],
            **_subscription_stats(workspaces),
        })
        return ctx


class SuperAdminLeadListView(SuperuserRequiredMixin, ListView):
    model = Lead
    template_name = 'balebot/superadmin/lead_list.html'
    context_object_name = 'leads'
    paginate_by = 25

    def get_queryset(self):
        qs = Lead.objects.all()
        q = (self.request.GET.get('q') or '').strip()
        if q:
            qs = qs.filter(
                Q(name__icontains=q)
                | Q(phone__icontains=q)
                | Q(business_name__icontains=q)
                | Q(business_type__icontains=q)
                | Q(note__icontains=q)
            )
        status = self.request.GET.get('status', '')
        if status == 'contacted':
            qs = qs.filter(is_contacted=True)
        elif status == 'pending':
            qs = qs.filter(is_contacted=False)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['search_q'] = (self.request.GET.get('q') or '').strip()
        ctx['filter_status'] = self.request.GET.get('status', '')
        ctx['lead_stat_total'] = Lead.objects.count()
        ctx['lead_stat_pending'] = Lead.objects.filter(is_contacted=False).count()
        ctx['lead_stat_contacted'] = Lead.objects.filter(is_contacted=True).count()
        return ctx


class SuperAdminLeadDetailView(SuperuserRequiredMixin, DetailView):
    model = Lead
    template_name = 'balebot/superadmin/lead_detail.html'
    context_object_name = 'lead'


class SuperAdminLeadToggleContactedView(SuperuserRequiredMixin, View):
    def post(self, request, pk):
        lead = get_object_or_404(Lead, pk=pk)
        lead.is_contacted = not lead.is_contacted
        lead.save(update_fields=['is_contacted'])
        if lead.is_contacted:
            messages.success(request, f'سرنخ «{lead.name}» به‌عنوان تماس‌گرفته‌شده علامت خورد.')
        else:
            messages.info(request, f'وضعیت تماس سرنخ «{lead.name}» به «در انتظار» برگشت.')
        next_url = request.POST.get('next') or reverse('superadmin_lead_detail', kwargs={'pk': pk})
        return redirect(next_url)


class SuperAdminPlanListView(SuperuserRequiredMixin, ListView):
    model = SubscriptionPlan
    template_name = 'balebot/superadmin/plan_list.html'
    context_object_name = 'plans'
    paginate_by = 20

    def get_queryset(self):
        return SubscriptionPlan.objects.all()


class SuperAdminPlanCreateView(SuperuserRequiredMixin, FormView):
    form_class = SubscriptionPlanForm
    template_name = 'balebot/superadmin/plan_form.html'
    success_url = reverse_lazy('superadmin_plan_list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['form_title'] = 'پلن جدید'
        ctx['is_create'] = True
        return ctx

    def form_valid(self, form):
        form.save()
        messages.success(self.request, f'پلن «{form.instance.name}» ایجاد شد.')
        return super().form_valid(form)


class SuperAdminPlanUpdateView(SuperuserRequiredMixin, FormView):
    form_class = SubscriptionPlanForm
    template_name = 'balebot/superadmin/plan_form.html'
    success_url = reverse_lazy('superadmin_plan_list')

    def dispatch(self, request, *args, **kwargs):
        self.plan = get_object_or_404(SubscriptionPlan, pk=kwargs['pk'])
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['instance'] = self.plan
        return kwargs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['form_title'] = f'ویرایش پلن «{self.plan.name}»'
        ctx['is_create'] = False
        ctx['plan'] = self.plan
        return ctx

    def form_valid(self, form):
        form.save()
        messages.success(self.request, f'پلن «{form.instance.name}» به‌روزرسانی شد.')
        return super().form_valid(form)


class SuperAdminPlanDeleteView(SuperuserRequiredMixin, View):
    def post(self, request, pk):
        plan = get_object_or_404(SubscriptionPlan, pk=pk)
        name = plan.name
        plan.delete()
        messages.success(request, f'پلن «{name}» حذف شد.')
        return redirect('superadmin_plan_list')


class SuperAdminLandingSettingsView(SuperuserRequiredMixin, FormView):
    form_class = LandingSettingsForm
    template_name = 'balebot/superadmin/landing_settings.html'
    success_url = reverse_lazy('superadmin_landing_settings')

    def get_object(self):
        return LandingSettings.get_solo()

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['instance'] = self.get_object()
        return kwargs

    def form_valid(self, form):
        form.save()
        messages.success(self.request, 'تنظیمات لندینگ ذخیره شد.')
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['settings_obj'] = self.get_object()
        ctx['active_plans'] = SubscriptionPlan.objects.filter(is_active=True).count()
        return ctx


class SuperAdminBrandSettingsView(SuperuserRequiredMixin, FormView):
    form_class = BrandSettingsForm
    template_name = 'balebot/superadmin/brand_settings.html'
    success_url = reverse_lazy('superadmin_brand_settings')

    def get_object(self):
        return LandingSettings.get_solo()

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['instance'] = self.get_object()
        return kwargs

    def form_valid(self, form):
        form.save()
        messages.success(self.request, 'تنظیمات برند ذخیره شد.')
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['settings_obj'] = self.get_object()
        from landing.services.brand_assets import get_brand_context
        ctx.update(get_brand_context(self.get_object()))
        return ctx


class SuperAdminBusinessCategoryListView(SuperuserRequiredMixin, ListView):
    model = BusinessCategory
    template_name = 'balebot/superadmin/business_category_list.html'
    context_object_name = 'categories'
    paginate_by = 30

    def get_queryset(self):
        return BusinessCategory.objects.all()


class SuperAdminBusinessCategoryCreateView(SuperuserRequiredMixin, FormView):
    form_class = BusinessCategoryForm
    template_name = 'balebot/superadmin/business_category_form.html'
    success_url = reverse_lazy('superadmin_business_category_list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['form_title'] = 'صنف جدید'
        ctx['is_create'] = True
        return ctx

    def form_valid(self, form):
        form.save()
        messages.success(self.request, f'صنف «{form.instance.name}» ایجاد شد.')
        return super().form_valid(form)


class SuperAdminBusinessCategoryUpdateView(SuperuserRequiredMixin, FormView):
    form_class = BusinessCategoryForm
    template_name = 'balebot/superadmin/business_category_form.html'
    success_url = reverse_lazy('superadmin_business_category_list')

    def dispatch(self, request, *args, **kwargs):
        self.category = get_object_or_404(BusinessCategory, pk=kwargs['pk'])
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['instance'] = self.category
        return kwargs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['form_title'] = f'ویرایش صنف «{self.category.name}»'
        ctx['is_create'] = False
        ctx['category'] = self.category
        return ctx

    def form_valid(self, form):
        form.save()
        messages.success(self.request, f'صنف «{form.instance.name}» به‌روزرسانی شد.')
        return super().form_valid(form)


class SuperAdminBusinessCategoryDeleteView(SuperuserRequiredMixin, View):
    def post(self, request, pk):
        category = get_object_or_404(BusinessCategory, pk=pk)
        if category.is_other:
            messages.error(request, 'گزینه «سایر» قابل حذف نیست؛ فقط می‌توانید آن را ویرایش کنید.')
            return redirect('superadmin_business_category_list')
        name = category.name
        category.delete()
        messages.success(request, f'صنف «{name}» حذف شد.')
        return redirect('superadmin_business_category_list')
