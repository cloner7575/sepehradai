import json

from django.contrib import messages
from django.db.models import Count
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views import View
from django.views.generic import DetailView, ListView, TemplateView

from django.conf import settings
from balebot.views_panel_users import SuperuserRequiredMixin
from instagram.forms import ActivityDomainForm
from instagram.mixins import InstagramPanelMixin
from instagram.models import ActivityDomain, ExtractedPhone, ExtractionJob
from instagram.services.phones import (
    finish_job,
    sanitize_source_filename,
    save_phone_for_job,
    validate_iran_mobile,
)
from instagram.services.export import JOB_PHONE_EXPORT_HEADERS, PHONE_EXPORT_HEADERS
from instagram.services.export_response import phone_export_response, phone_export_rows
from instagram.services.phone_list import domain_labels_for_workspace, phones_queryset_for_request
from instagram.services.stats import workspace_instagram_stats
from instagram.video_embed import video_url_to_embed


def _parse_json_body(request) -> dict:
    if not request.body:
        return {}
    try:
        return json.loads(request.body.decode('utf-8'))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return {}


def _json_error(message: str, status: int = 400) -> JsonResponse:
    return JsonResponse({'ok': False, 'error': message}, status=status)


def _tutorial_video_embed_url() -> str:
    return video_url_to_embed(getattr(settings, 'INSTAGRAM_BACKUP_TUTORIAL_VIDEO_URL', ''))


class InstagramDashboardView(InstagramPanelMixin, TemplateView):
    template_name = 'instagram/dashboard.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        workspace = self.get_workspace()
        stats = workspace_instagram_stats(workspace)
        ctx.update(stats)
        ctx['recent_jobs'] = (
            ExtractionJob.objects.filter(workspace=workspace)
            .select_related('activity_domain', 'created_by')[:8]
        )
        ctx['phones_by_domain'] = (
            ExtractedPhone.objects.filter(workspace=workspace)
            .values('activity_domain_label')
            .annotate(total=Count('id'))
            .order_by('-total')[:6]
        )
        return ctx


class BackupGuideView(InstagramPanelMixin, TemplateView):
    template_name = 'instagram/backup_guide.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['tutorial_video_embed_url'] = _tutorial_video_embed_url()
        return ctx


class ExtractionHistoryView(InstagramPanelMixin, ListView):
    model = ExtractionJob
    template_name = 'instagram/history.html'
    context_object_name = 'jobs'
    paginate_by = 20

    def get_queryset(self):
        return (
            ExtractionJob.objects.filter(workspace=self.get_workspace())
            .select_related('activity_domain', 'created_by')
            .order_by('-created_at')
        )


class ExtractedPhoneListView(InstagramPanelMixin, ListView):
    model = ExtractedPhone
    template_name = 'instagram/phone_list.html'
    context_object_name = 'phones'
    paginate_by = 50

    def get_queryset(self):
        return phones_queryset_for_request(self.get_workspace(), self.request)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        workspace = self.get_workspace()
        ctx['domain_labels'] = domain_labels_for_workspace(workspace)
        ctx['filter_q'] = (self.request.GET.get('q') or '').strip()
        ctx['filter_domain'] = (self.request.GET.get('domain') or '').strip()
        ctx['filter_job'] = (self.request.GET.get('job') or '').strip()
        ctx['filter_unique'] = self.request.GET.get('unique') == '1'
        ctx['phone_total'] = ExtractedPhone.objects.filter(workspace=workspace).count()
        return ctx


class ExtractedPhoneExportView(InstagramPanelMixin, View):
    http_method_names = ['get']

    def get(self, request, *args, **kwargs):
        qs = phones_queryset_for_request(self.get_workspace(), request)
        fmt = (request.GET.get('format') or 'csv').lower()
        if fmt not in ('csv', 'xlsx'):
            fmt = 'csv'
        rows = phone_export_rows(qs, include_job_id=True)
        return phone_export_response(
            rows=rows,
            filename_base='instagram-phones',
            fmt=fmt,
            headers=PHONE_EXPORT_HEADERS,
        )


class PhoneExtractorView(InstagramPanelMixin, TemplateView):
    template_name = 'instagram/phone_extractor.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        workspace = self.get_workspace()
        ctx['activity_domains'] = ActivityDomain.objects.filter(
            workspace=workspace,
            is_active=True,
        )
        ctx['has_domains'] = ctx['activity_domains'].exists()
        return ctx


class ActivityDomainListView(
    InstagramPanelMixin,
    SuperuserRequiredMixin,
    TemplateView,
):
    template_name = 'instagram/activity_domain_list.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['domains'] = ActivityDomain.objects.filter(workspace=self.get_workspace())
        ctx['form'] = ActivityDomainForm()
        return ctx

    def post(self, request, *args, **kwargs):
        workspace = self.get_workspace()
        form = ActivityDomainForm(request.POST)
        if form.is_valid():
            domain = form.save(commit=False)
            domain.workspace = workspace
            domain.save()
            messages.success(request, 'حوزه فعالیت اضافه شد.')
        else:
            messages.error(request, 'نام حوزه معتبر نیست.')
        return redirect('instagram:activity_domain_list')


