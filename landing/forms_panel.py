from django import forms

from landing.models import BusinessCategory, LandingSettings, ShowcaseBot, SubscriptionPlan
from landing.services.legal_text import normalize_legal_text

_INPUT = 'form-control panel-input'


class LandingSettingsForm(forms.ModelForm):
    class Meta:
        model = LandingSettings
        fields = (
            'demo_bot_url',
            'announce_text',
            'stats_label',
            'stat_stores',
            'stat_orders',
            'stat_setup_minutes',
            'pricing_note',
        )
        widgets = {
            'demo_bot_url': forms.URLInput(attrs={'class': _INPUT, 'dir': 'ltr'}),
            'announce_text': forms.TextInput(attrs={'class': _INPUT}),
            'stats_label': forms.TextInput(attrs={'class': _INPUT}),
            'stat_stores': forms.TextInput(attrs={'class': _INPUT}),
            'stat_orders': forms.TextInput(attrs={'class': _INPUT}),
            'stat_setup_minutes': forms.TextInput(attrs={'class': _INPUT}),
            'pricing_note': forms.Textarea(attrs={'class': _INPUT, 'rows': 2}),
        }


class TermsSettingsForm(forms.ModelForm):
    class Meta:
        model = LandingSettings
        fields = (
            'terms_page_title',
            'terms_page_content',
        )
        widgets = {
            'terms_page_title': forms.TextInput(attrs={'class': _INPUT}),
            'terms_page_content': forms.Textarea(attrs={
                'class': f'{_INPUT} terms-editor-textarea',
                'rows': 28,
                'dir': 'rtl',
                'spellcheck': 'true',
            }),
        }

    def clean_terms_page_content(self):
        return normalize_legal_text(self.cleaned_data.get('terms_page_content'))


class BrandSettingsForm(forms.ModelForm):
    class Meta:
        model = LandingSettings
        fields = (
            'brand_icon_svg',
            'brand_logo_svg',
            'brand_favicon_svg',
            'brand_wordmark_primary',
            'brand_wordmark_accent',
        )
        widgets = {
            'brand_wordmark_primary': forms.TextInput(attrs={'class': _INPUT, 'dir': 'ltr'}),
            'brand_wordmark_accent': forms.TextInput(attrs={'class': _INPUT, 'dir': 'ltr'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name in ('brand_icon_svg', 'brand_logo_svg', 'brand_favicon_svg'):
            self.fields[name].required = False
            self.fields[name].widget.attrs.update({
                'class': 'form-control panel-input',
                'accept': '.svg,image/svg+xml',
            })


class SubscriptionPlanForm(forms.ModelForm):
    features_text = forms.CharField(
        label='امکانات (هر خط یک مورد)',
        widget=forms.Textarea(attrs={'class': _INPUT, 'rows': 6}),
        required=False,
    )

    class Meta:
        model = SubscriptionPlan
        fields = (
            'name',
            'slug',
            'price_label',
            'price_period',
            'description',
            'is_featured',
            'is_active',
            'sort_order',
            'button_style',
            'cta_label',
        )
        widgets = {
            'name': forms.TextInput(attrs={'class': _INPUT}),
            'slug': forms.TextInput(attrs={'class': _INPUT, 'dir': 'ltr'}),
            'price_label': forms.TextInput(attrs={'class': _INPUT}),
            'price_period': forms.TextInput(attrs={'class': _INPUT}),
            'description': forms.TextInput(attrs={'class': _INPUT}),
            'sort_order': forms.NumberInput(attrs={'class': _INPUT}),
            'button_style': forms.Select(attrs={'class': _INPUT}),
            'cta_label': forms.TextInput(attrs={'class': _INPUT}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields['features_text'].initial = '\n'.join(self.instance.feature_list())

    def clean(self):
        cleaned = super().clean()
        raw = cleaned.get('features_text') or ''
        cleaned['_features_list'] = [line.strip() for line in raw.splitlines() if line.strip()]
        if cleaned.get('is_featured'):
            qs = SubscriptionPlan.objects.filter(is_featured=True)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError('فقط یک پلن می‌تواند «پیشنهاد ویژه» باشد.')
        return cleaned

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.features = self.cleaned_data.get('_features_list', [])
        if commit:
            instance.save()
        return instance


class BusinessCategoryForm(forms.ModelForm):
    class Meta:
        model = BusinessCategory
        fields = (
            'name',
            'slug',
            'sort_order',
            'is_active',
            'show_on_landing',
            'is_other',
        )
        widgets = {
            'name': forms.TextInput(attrs={'class': _INPUT}),
            'slug': forms.TextInput(attrs={'class': _INPUT, 'dir': 'ltr'}),
            'sort_order': forms.NumberInput(attrs={'class': _INPUT}),
        }

    def clean(self):
        cleaned = super().clean()
        if cleaned.get('is_other'):
            qs = BusinessCategory.objects.filter(is_other=True)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError('فقط یک صنف می‌تواند گزینه «سایر» باشد.')
        return cleaned


class ShowcaseBotForm(forms.ModelForm):
    class Meta:
        model = ShowcaseBot
        fields = (
            'name',
            'image',
            'description',
            'platform',
            'bot_url',
            'show_on_landing',
            'is_active',
            'sort_order',
        )
        widgets = {
            'name': forms.TextInput(attrs={'class': _INPUT}),
            'description': forms.Textarea(attrs={'class': _INPUT, 'rows': 4}),
            'platform': forms.Select(attrs={'class': _INPUT}),
            'bot_url': forms.URLInput(attrs={'class': _INPUT, 'dir': 'ltr'}),
            'sort_order': forms.NumberInput(attrs={'class': _INPUT}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['image'].required = not (self.instance and self.instance.pk)
        self.fields['image'].widget.attrs.update({
            'class': 'form-control panel-input',
            'accept': 'image/*',
        })
