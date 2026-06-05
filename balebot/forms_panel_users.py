from django import forms
from django.contrib.auth import get_user_model

User = get_user_model()

_INPUT = 'form-control panel-input'


class PanelUserCreateForm(forms.Form):
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
        help_text='کاربر می‌تواند ربات بله را در پنل مدیریت کند.',
    )
    allow_telegram = forms.BooleanField(
        required=False,
        initial=True,
        label='دسترسی تلگرام',
        help_text='کاربر می‌تواند ربات تلگرام را در پنل مدیریت کند.',
    )
    allow_bale_miniapp = forms.BooleanField(
        required=False,
        initial=False,
        label='دسترسی مینی‌اپ بله',
        help_text='مدیریت فروشگاه/نمونه‌کار مینی‌اپ بله در پنل.',
    )
    allow_telegram_miniapp = forms.BooleanField(
        required=False,
        initial=False,
        label='دسترسی مینی‌اپ تلگرام',
        help_text='مدیریت فروشگاه/نمونه‌کار مینی‌اپ تلگرام در پنل.',
    )

    def clean(self):
        cleaned = super().clean()
        allow_bale = cleaned.get('allow_bale')
        allow_telegram = cleaned.get('allow_telegram')
        allow_bale_ma = cleaned.get('allow_bale_miniapp')
        allow_telegram_ma = cleaned.get('allow_telegram_miniapp')
        if allow_bale_ma and not allow_bale:
            raise forms.ValidationError('مینی‌اپ بله نیاز به دسترسی بله دارد.')
        if allow_telegram_ma and not allow_telegram:
            raise forms.ValidationError('مینی‌اپ تلگرام نیاز به دسترسی تلگرام دارد.')
        if not allow_bale and not allow_telegram:
            raise forms.ValidationError('حداقل یکی از پلتفرم‌های بله یا تلگرام باید انتخاب شود.')
        return cleaned

    def clean_username(self):
        username = (self.cleaned_data.get('username') or '').strip()
        if not username:
            raise forms.ValidationError('نام کاربری الزامی است.')
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError('این نام کاربری قبلاً ثبت شده است.')
        return username


class PanelUserUpdateForm(forms.Form):
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
    )
    workspace_active = forms.BooleanField(
        required=False,
        initial=True,
        label='پنل فعال',
    )
    allow_bale = forms.BooleanField(
        required=False,
        initial=True,
        label='دسترسی بله',
        help_text='کاربر می‌تواند ربات بله را در پنل مدیریت کند.',
    )
    allow_telegram = forms.BooleanField(
        required=False,
        initial=True,
        label='دسترسی تلگرام',
        help_text='کاربر می‌تواند ربات تلگرام را در پنل مدیریت کند.',
    )
    allow_bale_miniapp = forms.BooleanField(
        required=False,
        initial=False,
        label='دسترسی مینی‌اپ بله',
        help_text='مدیریت فروشگاه/نمونه‌کار مینی‌اپ بله در پنل.',
    )
    allow_telegram_miniapp = forms.BooleanField(
        required=False,
        initial=False,
        label='دسترسی مینی‌اپ تلگرام',
        help_text='مدیریت فروشگاه/نمونه‌کار مینی‌اپ تلگرام در پنل.',
    )

    def clean(self):
        cleaned = super().clean()
        allow_bale = cleaned.get('allow_bale')
        allow_telegram = cleaned.get('allow_telegram')
        allow_bale_ma = cleaned.get('allow_bale_miniapp')
        allow_telegram_ma = cleaned.get('allow_telegram_miniapp')
        if allow_bale_ma and not allow_bale:
            raise forms.ValidationError('مینی‌اپ بله نیاز به دسترسی بله دارد.')
        if allow_telegram_ma and not allow_telegram:
            raise forms.ValidationError('مینی‌اپ تلگرام نیاز به دسترسی تلگرام دارد.')
        if not allow_bale and not allow_telegram:
            raise forms.ValidationError('حداقل یکی از پلتفرم‌های بله یا تلگرام باید انتخاب شود.')
        return cleaned
