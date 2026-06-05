import json

from django import forms
from django.utils.text import slugify

from balebot.models import CatalogCategory, CatalogItem, CatalogSettings

_INPUT = 'form-control panel-input'


class CatalogSettingsForm(forms.ModelForm):
    theme_primary = forms.CharField(
        required=False,
        label='رنگ اصلی',
        widget=forms.TextInput(attrs={'class': _INPUT, 'type': 'color'}),
    )
    theme_accent = forms.CharField(
        required=False,
        label='رنگ تأکیدی',
        widget=forms.TextInput(attrs={'class': _INPUT, 'type': 'color'}),
    )
    theme_layout = forms.ChoiceField(
        choices=[('grid', 'شبکه‌ای'), ('list', 'لیستی')],
        required=False,
        label='چیدمان',
        widget=forms.Select(attrs={'class': _INPUT}),
    )

    class Meta:
        model = CatalogSettings
        fields = [
            'is_enabled',
            'payment_admin_enabled',
            'payment_zarinpal_enabled',
            'payment_default_method',
            'admin_notify_chat_id',
            'zarinpal_merchant_id',
            'zarinpal_sandbox',
            'hero_title',
            'hero_subtitle',
            'logo',
        ]
        widgets = {
            'is_enabled': forms.CheckboxInput(attrs={'class': 'form-check-input', 'role': 'switch'}),
            'payment_admin_enabled': forms.CheckboxInput(attrs={'class': 'form-check-input', 'role': 'switch'}),
            'payment_zarinpal_enabled': forms.CheckboxInput(attrs={'class': 'form-check-input', 'role': 'switch'}),
            'payment_default_method': forms.Select(attrs={'class': _INPUT}),
            'admin_notify_chat_id': forms.NumberInput(attrs={'class': _INPUT, 'dir': 'ltr'}),
            'zarinpal_merchant_id': forms.TextInput(attrs={'class': _INPUT, 'dir': 'ltr', 'autocomplete': 'off'}),
            'zarinpal_sandbox': forms.CheckboxInput(attrs={'class': 'form-check-input', 'role': 'switch'}),
            'hero_title': forms.TextInput(attrs={'class': _INPUT}),
            'hero_subtitle': forms.TextInput(attrs={'class': _INPUT}),
            'logo': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }

    def clean(self):
        cleaned = super().clean()
        admin_on = cleaned.get('payment_admin_enabled')
        zarinpal_on = cleaned.get('payment_zarinpal_enabled')
        merchant = (cleaned.get('zarinpal_merchant_id') or '').strip()
        admin_chat = cleaned.get('admin_notify_chat_id')
        is_enabled = cleaned.get('is_enabled')

        if zarinpal_on and not merchant:
            self.add_error('zarinpal_merchant_id', 'برای فعال‌سازی زرین‌پال، مرچنت‌آیدی الزامی است.')
        if admin_on and not admin_chat:
            self.add_error(
                'admin_notify_chat_id',
                'برای ارسال سبد به ادمین، چت‌آیدی ادمین الزامی است.',
            )

        has_admin = bool(admin_on and admin_chat)
        has_zarinpal = bool(zarinpal_on and merchant)

        if is_enabled and not has_admin and not has_zarinpal:
            raise forms.ValidationError(
                'برای فعال‌سازی مینی‌اپ، حداقل یک روش پرداخت را کامل تنظیم کنید '
                '(چت‌آیدی ادمین یا مرچنت‌آیدی زرین‌پال).',
            )

        default = cleaned.get('payment_default_method')
        enabled = set()
        if has_admin:
            enabled.add(CatalogSettings.PaymentMethod.ADMIN_CART)
        if has_zarinpal:
            enabled.add(CatalogSettings.PaymentMethod.ZARINPAL)
        if enabled and default not in enabled:
            cleaned['payment_default_method'] = next(iter(enabled))
        return cleaned

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        theme = (self.instance.theme_config or {}) if self.instance else {}
        self.fields['theme_primary'].initial = theme.get('primary_color', '#2563eb')
        self.fields['theme_accent'].initial = theme.get('accent_color', '#7c3aed')
        self.fields['theme_layout'].initial = theme.get('layout', 'grid')
        self.fields['admin_notify_chat_id'].help_text = (
            'شناسه عددی گفتگوی شما با ربات (از @userinfobot یا لاگ ربات).'
        )
        self.fields['zarinpal_merchant_id'].help_text = 'از پنل زرین‌پال → درگاه پرداخت.'
        self.fields['is_enabled'].help_text = (
            'فقط وقتی فعال کنید که حداقل یک روش پرداخت را کامل پر کرده‌اید.'
        )

    def save(self, commit=True):
        obj = super().save(commit=False)
        obj.theme_config = {
            **(obj.theme_config or {}),
            'primary_color': self.cleaned_data.get('theme_primary') or '#2563eb',
            'accent_color': self.cleaned_data.get('theme_accent') or '#7c3aed',
            'layout': self.cleaned_data.get('theme_layout') or 'grid',
            'font_family': (obj.theme_config or {}).get('font_family', 'Vazirmatn'),
        }
        if commit:
            obj.save()
        return obj


