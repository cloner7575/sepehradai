from django.db.models import Max

from instagram.models import ExtractedPhone


def phones_queryset_for_request(workspace, request):
    qs = (
        ExtractedPhone.objects.filter(workspace=workspace)
        .select_related('job')
        .order_by('-created_at')
    )

    q = (request.GET.get('q') or '').strip()
    domain = (request.GET.get('domain') or '').strip()
    job_raw = (request.GET.get('job') or '').strip()

    if q:
        qs = qs.filter(phone_number__icontains=q)
    if domain:
        qs = qs.filter(activity_domain_label=domain)
    if job_raw.isdigit():
        qs = qs.filter(job_id=int(job_raw))

    if request.GET.get('unique') == '1':
        latest_ids = (
            ExtractedPhone.objects.filter(workspace=workspace)
            .values('phone_number')
            .annotate(latest_id=Max('id'))
            .values_list('latest_id', flat=True)
        )
        qs = (
            ExtractedPhone.objects.filter(pk__in=latest_ids)
            .select_related('job')
            .order_by('-created_at')
        )
        if q:
            qs = qs.filter(phone_number__icontains=q)
        if domain:
            qs = qs.filter(activity_domain_label=domain)
        if job_raw.isdigit():
            qs = qs.filter(job_id=int(job_raw))

    return qs


def domain_labels_for_workspace(workspace) -> list[str]:
    return list(
        ExtractedPhone.objects.filter(workspace=workspace)
        .exclude(activity_domain_label='')
        .values_list('activity_domain_label', flat=True)
        .distinct()
        .order_by('activity_domain_label'),
    )
