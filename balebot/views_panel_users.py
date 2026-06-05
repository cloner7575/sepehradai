from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Prefetch
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views.generic import FormView, ListView

from balebot.forms_panel_users import PanelUserCreateForm, PanelUserUpdateForm
from balebot.models import BotSettings, Workspace
from balebot.workspace import create_panel_user

User = get_user_model()


class SuperuserRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_superuser


class PanelUserListView(SuperuserRequiredMixin, ListView):
    template_name = 'balebot/panel_user_list.html'
    context_object_name = 'panel_users'
    paginate_by = 30

    def get_queryset(self):
        return (
            User.objects.filter(is_staff=True, is_superuser=False)
            .select_related('workspace')
            .prefetch_related(
                Prefetch(
                    'workspace__bot_settings',
                    queryset=BotSettings.objects.order_by('platform'),
                ),
            )
            .order_by('username')
        )


class PanelUserCreateView(SuperuserRequiredMixin, FormView):
    template_name = 'balebot/panel_user_form.html'
    form_class = PanelUserCreateForm
    success_url = reverse_lazy('panel_user_list')

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
        return {
            'workspace_name': ws.name if ws else '',
            'email': self.panel_user.email,
            'is_active': self.panel_user.is_active,
            'workspace_active': ws.is_active if ws else True,
        }

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['form_title'] = f'ویرایش کاربر: {self.panel_user.username}'
        ctx['is_create'] = False
        ctx['panel_user'] = self.panel_user
        ctx['bot_settings_list'] = []
        if self.workspace:
            ctx['bot_settings_list'] = list(
                BotSettings.objects.filter(workspace=self.workspace).order_by('platform'),
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
            self.workspace.save(update_fields=['name', 'is_active'])
        else:
            ws = Workspace.objects.create(
                name=form.cleaned_data['workspace_name'].strip() or self.panel_user.username,
                owner=self.panel_user,
                is_active=form.cleaned_data['workspace_active'],
            )
            BotSettings.ensure_for_workspace(ws)
            self.workspace = ws

        messages.success(self.request, 'تغییرات کاربر ذخیره شد.')
        return redirect('panel_user_edit', pk=self.panel_user.pk)

    def get_success_url(self):
        return reverse_lazy('panel_user_edit', kwargs={'pk': self.panel_user.pk})