class CatalogCategoryForm(forms.ModelForm):
    class Meta:
        model = CatalogCategory
        fields = ['parent', 'name', 'slug', 'icon', 'sort_order', 'is_active']
        widgets = {
            'parent': forms.Select(attrs={'class': _INPUT}),
            'name': forms.TextInput(attrs={'class': _INPUT}),
            'slug': forms.TextInput(attrs={'class': _INPUT, 'dir': 'ltr'}),
            'icon': forms.TextInput(attrs={'class': _INPUT, 'placeholder': 'bi-box'}),
            'sort_order': forms.NumberInput(attrs={'class': _INPUT}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input', 'role': 'switch'}),
        }

    def __init__(self, *args, workspace=None, platform=None, **kwargs):
        super().__init__(*args, **kwargs)
        qs = CatalogCategory.objects.filter(workspace=workspace, platform=platform)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        self.fields['parent'].queryset = qs.order_by('sort_order', 'name')
        self.fields['parent'].required = False

    def clean_slug(self):
        slug = (self.cleaned_data.get('slug') or '').strip()
        if not slug:
            name = self.cleaned_data.get('name') or ''
            slug = slugify(name, allow_unicode=False) or 'category'
        return slug[:140]


class CatalogItemForm(forms.ModelForm):
    metadata_json = forms.CharField(
        required=False,
        label='فیلدهای سفارشی (JSON)',
        widget=forms.Textarea(attrs={'class': _INPUT, 'rows': 4, 'dir': 'ltr'}),
    )

    class Meta:
        model = CatalogItem
        fields = [
            'category',
            'title',
            'slug',
            'short_description',
            'description',
            'item_type',
            'price',
            'sale_mode',
            'stock',
            'is_active',
            'is_featured',
            'sort_order',
        ]
        widgets = {
            'category': forms.Select(attrs={'class': _INPUT}),
            'title': forms.TextInput(attrs={'class': _INPUT}),
            'slug': forms.TextInput(attrs={'class': _INPUT, 'dir': 'ltr'}),
            'short_description': forms.TextInput(attrs={'class': _INPUT}),
            'description': forms.Textarea(attrs={'class': _INPUT, 'rows': 5}),
            'item_type': forms.Select(attrs={'class': _INPUT}),
            'price': forms.NumberInput(attrs={'class': _INPUT, 'dir': 'ltr'}),
            'sale_mode': forms.Select(attrs={'class': _INPUT}),
            'stock': forms.NumberInput(attrs={'class': _INPUT, 'dir': 'ltr'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input', 'role': 'switch'}),
            'is_featured': forms.CheckboxInput(attrs={'class': 'form-check-input', 'role': 'switch'}),
            'sort_order': forms.NumberInput(attrs={'class': _INPUT}),
        }

    def __init__(self, *args, workspace=None, platform=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['category'].queryset = CatalogCategory.objects.filter(
            workspace=workspace,
            platform=platform,
            is_active=True,
        ).order_by('sort_order', 'name')
        self.fields['category'].required = False
        if self.instance.pk:
            self.fields['metadata_json'].initial = json.dumps(
                self.instance.metadata or {},
                ensure_ascii=False,
                indent=2,
            )

    def clean_slug(self):
        slug = (self.cleaned_data.get('slug') or '').strip()
        if not slug:
            slug = slugify(self.cleaned_data.get('title') or '', allow_unicode=False) or 'item'
        return slug[:220]

    def clean_metadata_json(self):
        raw = (self.cleaned_data.get('metadata_json') or '').strip()
        if not raw:
            return {}
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as e:
            raise forms.ValidationError(f'JSON نامعتبر: {e}') from e
        if not isinstance(data, dict):
            raise forms.ValidationError('metadata باید یک شیء JSON باشد.')
        return data

    def save(self, commit=True):
        obj = super().save(commit=False)
        obj.metadata = self.cleaned_data.get('metadata_json') or {}
        if commit:
            obj.save()
        return obj
