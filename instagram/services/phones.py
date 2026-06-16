import re

from django.db import transaction
from django.db.models import F
from django.utils import timezone

from instagram.models import ExtractedPhone, ExtractionJob

IRAN_MOBILE_RE = re.compile(r'^09\d{9}$')


def validate_iran_mobile(phone: str) -> bool:
    return bool(IRAN_MOBILE_RE.match((phone or '').strip()))


def sanitize_source_filename(name: str) -> str:
    from pathlib import Path

    base = Path((name or '').strip()).name
    return base[:255]


@transaction.atomic
def save_phone_for_job(job: ExtractionJob, phone: str) -> tuple[ExtractedPhone | None, bool]:
    phone = (phone or '').strip()
    if not validate_iran_mobile(phone):
        return None, False

    phone_obj, created = ExtractedPhone.objects.get_or_create(
        job=job,
        phone_number=phone,
        defaults={
            'workspace': job.workspace,
            'activity_domain_label': job.domain_label,
        },
    )
    if created:
        ExtractionJob.objects.filter(pk=job.pk).update(phone_count=F('phone_count') + 1)
        job.refresh_from_db(fields=['phone_count'])
    return phone_obj, created


@transaction.atomic
def finish_job(
    job: ExtractionJob,
    *,
    json_files_scanned: int = 0,
    error: str = '',
) -> ExtractionJob:
    job.json_files_scanned = max(0, int(json_files_scanned))
    job.completed_at = timezone.now()
    if error.strip():
        job.status = ExtractionJob.Status.FAILED
        job.error_message = error.strip()[:2000]
    else:
        job.status = ExtractionJob.Status.COMPLETED
        job.error_message = ''
    job.save(
        update_fields=[
            'json_files_scanned',
            'completed_at',
            'status',
            'error_message',
        ],
    )
    return job