class ActivityDomainToggleView(InstagramPanelMixin, SuperuserRequiredMixin, View):
    http_method_names = ['post']

    def post(self, request, pk, *args, **kwargs):
        domain = get_object_or_404(
            ActivityDomain,
            pk=pk,
            workspace=self.get_workspace(),
        )
        domain.is_active = not domain.is_active
        domain.save(update_fields=['is_active'])
        messages.success(request, 'وضعیت حوزه به‌روزرسانی شد.')
        return redirect('instagram:activity_domain_list')


class ExtractionStartView(InstagramPanelMixin, View):
    http_method_names = ['post']

    def post(self, request, *args, **kwargs):
        data = _parse_json_body(request)
        workspace = self.get_workspace()

        domain_id_raw = data.get('activity_domain_id')
        custom = (data.get('activity_domain_custom') or '').strip()[:120]
        source_filename = sanitize_source_filename(data.get('source_filename') or '')

        activity_domain = None
        is_other = domain_id_raw in (None, '', 'other', 0, '0')

        if is_other:
            if not request.user.is_superuser:
                return _json_error('فقط مدیر سیستم می‌تواند حوزه سفارشی تعریف کند.')
            if not custom:
                return _json_error('برای گزینه «سایر» نام حوزه فعالیت الزامی است.')
        else:
            try:
                domain_pk = int(domain_id_raw)
            except (TypeError, ValueError):
                return _json_error('حوزه فعالیت نامعتبر است.')
            activity_domain = ActivityDomain.objects.filter(
                pk=domain_pk,
                workspace=workspace,
                is_active=True,
            ).first()
            if not activity_domain:
                return _json_error('حوزه فعالیت یافت نشد.')
            custom = ''

        job = ExtractionJob.objects.create(
            workspace=workspace,
            created_by=request.user,
            activity_domain=activity_domain,
            activity_domain_custom=custom,
            source_filename=source_filename,
            status=ExtractionJob.Status.RUNNING,
        )
        return JsonResponse({'ok': True, 'job_id': job.pk})


class ExtractionSavePhoneView(InstagramPanelMixin, View):
    http_method_names = ['post']

    def post(self, request, *args, **kwargs):
        data = _parse_json_body(request)
        try:
            job_id = int(data.get('job_id'))
        except (TypeError, ValueError):
            return _json_error('شناسه عملیات نامعتبر است.')

        phone = (data.get('phone') or '').strip()
        if not validate_iran_mobile(phone):
            return _json_error('فرمت شماره موبایل نامعتبر است.')

        job = get_object_or_404(
            ExtractionJob,
            pk=job_id,
            workspace=self.get_workspace(),
        )
        if job.status != ExtractionJob.Status.RUNNING:
            return _json_error('این عملیات استخراج دیگر فعال نیست.', status=409)

        _, created = save_phone_for_job(job, phone)
        job.refresh_from_db(fields=['phone_count'])
        return JsonResponse(
            {
                'ok': True,
                'saved': created,
                'phone_count': job.phone_count,
            },
        )


class ExtractionFinishView(InstagramPanelMixin, View):
    http_method_names = ['post']

    def post(self, request, *args, **kwargs):
        data = _parse_json_body(request)
        try:
            job_id = int(data.get('job_id'))
        except (TypeError, ValueError):
            return _json_error('شناسه عملیات نامعتبر است.')

        job = get_object_or_404(
            ExtractionJob,
            pk=job_id,
            workspace=self.get_workspace(),
        )
        if job.status != ExtractionJob.Status.RUNNING:
            return JsonResponse(
                {
                    'ok': True,
                    'redirect_url': reverse('instagram:extraction_detail', kwargs={'pk': job.pk}),
                },
            )

        try:
            json_files_scanned = int(data.get('json_files_scanned') or 0)
        except (TypeError, ValueError):
            json_files_scanned = 0

        error = (data.get('error') or '').strip()
        finish_job(job, json_files_scanned=json_files_scanned, error=error)
        phone_list_url = reverse('instagram:phone_list') + f'?job={job.pk}'
        return JsonResponse(
            {
                'ok': True,
                'redirect_url': phone_list_url,
            },
        )


class ExtractionDetailView(InstagramPanelMixin, DetailView):
    model = ExtractionJob
    template_name = 'instagram/extraction_detail.html'
    context_object_name = 'job'

    def get_queryset(self):
        return ExtractionJob.objects.filter(workspace=self.get_workspace()).select_related(
            'activity_domain',
            'created_by',
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['phone_count'] = ExtractedPhone.objects.filter(job=self.object).count()
        return ctx


class ExtractionExportView(InstagramPanelMixin, View):
    http_method_names = ['get']

    def get(self, request, pk, *args, **kwargs):
        job = get_object_or_404(
            ExtractionJob,
            pk=pk,
            workspace=self.get_workspace(),
        )
        fmt = (request.GET.get('format') or 'csv').lower()
        if fmt not in ('csv', 'xlsx'):
            fmt = 'csv'
        qs = ExtractedPhone.objects.filter(job=job)
        rows = phone_export_rows(qs, include_job_id=False)
        return phone_export_response(
            rows=rows,
            filename_base=f'instagram-phones-{job.pk}',
            fmt=fmt,
            headers=JOB_PHONE_EXPORT_HEADERS,
        )
