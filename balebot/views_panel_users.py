from datetime import timedelta

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Prefetch, Q
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import FormView, ListView

from balebot.forms_panel_users import PanelUserCreateForm, PanelUserUpdateForm
from balebot.models import BotSettings, Workspace
from balebot.services.jalali_datetime import aware_to_jalali_parts
from balebot.workspace import create_panel_user, ensure_bot_settings_for_workspace

User = get_user_model()


class SuperuserRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_superuser


def _panel_user_base_queryset():
    return (
        User.objects.filter(is_staff=True, is_superuser=False)
        .select_related('workspace')
        .prefetch_related(
            Prefetch(
                'workspace__bot_settings',
                queryset=BotSettings.objects.order_by('platform'),
            ),
        )
    )


def _panel_user_stats(users):
    total = len(users)
    active = 0
    inactive = 0
    sub_expired = 0
    sub_expiring = 0
    for user in users:
        try:
            ws = user.workspace
        except Workspace.DoesNotExist:
            inactive += 1
            continue
        if user.is_active and ws.is_active:
            active += 1
        else:
            inactive += 1
        status = ws.subscription_status()
        if status == 'expired':
            sub_expired += 1
        elif status == 'expiring_soon':
            sub_expiring += 1
    return {
        'user_stat_total': total,
        'user_stat_active': active,
        'user_stat_inactive': inactive,
        'user_stat_sub_expired': sub_expired,
        'user_stat_sub_expiring': sub_expiring,
    }


class PanelUserListView(SuperuserRequiredMixin, ListView):
    template_name = 'balebot/panel_user_list.html'
    context_object_name = 'panel_users'
    paginate_by = 30

    def get_queryset(self):
        qs = _panel_user_base_queryset()
        q = (self.request.GET.get('q') or '').strip()
        if q:
            qs = qs.filter(
                Q(username__icontains=q)
                | Q(email__icontains=q)
                | Q(workspace__name__icontains=q),
            )
        status = (self.request.GET.get('status') or '').strip()
        now = timezone.now()
        soon = now + timedelta(days=7)
        if status == 'active':
            qs = qs.filter(is_active=True, workspace__is_active=True)
        elif status == 'inactive':
            qs = qs.filter(Q(is_active=False) | Q(workspace__is_active=False))
        elif status == 'sub_expired':
            qs = qs.filter(
                workspace__subscription_expires_at__isnull=False,
                workspace__subscription_expires_at__lte=now,
            )
        elif status == 'sub_expiring':
            qs = qs.filter(
                workspace__subscription_expires_at__gt=now,
                workspace__subscription_expires_at__lte=soon,
                workspace__is_active=True,
            )
        elif status == 'sub_unlimited':
            qs = qs.filter(workspace__subscription_expires_at__isnull=True)
        return qs.order_by('username')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        all_users = list(_panel_user_base_queryset().order_by('username'))
        ctx.update(_panel_user_stats(all_users))
        ctx['search_q'] = (self.request.GET.get('q') or '').strip()
        ctx['filter_status'] = (self.request.GET.get('status') or '').strip()
        return ctx


class PanelUserCreateView(SuperuserRequiredMixin, FormView):
    template_name = 'balebot/panel_user_form.html'
    form_class = PanelUserCreateForm
    success_url = reverse_lazy('panel_user_list')

    def get_initial(self):
        d, t = aware_to_jalali_parts(timezone.now() + timedelta(days=30))
        return {
            'jalali_subscription_expires_date': d,
            'jalali_subscription_expires_time': t,
        }

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['form_title'] = 'کاربر پنل جدید'
        ctx['is_create'] = True
        return ctx

    def form_valid(self, form):
        user, workspace = create_panel_user(
            username=form.cleaned_data['username'],
            password=form.cleaned_data['password'],
            workspace_name=form.cleaned_data['workspace_name'],
            email=form.cleaned_data.get('email') or '',
            allow_bale=form.cleaned_data['allow_bale'],
            allow_telegram=form.cleaned_data['allow_telegram'],
            allow_bale_miniapp=form.cleaned_data['allow_bale_miniapp'],
            allow_telegram_miniapp=form.cleaned_data['allow_telegram_miniapp'],
            allow_instagram=form.cleaned_data['allow_instagram'],
            subscription_expires_at=form.cleaned_data.get('subscription_expires_at'),
        )
        messages.success(
            self.request,
            f'کاربر «{user.username}» با پنل «{workspace.name}» ساخته شد.',
        )
        return redirect('panel_user_edit', pk=user.pk)


