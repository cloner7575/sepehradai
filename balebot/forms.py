import json

from django import forms

from balebot.models import BotSettings, Campaign
from balebot.services.jalali_datetime import aware_to_jalali_parts, parse_jalali_date_time
from balebot.services.keyboard_layout import (
    keyboard_has_any_button,
    normalize_to_sections,
    sanitize_keyboard_for_storage,
    sanitize_start_keyboard_for_storage,
)


class BotSettingsForm(forms.ModelForm):
    start_inline_keyboard = forms.CharField(
        required=False,
        label='',
        widget=forms.HiddenInput(attrs={'id': 'id_start_inline_keyboard'}),
    )

    class Meta:
        model = BotSettings
        fields = [
            'panel_brand_title',
            'panel_brand_subtitle',
            'welcome_message',
            'contact_button_label',
            'contact_prompt_message',
            'registration_success_message',
            'unsubscribe_message',
            'callback_ack_message',
            'help_message',
            'start_inline_keyboard',
            'collect_contact_on_start',
            'enable_help_command',
            'enable_stop_command',
        ]
        widgets = {
            'panel_brand_title': forms.TextInput(
                attrs={'class': 'form-control panel-input'},
            ),
            'panel_brand_subtitle': forms.TextInput(
                attrs={'class': 'form-control panel-input'},
            ),
            'welcome_message': forms.Textarea(
                attrs={'class': 'form-control panel-input', 'rows': 4},
            ),
            'contact_button_label': forms.TextInput(
                attrs={'class': 'form-control panel-input'},
            ),
            'contact_prompt_message': forms.Textarea(
                attrs={
                    'class': 'form-control panel-input',
                    'rows': 2,
                    'placeholder': 'فقط وقتی هم اینلاین و هم تماس فعال است — پیام دوم قبل از کیبورد تماس',
                },
            ),
            'registration_success_message': forms.Textarea(
                attrs={'class': 'form-control panel-input', 'rows': 4},
            ),
            'unsubscribe_message': forms.Textarea(
                attrs={'class': 'form-control panel-input', 'rows': 3},
            ),
            'callback_ack_message': forms.TextInput(
                attrs={'class': 'form-control panel-input'},
            ),
            'help_message': forms.Textarea(
                attrs={'class': 'form-control panel-input', 'rows': 3},
            ),
            'collect_contact_on_start': forms.CheckboxInput(
                attrs={'class': 'form-check-input', 'role': 'switch'},
            ),
            'enable_help_command': forms.CheckboxInput(
                attrs={'class': 'form-check-input', 'role': 'switch'},
            ),
            'enable_stop_command': forms.CheckboxInput(
                attrs={'class': 'form-check-input', 'role': 'switch'},
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        raw = getattr(self.instance, 'start_inline_keyboard', None)
        norm = sanitize_start_keyboard_for_storage(normalize_to_sections(raw))
        self.fields['start_inline_keyboard'].initial = json.dumps(norm, ensure_ascii=False)

    def clean_start_inline_keyboard(self):
        raw = self.cleaned_data.get('start_inline_keyboard')
        if raw is None or (isinstance(raw, str) and not raw.strip()):
            return sanitize_start_keyboard_for_storage(None)
        try:
            data = json.loads(raw) if isinstance(raw, str) else raw
        except json.JSONDecodeError as e:
            raise forms.ValidationError(f'دادهٔ نامعتبر: {e}') from e
        return sanitize_start_keyboard_for_storage(data)

    def clean(self):
        cleaned = super().clean()
        if cleaned.get('collect_contact_on_start') and not (
            cleaned.get('welcome_message') or ''
        ).strip():
            raise forms.ValidationError(
                'وقتی دکمهٔ تماس فعال است، پیام خوش‌آمد نباید خالی باشد.'
            )
        if cleaned.get('enable_help_command') and not (
            cleaned.get('help_message') or ''
        ).strip():
            raise forms.ValidationError(
                'وقتی /help فعال است، متن راهنما را پر کنید.'
            )
        return cleaned


class CampaignForm(forms.ModelForm):
    inline_keyboard = forms.CharField(
        required=False,
        label='',
        widget=forms.HiddenInput(attrs={'id': 'id_inline_keyboard'}),
    )
    jalali_scheduled_date = forms.CharField(
        required=False,
        label='تاریخ شمسی ارسال',
        help_text='مثلاً ۱۴۰۳/۰۸/۱۵ یا ۱۴۰۳-۸-۱۵ (فقط برای کمپین زمان‌بندی‌شده).',
        widget=forms.TextInput(
            attrs={
                'class': 'form-control panel-input',
                'placeholder': '۱۴۰۳/۰۸/۱۵',
                'dir': 'ltr',
                'autocomplete': 'off',
                'data-scheduled-field': 'date',
            },
        ),
    )
    jalali_scheduled_time = forms.CharField(
        required=False,
        label='ساعت ارسال',
        help_text='به وقت ایران (منطقهٔ زمانی سرور). مثلاً ۱۴:۳۰.',
        widget=forms.TextInput(
            attrs={
                'class': 'form-control panel-input',
                'placeholder': '۱۴:۳۰',
                'dir': 'ltr',
                'autocomplete': 'off',
                'data-scheduled-field': 'time',
            },
        ),
    )

    class Meta:
        model = Campaign
        fields = [
            'title',
            'schedule_kind',
            'content_type',
            'body',
            'media',
            'inline_keyboard',
        ]
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control panel-input'}),
            'schedule_kind': forms.Select(attrs={'class': 'form-select panel-input'}),
            'content_type': forms.Select(attrs={'class': 'form-select panel-input'}),
            'body': forms.Textarea(attrs={'class': 'form-control panel-input', 'rows': 5}),
            'media': forms.ClearableFileInput(attrs={'class': 'form-control panel-input'}),
        }

    field_order = [
        'title',
        'schedule_kind',
        'jalali_scheduled_date',
        'jalali_scheduled_time',
        'content_type',
        'body',
        'media',
        'inline_keyboard',
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        raw = self.instance.inline_keyboard if self.instance.pk else None
        norm = normalize_to_sections(raw)
        self.fields['inline_keyboard'].initial = json.dumps(norm, ensure_ascii=False)

        # Preserve field order: jalali fields sit after schedule_kind in Meta.fields
        if self.instance.pk and self.instance.schedule_kind == Campaign.ScheduleKind.SCHEDULED:
            if self.instance.scheduled_at:
                dpart, tpart = aware_to_jalali_parts(self.instance.scheduled_at)
                self.fields['jalali_scheduled_date'].initial = dpart
                self.fields['jalali_scheduled_time'].initial = tpart

    def clean_inline_keyboard(self):
        raw = self.cleaned_data.get('inline_keyboard')
        if raw is None or (isinstance(raw, str) and not raw.strip()):
            return sanitize_keyboard_for_storage(None)
        try:
            data = json.loads(raw) if isinstance(raw, str) else raw
        except json.JSONDecodeError as e:
            raise forms.ValidationError(f'دادهٔ نامعتبر: {e}') from e
        return sanitize_keyboard_for_storage(data)

    def clean(self):
        cleaned = super().clean()
        ct = cleaned.get('content_type')
        media = cleaned.get('media')
        has_media = bool(media) or bool(getattr(self.instance, 'media', None) and self.instance.media)

        if ct in (
            Campaign.ContentType.PHOTO,
            Campaign.ContentType.VIDEO,
            Campaign.ContentType.VOICE,
            Campaign.ContentType.DOCUMENT,
        ):
            if not has_media:
                raise forms.ValidationError('برای این نوع محتوا بارگذاری فایل الزامی است.')

        kb = cleaned.get('inline_keyboard')
        if ct == Campaign.ContentType.TEXT_BUTTONS:
            if not keyboard_has_any_button(kb):
                raise forms.ValidationError(
                    'برای «متن + دکمه» حداقل یک دکمه در سازندهٔ صفحه‌کلید اضافه کنید.',
                )

        kind = cleaned.get('schedule_kind')
        j_date = (cleaned.get('jalali_scheduled_date') or '').strip()
        j_time = (cleaned.get('jalali_scheduled_time') or '').strip()

        if kind == Campaign.ScheduleKind.SCHEDULED:
            if not j_date or not j_time:
                raise forms.ValidationError(
                    'برای کمپین زمان‌بندی‌شده، تاریخ و ساعت شمسی را پر کنید.',
                )
            try:
                cleaned['resolved_scheduled_at'] = parse_jalali_date_time(j_date, j_time)
            except ValueError as e:
                raise forms.ValidationError(str(e)) from e
        else:
            cleaned['resolved_scheduled_at'] = None

        return cleaned

    def save(self, commit=True):
        obj = super().save(commit=False)
        obj.scheduled_at = self.cleaned_data['resolved_scheduled_at']
        if commit:
            obj.save()
            self._save_m2m()
        return obj
