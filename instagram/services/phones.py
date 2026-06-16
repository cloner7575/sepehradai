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


BATCH_PHONE_MAX = 100


@transaction.atomic
def save_phones_batch_for_job(job: ExtractionJob, phones: list) -> dict:
    valid: list[str] = []
    seen: set[str] = set()
    for raw in phones:
        phone = (raw or '').strip()
        if not validate_iran_mobile(phone) or phone in seen:
            continue
        seen.add(phone)
        valid.append(phone)

    if not valid:
        job.refresh_from_db(fields=['phone_count'])
        return {'saved_count': 0, 'saved_phones': [], 'phone_count': job.phone_count}

    existing = set(
        ExtractedPhone.objects.filter(job=job, phone_number__in=valid).values_list(
            'phone_number',
            flat=True,
        ),
    )
    to_create = [p for p in valid if p not in existing]

    if to_create:
        ExtractedPhone.objects.bulk_create(
            [
                ExtractedPhone(
                    job=job,
                    workspace=job.workspace,
                    phone_number=phone,
                    activity_domain_label=job.domain_label,
                )
                for phone in to_create
            ],
        )
        ExtractionJob.objects.filter(pk=job.pk).update(phone_count=F('phone_count') + len(to_create))

    job.refresh_from_db(fields=['phone_count'])
    return {
        'saved_count': len(to_create),
        'saved_phones': to_create,
        'phone_count': job.phone_count,
    }


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