class PanelUserUpdateView(SuperuserRequiredMixin, FormView):
    template_name = 'balebot/panel_user_form.html'
    form_class = PanelUserUpdateForm

    def dispatch(self, request, *args, **kwargs):
        self.panel_user = get_object_or_404(
            User,
            pk=kwargs['pk'],
            is_staff=True,
            is_superuser=False,
        )
        try:
            self.workspace = self.panel_user.workspace
        except Workspace.DoesNotExist:
            self.workspace = None
        return super().dispatch(request, *args, **kwargs)

    def get_initial(self):
        ws = self.workspace
        sub_date, sub_time = aware_to_jalali_parts(ws.subscription_expires_at if ws else None)
        return {
            'workspace_name': ws.name if ws else '',
            'email': self.panel_user.email,
            'is_active': self.panel_user.is_active,
            'workspace_active': ws.is_active if ws else True,
            'allow_bale': ws.allow_bale if ws else True,
            'allow_telegram': ws.allow_telegram if ws else True,
            'allow_bale_miniapp': ws.allow_bale_miniapp if ws else False,
            'allow_telegram_miniapp': ws.allow_telegram_miniapp if ws else False,
            'allow_instagram': ws.allow_instagram if ws else False,
            'jalali_subscription_expires_date': sub_date,
            'jalali_subscription_expires_time': sub_time,
        }

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['form_title'] = f'ویرایش کاربر: {self.panel_user.username}'
        ctx['is_create'] = False
        ctx['panel_user'] = self.panel_user
        ctx['workspace'] = self.workspace
        ctx['bot_settings_list'] = []
        if self.workspace:
            allowed = self.workspace.allowed_platforms()
            ctx['bot_settings_list'] = list(
                BotSettings.objects.filter(
                    workspace=self.workspace,
                    platform__in=allowed,
                ).order_by('platform'),
            )
        return ctx

    def form_valid(self, form):
        self.panel_user.email = form.cleaned_data.get('email') or ''
        self.panel_user.is_active = form.cleaned_data['is_active']
        password = (form.cleaned_data.get('password') or '').strip()
        if password:
            self.panel_user.set_password(password)
        self.panel_user.save()

        if self.workspace:
            self.workspace.name = form.cleaned_data['workspace_name'].strip()
            self.workspace.is_active = form.cleaned_data['workspace_active']
            self.workspace.allow_bale = form.cleaned_data['allow_bale']
            self.workspace.allow_telegram = form.cleaned_data['allow_telegram']
            self.workspace.allow_bale_miniapp = form.cleaned_data['allow_bale_miniapp']
            self.workspace.allow_telegram_miniapp = form.cleaned_data['allow_telegram_miniapp']
            self.workspace.allow_instagram = form.cleaned_data['allow_instagram']
            self.workspace.subscription_expires_at = form.cleaned_data.get('subscription_expires_at')
            self.workspace.save(update_fields=[
                'name', 'is_active', 'allow_bale', 'allow_telegram',
                'allow_bale_miniapp', 'allow_telegram_miniapp', 'allow_instagram',
                'subscription_expires_at',
            ])
            ensure_bot_settings_for_workspace(self.workspace)
        else:
            ws = Workspace.objects.create(
                name=form.cleaned_data['workspace_name'].strip() or self.panel_user.username,
                owner=self.panel_user,
                is_active=form.cleaned_data['workspace_active'],
                allow_bale=form.cleaned_data['allow_bale'],
                allow_telegram=form.cleaned_data['allow_telegram'],
                allow_bale_miniapp=form.cleaned_data['allow_bale_miniapp'],
                allow_telegram_miniapp=form.cleaned_data['allow_telegram_miniapp'],
                allow_instagram=form.cleaned_data['allow_instagram'],
                subscription_expires_at=form.cleaned_data.get('subscription_expires_at'),
            )
            ensure_bot_settings_for_workspace(ws)
            self.workspace = ws

        messages.success(self.request, 'تغییرات کاربر ذخیره شد.')
        return redirect('panel_user_edit', pk=self.panel_user.pk)

    def get_success_url(self):
        return reverse_lazy('panel_user_edit', kwargs={'pk': self.panel_user.pk})
