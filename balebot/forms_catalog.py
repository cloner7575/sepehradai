import json

from django import forms
from django.utils.text import slugify

from balebot.models import CatalogCategory, CatalogItem, CatalogSettings
from balebot.widgets import PersianClearableFileInput
from balebot.services.catalog_page_layout import get_home_blocks, sanitize_home_blocks
from balebot.services.checkout_form import default_checkout_form, sanitize_checkout_form

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
        label='چیدمان آیتم‌ها',
        widget=forms.Select(attrs={'class': _INPUT}),
    )
    label_buy_now = forms.CharField(required=False, label='دکمه خرید', widget=forms.TextInput(attrs={'class': _INPUT}))
    label_add_to_cart = forms.CharField(
        required=False,
        label='افزودن به سبد',
        widget=forms.TextInput(attrs={'class': _INPUT}),
    )
    label_request_quote = forms.CharField(
        required=False,
        label='درخواست / تماس',
        widget=forms.TextInput(attrs={'class': _INPUT}),
    )
    label_cart = forms.CharField(required=False, label='عنوان سبد', widget=forms.TextInput(attrs={'class': _INPUT}))
    label_checkout = forms.CharField(
        required=False,
        label='دکمه تسویه',
        widget=forms.TextInput(attrs={'class': _INPUT}),
    )
    label_download = forms.CharField(
        required=False,
        label='دکمه دانلود',
        widget=forms.TextInput(attrs={'class': _INPUT}),
    )
    checkout_form_json = forms.CharField(
        required=False,
        label='',
        widget=forms.HiddenInput(attrs={'id': 'id_checkout_form_json'}),
    )

    class Meta:
        model = CatalogSettings
        fields = [
            'is_enabled',
            'require_channel_membership',
            'required_channel_id',
            'channel_membership_message',
            'channel_invite_link',
            'payment_admin_enabled',
            'payment_zarinpal_enabled',
            'payment_default_method',
            'admin_notify_chat_id',
            'zarinpal_merchant_id',
            'zarinpal_sandbox',
            'hero_title',
            'hero_subtitle',
            'logo',
            'hero_background',
        ]
        widgets = {
            'is_enabled': forms.CheckboxInput(attrs={'class': 'form-check-input', 'role': 'switch'}),
            'require_channel_membership': forms.CheckboxInput(attrs={'class': 'form-check-input', 'role': 'switch'}),
            'required_channel_id': forms.TextInput(attrs={'class': _INPUT, 'dir': 'ltr', 'placeholder': '@mychannel'}),
            'channel_membership_message': forms.Textarea(attrs={'class': _INPUT, 'rows': 3}),
            'channel_invite_link': forms.URLInput(attrs={'class': _INPUT, 'dir': 'ltr', 'placeholder': 'https://...'}),
            'payment_admin_enabled': forms.CheckboxInput(attrs={'class': 'form-check-input', 'role': 'switch'}),
            'payment_zarinpal_enabled': forms.CheckboxInput(attrs={'class': 'form-check-input', 'role': 'switch'}),
            'payment_default_method': forms.Select(attrs={'class': _INPUT}),
            'admin_notify_chat_id': forms.NumberInput(attrs={'class': _INPUT, 'dir': 'ltr'}),
            'zarinpal_merchant_id': forms.TextInput(attrs={'class': _INPUT, 'dir': 'ltr', 'autocomplete': 'off'}),
            'zarinpal_sandbox': forms.CheckboxInput(attrs={'class': 'form-check-input', 'role': 'switch'}),
            'hero_title': forms.TextInput(attrs={'class': _INPUT, 'placeholder': 'نام ویترین یا کسب‌وکار'}),
            'hero_subtitle': forms.TextInput(attrs={'class': _INPUT, 'placeholder': 'توضیح کوتاه زیر عنوان'}),
            'logo': PersianClearableFileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
            'hero_background': PersianClearableFileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
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

        require_channel = cleaned.get('require_channel_membership')
        channel_id = (cleaned.get('required_channel_id') or '').strip()
        if require_channel and not channel_id:
            self.add_error(
                'required_channel_id',
                'برای فعال‌سازی شرط عضویت کانال، شناسه کانال الزامی است.',
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
        labels = (self.instance.labels or {}) if self.instance else {}
        self.fields['theme_primary'].initial = theme.get('primary_color', '#334155')
        self.fields['theme_accent'].initial = theme.get('accent_color', '#3f3f46')
        self.fields['theme_layout'].initial = theme.get('layout', 'grid')
        self.fields['label_buy_now'].initial = labels.get('buy_now', 'خرید')
        self.fields['label_add_to_cart'].initial = labels.get('add_to_cart', 'افزودن به سبد')
        self.fields['label_request_quote'].initial = labels.get('request_quote', 'درخواست / تماس')
        self.fields['label_cart'].initial = labels.get('cart', 'سبد خرید')
        self.fields['label_checkout'].initial = labels.get('checkout', 'تسویه حساب')
        self.fields['label_download'].initial = labels.get('download', 'دانلود')
        checkout = (self.instance.checkout_form or default_checkout_form()) if self.instance else default_checkout_form()
        self.initial['checkout_form_json'] = json.dumps(checkout, ensure_ascii=False)
        self.fields['checkout_form_json'].initial = self.initial['checkout_form_json']
        self.fields['hero_title'].help_text = 'در بالای مینی‌اپ نمایش داده می‌شود.'
        self.fields['hero_subtitle'].help_text = 'زیر عنوان — اختیاری.'
        self.fields['logo'].help_text = 'لوگوی کوچک روی بنر هیرو (جدا از پس‌زمینه).'
        self.fields['hero_background'].help_text = 'تصویر پس‌زمینه بنر هیرو — اختیاری.'
        self.fields['theme_layout'].help_text = 'نحوه نمایش لیست آیتم‌ها در صفحه اصلی.'
        self.fields['admin_notify_chat_id'].help_text = (
            'شناسه عددی گفتگوی شما با ربات (از @userinfobot یا لاگ ربات).'
        )
        self.fields['zarinpal_merchant_id'].help_text = 'از پنل زرین‌پال → درگاه پرداخت.'
        self.fields['is_enabled'].help_text = (
            'فقط وقتی فعال کنید که حداقل یک روش پرداخت را کامل پر کرده‌اید.'
        )
        self.fields['require_channel_membership'].help_text = (
            'اگر فعال باشد، کاربر تا زمان عضویت در کانال به مینی‌اپ دسترسی ندارد.'
        )
        self.fields['required_channel_id'].help_text = (
            'نام کاربری کانال (مثلاً @mychannel) یا شناسه عددی. ربات باید ادمین کانال باشد.'
        )
        self.fields['channel_membership_message'].help_text = (
            'پیامی که به کاربرانی که هنوز عضو کانال نیستند نمایش داده می‌شود.'
        )
        self.fields['channel_invite_link'].help_text = (
            'لینک دعوت کانال برای دکمه «عضویت در کانال» در مینی‌اپ.'
        )

    def clean_checkout_form_json(self):
        raw = self.cleaned_data.get('checkout_form_json')
        return sanitize_checkout_form(raw)

    def save(self, commit=True):
        obj = super().save(commit=False)
        obj.theme_config = {
            **(obj.theme_config or {}),
            'primary_color': self.cleaned_data.get('theme_primary') or '#334155',
            'accent_color': self.cleaned_data.get('theme_accent') or '#3f3f46',
            'layout': self.cleaned_data.get('theme_layout') or 'grid',
            'font_family': (obj.theme_config or {}).get('font_family', 'Vazirmatn'),
        }
        obj.labels = {
            'buy_now': (self.cleaned_data.get('label_buy_now') or '').strip() or 'خرید',
            'add_to_cart': (self.cleaned_data.get('label_add_to_cart') or '').strip() or 'افزودن به سبد',
            'request_quote': (self.cleaned_data.get('label_request_quote') or '').strip() or 'درخواست / تماس',
            'cart': (self.cleaned_data.get('label_cart') or '').strip() or 'سبد خرید',
            'checkout': (self.cleaned_data.get('label_checkout') or '').strip() or 'تسویه حساب',
            'download': (self.cleaned_data.get('label_download') or '').strip() or 'دانلود',
            'remove_from_cart': (obj.labels or {}).get('remove_from_cart', 'حذف'),
        }
        obj.checkout_form = self.cleaned_data.get('checkout_form_json') or default_checkout_form()
        if commit:
            obj.save()
        return obj


class MiniAppFlowForm(forms.ModelForm):
    """ظاهر و چیدمان صفحهٔ اصلی مینی‌اپ."""

    page_layout = forms.CharField(
        required=False,
        label='',
        widget=forms.HiddenInput(attrs={'id': 'id_page_layout'}),
    )
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
        label='چیدمان محصولات',
        widget=forms.Select(attrs={'class': _INPUT}),
    )
    label_buy_now = forms.CharField(
        required=False,
        label='دکمه خرید',
        widget=forms.TextInput(attrs={'class': _INPUT}),
    )

    class Meta:
        model = CatalogSettings
        fields = ['hero_title', 'hero_subtitle', 'logo', 'hero_background']
        widgets = {
            'hero_title': forms.TextInput(attrs={'class': _INPUT, 'placeholder': 'نام ویترین'}),
            'hero_subtitle': forms.TextInput(attrs={'class': _INPUT, 'placeholder': 'توضیح کوتاه'}),
            'logo': PersianClearableFileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
            'hero_background': PersianClearableFileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        theme = (self.instance.theme_config or {}) if self.instance else {}
        labels = (self.instance.labels or {}) if self.instance else {}
        self.fields['theme_primary'].initial = theme.get('primary_color', '#334155')
        self.fields['theme_accent'].initial = theme.get('accent_color', '#3f3f46')
        self.fields['theme_layout'].initial = theme.get('layout', 'grid')
        self.fields['label_buy_now'].initial = labels.get('buy_now', 'خرید')
        blocks = get_home_blocks(theme)
        self.initial['page_layout'] = json.dumps(blocks, ensure_ascii=False)
        self.fields['page_layout'].initial = self.initial['page_layout']

    def clean_page_layout(self):
        raw = self.cleaned_data.get('page_layout')
        return sanitize_home_blocks(raw)

    def save(self, commit=True):
        obj = super().save(commit=False)
        blocks = self.cleaned_data.get('page_layout')
        if blocks is None:
            blocks = get_home_blocks(obj.theme_config)
        obj.theme_config = {
            **(obj.theme_config or {}),
            'primary_color': self.cleaned_data.get('theme_primary') or '#334155',
            'accent_color': self.cleaned_data.get('theme_accent') or '#3f3f46',
            'layout': self.cleaned_data.get('theme_layout') or 'grid',
            'font_family': (obj.theme_config or {}).get('font_family', 'Vazirmatn'),
            'home_blocks': blocks,
        }
        obj.labels = {
            **(obj.labels or {}),
            'buy_now': (self.cleaned_data.get('label_buy_now') or '').strip() or 'خرید',
        }
        if commit:
            obj.save()
        return obj


class CatalogCategoryForm(forms.ModelForm):
    class Meta:
        model = CatalogCategory
        fields = ['parent', 'name', 'slug', 'image', 'sort_order', 'is_active']
        widgets = {
            'parent': forms.Select(attrs={'class': _INPUT}),
            'name': forms.TextInput(attrs={'class': _INPUT}),
            'slug': forms.TextInput(attrs={'class': _INPUT, 'dir': 'ltr'}),
            'image': PersianClearableFileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
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
            'cover',
            'download_file',
            'download_link',
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
            'item_type': forms.Select(attrs={'class': _INPUT, 'id': 'id_item_type'}),
            'cover': PersianClearableFileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
            'download_file': PersianClearableFileInput(attrs={'class': 'form-control'}),
            'download_link': forms.URLInput(attrs={'class': _INPUT, 'dir': 'ltr', 'placeholder': 'https://...'}),
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
        self.fields['cover'].help_text = 'تصویر نمایشی کاور — در لیست و صفحه آیتم نشان داده می‌شود.'
        self.fields['download_file'].help_text = 'آپلود فایل روی سرور شما — یا از لینک مستقیم زیر استفاده کنید.'
        self.fields['download_link'].help_text = 'لینک مستقیم فایل (گوگل‌درایو، دراپ‌باکس، CDN و...). یکی از دو روش کافی است.'
        self.fields['item_type'].help_text = 'برای فایل دانلود رایگان، نوع «فایل دانلود» را انتخاب کنید.'
        if self.instance.pk:
            self.fields['metadata_json'].initial = json.dumps(
                self.instance.metadata or {},
                ensure_ascii=False,
                indent=2,
            )

    def clean_download_link(self):
        link = (self.cleaned_data.get('download_link') or '').strip()
        return link

    def clean(self):
        cleaned = super().clean()
        item_type = cleaned.get('item_type')
        download_file = cleaned.get('download_file')
        download_link = (cleaned.get('download_link') or '').strip()
        has_existing_file = bool(self.instance.pk and self.instance.download_file)
        if item_type == CatalogItem.ItemType.DOWNLOAD:
            has_source = bool(download_file or has_existing_file or download_link)
            if not has_source:
                raise forms.ValidationError(
                    'برای نوع «فایل دانلود»، فایل را آپلود کنید یا لینک مستقیم دانلود را وارد کنید.',
                )
            cleaned['sale_mode'] = CatalogItem.SaleMode.REQUEST_ONLY
            cleaned['price'] = None
        return cleaned

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
