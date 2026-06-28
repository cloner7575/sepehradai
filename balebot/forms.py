import json

from django import forms
from django.core.files import File
from django.core.files.storage import default_storage

from balebot.models import BotSettings, Campaign, Platform, Tag
from balebot.widgets import PersianClearableFileInput
from balebot.services.jalali_datetime import aware_to_jalali_parts, parse_jalali_date_time

# هم‌نام با مقدار سشن در views_panel (آپلود ویدیو)
_CAMPAIGN_PENDING_MEDIA_SESSION_KEY = 'campaign_pending_media'
from balebot.services.flow_sanitize import empty_start_flow, sanitize_start_flow

_SETTINGS_INPUT_CLASS = 'form-control panel-input'

_CAMPAIGN_PANEL_CONTENT_CHOICES = [
    (Campaign.ContentType.TEXT, 'متن'),
    (Campaign.ContentType.PHOTO, 'عکس'),
    (Campaign.ContentType.VIDEO, 'ویدیو'),
    (Campaign.ContentType.DOCUMENT, 'فایل'),
]

_LEGACY_CAMPAIGN_CONTENT_LABELS = {
    Campaign.ContentType.TEXT_BUTTONS: 'متن + دکمه (قدیمی)',
    Campaign.ContentType.VOICE: 'صدا (قدیمی)',
}


