from django.contrib import messages
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_http_methods

from landing.forms import LeadForm
from landing.services.notify import notify_lead_via_bale
from landing.services.public_content import get_public_landing_context


@require_http_methods(['GET'])
def landing_index(request: HttpRequest) -> HttpResponse:
    if request.user.is_authenticated:
        return redirect('panel_dashboard')
    ctx = get_public_landing_context()
    ctx['form'] = LeadForm()
    return render(request, 'landing/index.html', ctx)



@require_http_methods(['POST'])
def submit_lead(request: HttpRequest) -> HttpResponse:
    if request.POST.get('website', '').strip():
        return redirect('landing_index')

    form = LeadForm(request.POST)
    if not form.is_valid():
        ctx = get_public_landing_context()
        ctx['form'] = form
        ctx['form_errors'] = True
        return render(request, 'landing/index.html', ctx, status=400)

    lead = form.save(commit=False)
    lead.source = 'landing'
    lead.save()
    notify_lead_via_bale(lead)
    messages.success(
        request,
        'درخواستت ثبت شد! به‌زودی باهات تماس می‌گیریم و دمو رایگان می‌فرستیم.',
    )
    return redirect(reverse('landing_index') + '#cta')
