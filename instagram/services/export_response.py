from django.http import HttpResponse

from instagram.services.export import (
    JOB_PHONE_EXPORT_HEADERS,
    PHONE_EXPORT_HEADERS,
    build_phones_xlsx,
)


def phone_export_rows(qs, *, include_job_id: bool = True) -> list[tuple]:
    rows = []
    for phone in qs.order_by('phone_number'):
        row = (
            phone.phone_number,
            phone.activity_domain_label,
            phone.created_at.strftime('%Y-%m-%d %H:%M:%S'),
        )
        if include_job_id:
            row = (*row, phone.job_id)
        rows.append(row)
    return rows


def phone_export_response(
    *,
    rows: list[tuple],
    filename_base: str,
    fmt: str,
    headers: tuple[str, ...],
) -> HttpResponse:
    if fmt == 'xlsx':
        content = build_phones_xlsx(headers, rows)
        response = HttpResponse(
            content,
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )
        response['Content-Disposition'] = f'attachment; filename="{filename_base}.xlsx"'
        return response

    import csv
    from io import StringIO

    buffer = StringIO()
    writer = csv.writer(buffer)
    writer.writerow(headers)
    writer.writerows(rows)
    response = HttpResponse(
        '\ufeff' + buffer.getvalue(),
        content_type='text/csv; charset=utf-8-sig',
    )
    response['Content-Disposition'] = f'attachment; filename="{filename_base}.csv"'
    return response
