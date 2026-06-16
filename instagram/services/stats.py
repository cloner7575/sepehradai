from django.db.models import Count

from instagram.models import ActivityDomain, ExtractedPhone, ExtractionJob


def workspace_instagram_stats(workspace) -> dict:
    jobs = ExtractionJob.objects.filter(workspace=workspace)
    return {
        'job_total': jobs.count(),
        'job_completed': jobs.filter(status=ExtractionJob.Status.COMPLETED).count(),
        'job_running': jobs.filter(status=ExtractionJob.Status.RUNNING).count(),
        'phone_total': ExtractedPhone.objects.filter(workspace=workspace).count(),
        'domain_active': ActivityDomain.objects.filter(workspace=workspace, is_active=True).count(),
        'domain_total': ActivityDomain.objects.filter(workspace=workspace).count(),
    }
