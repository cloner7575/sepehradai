from django import forms
from django.contrib.auth import get_user_model

from balebot.services.jalali_datetime import parse_jalali_date_time

User = get_user_model()

_INPUT = 'form-control panel-input'
_CHECKBOX = {'class': 'form-check-input'}
_JALALI_DATE_ATTRS = {
    'class': _INPUT,
    'placeholder': '۱۴۰۳/۰۸/۱۵',
    'dir': 'ltr',
    'autocomplete': 'off',
    'data-jalali-date': '1',
    'readonly': 'readonly',
}
_JALALI_TIME_ATTRS = {
    'class': _INPUT,
    'placeholder': '۱۴:۳۰',
    'dir': 'ltr',
    'autocomplete': 'off',
    'data-jalali-time': '1',
}


class JalaliSubscriptionFormMixin(forms.Form):
    jalali_subscription_expires_date = forms.CharField(
        required=False,
        label='تاریخ انقضا (شمسی)',
        widget=forms.TextInput(attrs=_JALALI_DATE_ATTRS),
    )
    jalali_subscription_expires_time = forms.CharField(
        required=False,
        label='ساعت انقضا',
        help_text='خالی = بدون محدودیت. به وقت ایران (منطقهٔ زمانی سرور).',
        widget=forms.TextInput(attrs=_JALALI_TIME_ATTRS),
    )

    def _resolve_subscription_expires_at(self, cleaned):
        j_date = (cleaned.get('jalali_subscription_expires_date') or '').strip()
        j_time = (cleaned.get('jalali_subscription_expires_time') or '').strip()
        if not j_date and not j_time:
            cleaned['subscription_expires_at'] = None
            return cleaned
        if not j_date:
            raise forms.ValidationError('تاریخ انقضای شمسی را وارد کنید یا هر دو فیلد را خالی بگذارید.')
        if not j_time:
            j_time = '23:59'
        try:
            cleaned['subscription_expires_at'] = parse_jalali_date_time(j_date, j_time)
        except ValueError as exc:
            raise forms.ValidationError(str(exc)) from exc
        return cleaned


class PanelUserCreateForm(JalaliSubscriptionFormMixin):
    username = forms.CharField(
        max_length=150,
        label='نام کاربری',
        widget=forms.TextInput(attrs={'class': _INPUT, 'autocomplete': 'username'}),
    )
    password = forms.CharField(
        label='رمز عبور',
        widget=forms.PasswordInput(attrs={'class': _INPUT, 'autocomplete': 'new-password'}),
    )
    email = forms.EmailField(
        required=False,
        label='ایمیل',
        widget=forms.EmailInput(attrs={'class': _INPUT}),
    )
    workspace_name = forms.CharField(
        max_length=120,
        label='نام پنل',
        widget=forms.TextInput(attrs={'class': _INPUT}),
    )
    allow_bale = forms.BooleanField(
        required=False,
        initial=True,
        label='دسترسی بله',
        widget=forms.CheckboxInput(attrs=_CHECKBOX),
        help_text='کاربر می‌تواند ربات بله را در پنل مدیریت کند.',
    )
    allow_telegram = forms.BooleanField(
        required=False,
        initial=True,
        label='دسترسی تلگرام',
        widget=forms.CheckboxInput(attrs=_CHECKBOX),
        help_text='کاربر می‌تواند ربات تلگرام را در پنل مدیریت کند.',
    )
    allow_bale_miniapp = forms.BooleanField(
        required=False,
        initial=False,
        label='دسترسی مینی‌اپ بله',
        widget=forms.CheckboxInput(attrs=_CHECKBOX),
        help_text='مدیریت ویترین و محتوای مینی‌اپ بله در پنل.',
    )
    allow_telegram_miniapp = forms.BooleanField(
        required=False,
        initial=False,
        label='دسترسی مینی‌اپ تلگرام',
        widget=forms.CheckboxInput(attrs=_CHECKBOX),
        help_text='مدیریت ویترین و محتوای مینی‌اپ تلگرام در پنل.',
    )
    allow_instagram = forms.BooleanField(
        required=False,
        initial=False,
        label='دسترسی اینستاگرام',
        widget=forms.CheckboxInput(attrs=_CHECKBOX),
        help_text='استخراج و مدیریت شماره از بکاپ دایرکت اینستاگرام.',
    )

    def clean(self):
        cleaned = super().clean()
        allow_bale = cleaned.get('allow_bale')
        allow_telegram = cleaned.get('allow_telegram')
        allow_bale_ma = cleaned.get('allow_bale_miniapp')
        allow_telegram_ma = cleaned.get('allow_telegram_miniapp')
        allow_instagram = cleaned.get('allow_instagram')
        if allow_bale_ma and not allow_bale:
            raise forms.ValidationError('مینی‌اپ بله نیاز به دسترسی بله دارد.')
        if allow_telegram_ma and not allow_telegram:
            raise forms.ValidationError('مینی‌اپ تلگرام نیاز به دسترسی تلگرام دارد.')
        if not allow_bale and not allow_telegram and not allow_instagram:
            raise forms.ValidationError('حداقل یک دسترسی (بله، تلگرام یا اینستاگرام) باید انتخاب شود.')
        return self._resolve_subscription_expires_at(cleaned)

    def clean_username(self):
        username = (self.cleaned_data.get('username') or '').strip()
        if not username:
            raise forms.ValidationError('نام کاربری الزامی است.')
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError('این نام کاربری قبلاً ثبت شده است.')
        return username