class BotSettingsForm(forms.ModelForm):
    bot_token = forms.CharField(
        required=False,
        label='توکن ربات',
        help_text='از BotFather دریافت کنید. برای حفظ توکن قبلی خالی بگذارید.',
        widget=forms.PasswordInput(
            attrs={
                'class': _SETTINGS_INPUT_CLASS,
                'autocomplete': 'new-password',
                'placeholder': 'توکن جدید (اختیاری)',
            },
        ),
    )

    class Meta:
        model = BotSettings
        fields = [
            'bot_token',
            'is_enabled',
            'panel_brand_title',
            'panel_brand_subtitle',
            'start_message_normal',
            'start_message_contact',
            'contact_button_label',
            'registration_success_message',
            'unsubscribe_message',
            'callback_ack_message',
            'help_message',
            'collect_contact_on_start',
            'enable_help_command',
            'enable_stop_command',
            'enable_support',
            'support_button_label',
            'support_start_prompt_message',
            'support_waiting_message',
        ]
        widgets = {
            'is_enabled': forms.CheckboxInput(
                attrs={'class': 'form-check-input', 'role': 'switch'},
            ),
            'panel_brand_title': forms.TextInput(
                attrs={'class': _SETTINGS_INPUT_CLASS},
            ),
            'panel_brand_subtitle': forms.TextInput(
                attrs={'class': _SETTINGS_INPUT_CLASS},
            ),
            'start_message_normal': forms.Textarea(
                attrs={
                    'class': _SETTINGS_INPUT_CLASS,
                    'rows': 4,
                    'placeholder': 'کاربر ثبت‌نام‌شده یا بدون اجبار تماس',
                },
            ),
            'start_message_contact': forms.Textarea(
                attrs={
                    'class': _SETTINGS_INPUT_CLASS,
                    'rows': 4,
                    'placeholder': 'کاربر بدون شماره وقتی دکمهٔ تماس روشن است',
                },
            ),
            'contact_button_label': forms.TextInput(
                attrs={'class': _SETTINGS_INPUT_CLASS},
            ),
            'registration_success_message': forms.Textarea(
                attrs={'class': _SETTINGS_INPUT_CLASS, 'rows': 4},
            ),
            'unsubscribe_message': forms.Textarea(
                attrs={'class': _SETTINGS_INPUT_CLASS, 'rows': 3},
            ),
            'callback_ack_message': forms.TextInput(
                attrs={'class': _SETTINGS_INPUT_CLASS},
            ),
            'help_message': forms.Textarea(
                attrs={'class': _SETTINGS_INPUT_CLASS, 'rows': 3},
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
            'enable_support': forms.CheckboxInput(
                attrs={'class': 'form-check-input', 'role': 'switch'},
            ),
            'support_button_label': forms.TextInput(
                attrs={'class': _SETTINGS_INPUT_CLASS},
            ),
            'support_start_prompt_message': forms.Textarea(
                attrs={'class': _SETTINGS_INPUT_CLASS, 'rows': 3},
            ),
            'support_waiting_message': forms.Textarea(
                attrs={'class': _SETTINGS_INPUT_CLASS, 'rows': 3},
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._initial_bot_token = ''
        if self.instance and self.instance.pk:
            self._initial_bot_token = (self.instance.bot_token or '').strip()
        if self._initial_bot_token and 'bot_token' in self.fields:
            self.fields['bot_token'].help_text = (
                f'توکن فعلی: {self.instance.masked_bot_token()} — برای تغییر، توکن جدید وارد کنید.'
            )

    def clean_bot_token(self):
        token = (self.cleaned_data.get('bot_token') or '').strip()
        if token:
            return token
        if self._initial_bot_token:
            return self._initial_bot_token
        return ''

    def clean(self):
        cleaned = super().clean()
        if not (cleaned.get('start_message_normal') or '').strip():
            raise forms.ValidationError('پیام /start معمولی را پر کنید.')
        if cleaned.get('collect_contact_on_start') and not (
            cleaned.get('start_message_contact') or ''
        ).strip():
            raise forms.ValidationError(
                'وقتی دریافت شماره بعد از /start روشن است، پیام مخصوص آن را هم پر کنید.'
            )
        if cleaned.get('enable_help_command') and not (
            cleaned.get('help_message') or ''
        ).strip():
            raise forms.ValidationError(
                'وقتی /help فعال است، متن راهنما را پر کنید.'
            )
        if cleaned.get('enable_support'):
            if not (cleaned.get('support_button_label') or '').strip():
                raise forms.ValidationError(
                    'وقتی پشتیبانی فعال است، برچسب دکمهٔ پشتیبانی را پر کنید.'
                )
            if not (cleaned.get('support_start_prompt_message') or '').strip():
                raise forms.ValidationError(
                    'وقتی پشتیبانی فعال است، متن راهنمای شروع پشتیبانی را پر کنید.'
                )
            if not (cleaned.get('support_waiting_message') or '').strip():
                raise forms.ValidationError(
                    'وقتی پشتیبانی فعال است، پیام ثبت درخواست پشتیبانی را پر کنید.'
                )
        return cleaned

    def save(self, commit=True):
        return super().save(commit=commit)


class FlowEngineForm(BotSettingsForm):
    """فیلدهای ساخت جریان /start در صفحهٔ موتور جریان."""

    start_flow = forms.CharField(
        required=False,
        label='',
        widget=forms.HiddenInput(attrs={'id': 'id_start_flow'}),
    )

    class Meta(BotSettingsForm.Meta):
        fields = [
            'start_flow',
            'start_flow_default_text',
            'start_message_normal',
            'collect_contact_on_start',
            'start_message_contact',
            'contact_button_label',
            'registration_success_message',
        ]
        widgets = {
            **BotSettingsForm.Meta.widgets,
            'start_flow_default_text': forms.Textarea(
                attrs={
                    'class': _SETTINGS_INPUT_CLASS,
                    'rows': 2,
                    'placeholder': 'وقتی مسیر دکمه به جایی وصل نیست',
                },
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        raw = getattr(self.instance, 'start_flow', None)
        if raw and isinstance(raw, dict) and raw.get('version') == 2:
            norm = sanitize_start_flow(raw)
        else:
            norm = empty_start_flow()
        dumped = json.dumps(norm, ensure_ascii=False)
        self.initial['start_flow'] = dumped
        self.fields['start_flow'].initial = dumped

    def clean_start_flow(self):
        raw = self.cleaned_data.get('start_flow')
        if raw is None or (isinstance(raw, str) and not raw.strip()):
            return empty_start_flow()
        try:
            data = json.loads(raw) if isinstance(raw, str) else raw
        except json.JSONDecodeError as e:
            raise forms.ValidationError(f'دادهٔ نامعتبر: {e}') from e
        return sanitize_start_flow(data)

    def clean(self):
        cleaned = super(BotSettingsForm, self).clean()
        if not (cleaned.get('start_message_normal') or '').strip():
            raise forms.ValidationError('پیام خوش‌آمد را پر کنید.')
        if cleaned.get('collect_contact_on_start') and not (
            cleaned.get('start_message_contact') or ''
        ).strip():
            raise forms.ValidationError(
                'وقتی دریافت شماره روشن است، پیام مخصوص آن را هم پر کنید.',
            )
        return cleaned


class CampaignForm(forms.ModelForm):
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
    AUDIENCE_ALL = 'all'
    AUDIENCE_TAGS = 'tags'

    audience_mode = forms.ChoiceField(
        choices=[
            (AUDIENCE_ALL, 'ارسال برای همه'),
            (AUDIENCE_TAGS, 'ارسال به دسته‌بندی‌های انتخابی'),
        ],
        label='مخاطبان کمپین',
        initial=AUDIENCE_ALL,
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'}),
    )
    target_tags = forms.ModelMultipleChoiceField(
        required=False,
        queryset=Tag.objects.filter(is_active=True).order_by('name'),
        label='دسته‌بندی‌ها',
        help_text='یک یا چند دسته‌بندی را انتخاب کنید.',
        widget=forms.SelectMultiple(attrs={'class': 'form-select panel-input', 'size': 6}),
    )

    class Meta:
        model = Campaign
        fields = [
            'title',
            'schedule_kind',
            'content_type',
            'target_tags',
            'body',
            'media',
        ]
        labels = {
            'title': 'عنوان کمپین',
            'schedule_kind': 'نوع زمان ارسال',
            'content_type': 'نوع محتوا',
            'body': 'متن پیام',
            'media': 'فایل',
        }
        widgets = {
            'title': forms.TextInput(
                attrs={
                    'class': 'form-control panel-input',
                    'placeholder': 'مثلاً: اطلاع‌رسانی جشنواره بهاره',
                },
            ),
            'schedule_kind': forms.Select(attrs={'class': 'form-select panel-input'}),
            'content_type': forms.Select(attrs={'class': 'form-select panel-input'}),
            'body': forms.Textarea(
                attrs={
                    'class': 'form-control panel-input',
                    'rows': 5,
                    'placeholder': 'متن پیامی که برای مخاطبان ارسال می‌شود…',
                },
            ),
            'media': PersianClearableFileInput(attrs={'class': 'form-control panel-input'}),
        }

    field_order = [
        'title',
        'schedule_kind',
        'jalali_scheduled_date',
        'jalali_scheduled_time',
        'content_type',
        'audience_mode',
        'target_tags',
        'body',
        'media',
    ]

    def __init__(self, *args, request=None, platform=None, workspace=None, **kwargs):
        self.request = request
        self.platform = platform or Platform.BALE
        self.workspace = workspace
        super().__init__(*args, **kwargs)
        tag_filter = {'platform': self.platform, 'is_active': True}
        if self.workspace is not None:
            tag_filter['workspace'] = self.workspace
        self.fields['target_tags'].queryset = Tag.objects.filter(**tag_filter).order_by('name')
        if self.instance.pk and self.instance.target_tags.exists():
            self.initial['audience_mode'] = self.AUDIENCE_TAGS
        else:
            self.initial['audience_mode'] = self.AUDIENCE_ALL

        panel_choices = list(_CAMPAIGN_PANEL_CONTENT_CHOICES)
        if self.instance.pk:
            current = self.instance.content_type
            if current and current not in {value for value, _ in panel_choices}:
                panel_choices = [
                    (current, _LEGACY_CAMPAIGN_CONTENT_LABELS.get(current, current)),
                    *panel_choices,
                ]
        self.fields['content_type'].choices = panel_choices
        if not self.instance.pk and not self.initial.get('content_type'):
            self.initial['content_type'] = Campaign.ContentType.TEXT

        # Preserve field order: jalali fields sit after schedule_kind in Meta.fields
        if self.instance.pk and self.instance.schedule_kind == Campaign.ScheduleKind.SCHEDULED:
            if self.instance.scheduled_at:
                dpart, tpart = aware_to_jalali_parts(self.instance.scheduled_at)
                self.fields['jalali_scheduled_date'].initial = dpart
                self.fields['jalali_scheduled_time'].initial = tpart

        self._discard_stale_pending_media_session()

    def _discard_stale_pending_media_session(self) -> None:
        req = self.request
        if not req:
            return
        pending = req.session.get(_CAMPAIGN_PENDING_MEDIA_SESSION_KEY)
        if not pending:
            return
        cid = pending.get('campaign_id')
        my_pk = self.instance.pk
        if my_pk:
            if cid is not None and int(cid) != int(my_pk):
                req.session.pop(_CAMPAIGN_PENDING_MEDIA_SESSION_KEY, None)
        elif cid is not None:
            req.session.pop(_CAMPAIGN_PENDING_MEDIA_SESSION_KEY, None)

    def _pending_video_ready(self) -> bool:
        req = self.request
        if not req:
            return False
        pending = req.session.get(_CAMPAIGN_PENDING_MEDIA_SESSION_KEY)
        path = (pending or {}).get('path')
        return bool(path and default_storage.exists(path))

    def clean(self):
        cleaned = super().clean()
        ct = cleaned.get('content_type')
        media_val = cleaned.get('media')
        cleared = media_val is False
        has_new_upload = media_val not in (None, False) and bool(media_val)
        has_existing = (
            bool(getattr(self.instance, 'media', None) and getattr(self.instance.media, 'name', ''))
            and not cleared
        )

        req = self.request
        if ct != Campaign.ContentType.VIDEO and req:
            req.session.pop(_CAMPAIGN_PENDING_MEDIA_SESSION_KEY, None)

        pending_ok = ct == Campaign.ContentType.VIDEO and self._pending_video_ready()

        if has_new_upload and req:
            req.session.pop(_CAMPAIGN_PENDING_MEDIA_SESSION_KEY, None)

        if cleared and req:
            req.session.pop(_CAMPAIGN_PENDING_MEDIA_SESSION_KEY, None)

        has_media = has_new_upload or has_existing or pending_ok

        if ct in (
            Campaign.ContentType.PHOTO,
            Campaign.ContentType.VIDEO,
            Campaign.ContentType.DOCUMENT,
            Campaign.ContentType.VOICE,
        ):
            if not has_media:
                raise forms.ValidationError('برای این نوع محتوا انتخاب یا بارگذاری فایل الزامی است.')

        if ct == Campaign.ContentType.TEXT and not (cleaned.get('body') or '').strip():
            raise forms.ValidationError('برای کمپین متنی، متن پیام را وارد کنید.')

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

        mode = cleaned.get('audience_mode')
        tags = cleaned.get('target_tags')
        if mode == self.AUDIENCE_TAGS and not tags:
            raise forms.ValidationError(
                'برای ارسال به دسته‌بندی، حداقل یک دسته‌بندی انتخاب کنید.',
            )

        return cleaned

    def save(self, commit=True):
        obj = super().save(commit=False)
        obj.scheduled_at = self.cleaned_data['resolved_scheduled_at']
        obj.inline_keyboard = []
        if commit:
            obj.save()
            if self.cleaned_data.get('audience_mode') == self.AUDIENCE_ALL:
                obj.target_tags.clear()
            else:
                self._save_m2m()
            self._apply_pending_video_upload(obj)
        return obj

    def _apply_pending_video_upload(self, obj: Campaign) -> None:
        req = self.request
        if not req or obj.content_type != Campaign.ContentType.VIDEO:
            return
        pending = req.session.pop(_CAMPAIGN_PENDING_MEDIA_SESSION_KEY, None)
        if not pending:
            return
        path = pending.get('path')
        if not path or not default_storage.exists(path):
            return
        try:
            with default_storage.open(path, 'rb') as fh:
                obj.media.save(pending['original_name'], File(fh), save=False)
            obj.save(update_fields=['media', 'updated_at'])
        finally:
            try:
                default_storage.delete(path)
            except OSError:
                pass


class TagForm(forms.ModelForm):
    class Meta:
        model = Tag
        fields = ['name', 'slug', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control panel-input', 'placeholder': 'مثلاً مشتری VIP'}),
            'slug': forms.TextInput(
                attrs={
                    'class': 'form-control panel-input',
                    'placeholder': 'خودکار از نام ساخته می‌شود',
                    'dir': 'ltr',
                },
            ),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'name': 'نام دسته‌بندی',
            'slug': 'شناسه (slug)',
            'is_active': 'فعال',
        }

    def __init__(self, *args, workspace=None, platform=None, **kwargs):
        self.workspace = workspace
        self.platform = platform
        super().__init__(*args, **kwargs)
        self.fields['slug'].required = False

    def clean_slug(self):
        from django.utils.text import slugify

        slug = (self.cleaned_data.get('slug') or '').strip()
        name = (self.cleaned_data.get('name') or '').strip()
        if not slug and name:
            slug = slugify(name, allow_unicode=False)
        if not slug:
            raise forms.ValidationError('شناسه دسته‌بندی معتبر نیست.')
        return slug[:140]

    def clean(self):
        cleaned = super().clean()
        if not self.workspace or not self.platform:
            return cleaned
        slug = cleaned.get('slug')
        name = cleaned.get('name')
        if slug and Tag.objects.filter(
            workspace=self.workspace,
            platform=self.platform,
            slug=slug,
        ).exists():
            self.add_error('slug', 'این شناسه قبلاً ثبت شده است.')
        if name and Tag.objects.filter(
            workspace=self.workspace,
            platform=self.platform,
            name=name,
        ).exists():
            self.add_error('name', 'این نام قبلاً ثبت شده است.')
        return cleaned

    def save(self, commit=True):
        obj = super().save(commit=False)
        if self.workspace:
            obj.workspace = self.workspace
        if self.platform:
            obj.platform = self.platform
        if commit:
            obj.save()
        return obj


