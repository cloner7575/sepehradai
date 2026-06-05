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