class PanelUserUpdateForm(JalaliSubscriptionFormMixin):
    workspace_name = forms.CharField(
        max_length=120,
        label='نام پنل',
        widget=forms.TextInput(attrs={'class': _INPUT}),
    )
    email = forms.EmailField(
        required=False,
        label='ایمیل',
        widget=forms.EmailInput(attrs={'class': _INPUT}),
    )
    password = forms.CharField(
        required=False,
        label='رمز عبور جدید',
        help_text='برای حفظ رمز فعلی خالی بگذارید.',
        widget=forms.PasswordInput(attrs={'class': _INPUT, 'autocomplete': 'new-password'}),
    )
    is_active = forms.BooleanField(
        required=False,
        initial=True,
        label='حساب فعال',
        widget=forms.CheckboxInput(attrs=_CHECKBOX),
    )
    workspace_active = forms.BooleanField(
        required=False,
        initial=True,
        label='پنل فعال',
        widget=forms.CheckboxInput(attrs=_CHECKBOX),
    )
    allow_bale = forms.BooleanField(
        required=False,
        initial=True,
        label='دسترسی بله',
        widget=forms.CheckboxInput(attrs=_CHECKBOX),
        help_text='کاربر می‌تواند ربات بله را در پنل مدیریت کند.',
    )
    allow_telegram = forms.BooleanField(
        required=False,
        initial=True,
        label='دسترسی تلگرام',
        widget=forms.CheckboxInput(attrs=_CHECKBOX),
        help_text='کاربر می‌تواند ربات تلگرام را در پنل مدیریت کند.',
    )
    allow_bale_miniapp = forms.BooleanField(
        required=False,
        initial=False,
        label='دسترسی مینی‌اپ بله',
        widget=forms.CheckboxInput(attrs=_CHECKBOX),
        help_text='مدیریت ویترین و محتوای مینی‌اپ بله در پنل.',
    )
    allow_telegram_miniapp = forms.BooleanField(
        required=False,
        initial=False,
        label='دسترسی مینی‌اپ تلگرام',
        widget=forms.CheckboxInput(attrs=_CHECKBOX),
        help_text='مدیریت ویترین و محتوای مینی‌اپ تلگرام در پنل.',
    )
    allow_instagram = forms.BooleanField(
        required=False,
        initial=False,
        label='دسترسی اینستاگرام',
        widget=forms.CheckboxInput(attrs=_CHECKBOX),
        help_text='استخراج و مدیریت شماره از بکاپ دایرکت اینستاگرام.',
    )

    def clean(self):
        cleaned = super().clean()
        allow_bale = cleaned.get('allow_bale')
        allow_telegram = cleaned.get('allow_telegram')
        allow_bale_ma = cleaned.get('allow_bale_miniapp')
        allow_telegram_ma = cleaned.get('allow_telegram_miniapp')
        allow_instagram = cleaned.get('allow_instagram')
        if allow_bale_ma and not allow_bale:
            raise forms.ValidationError('مینی‌اپ بله نیاز به دسترسی بله دارد.')
        if allow_telegram_ma and not allow_telegram:
            raise forms.ValidationError('مینی‌اپ تلگرام نیاز به دسترسی تلگرام دارد.')
        if not allow_bale and not allow_telegram and not allow_instagram:
            raise forms.ValidationError('حداقل یک دسترسی (بله، تلگرام یا اینستاگرام) باید انتخاب شود.')
        return self._resolve_subscription_expires_at(cleaned)
