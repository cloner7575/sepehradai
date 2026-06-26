import re

from django import forms

from instagram.services.phones import validate_iran_mobile
from landing.constants import BUSINESS_TYPES, MESSENGER_CHOICES
from landing.models import Lead

_PERSIAN_DIGITS = str.maketrans('۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩', '01234567890123456789')


def normalize_phone(value: str) -> str:
    digits = re.sub(r'\D', '', (value or '').translate(_PERSIAN_DIGITS))
    if digits.startswith('98') and len(digits) == 12:
        digits = '0' + digits[2:]
    if digits.startswith('9') and len(digits) == 10:
        digits = '0' + digits
    return digits


class LeadForm(forms.ModelForm):
    website = forms.CharField(required=False, widget=forms.HiddenInput())

    class Meta:
        model = Lead
        fields = ('name', 'business_name', 'phone', 'messenger', 'business_type', 'note')
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'landing-input',
                'placeholder': 'نام شما',
                'autocomplete': 'name',
            }),
            'business_name': forms.TextInput(attrs={
                'class': 'landing-input',
                'placeholder': 'نام فروشگاه یا برند',
                'autocomplete': 'organization',
            }),
            'phone': forms.TextInput(attrs={
                'class': 'landing-input',
                'placeholder': '۰۹۱۲۳۴۵۶۷۸۹',
                'inputmode': 'tel',
                'autocomplete': 'tel',
            }),
            'messenger': forms.Select(attrs={'class': 'landing-input'}),
            'business_type': forms.Select(attrs={'class': 'landing-input'}),
            'note': forms.Textarea(attrs={
                'class': 'landing-input landing-textarea',
                'rows': 3,
                'placeholder': 'هر توضیحی که فکر می‌کنی لازمه…',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['name'].required = True
        self.fields['phone'].required = True
        self.fields['messenger'].required = False
        self.fields['messenger'].choices = [('', 'انتخاب کنید')] + list(MESSENGER_CHOICES)
        self.fields['business_type'].required = False
        self.fields['business_type'].choices = [('', 'انتخاب صنف')] + list(BUSINESS_TYPES)

    def clean_phone(self):
        phone = normalize_phone(self.cleaned_data.get('phone', ''))
        if not validate_iran_mobile(phone):
            raise forms.ValidationError('شماره موبایل معتبر وارد کنید (مثال: ۰۹۱۲۳۴۵۶۷۸۹).')
        return phone

    def clean_website(self):
        return self.cleaned_data.get('website', '')
