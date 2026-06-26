import json

from django import forms
from django.utils.text import slugify

from balebot.models import CatalogCategory, CatalogItem, CatalogOrder, CatalogSettings
from balebot.widgets import PersianClearableFileInput
from balebot.services.catalog_item_types import ITEM_TYPE_GUIDES, get_item_type_guide
from balebot.services.catalog_page_layout import get_home_blocks, sanitize_home_blocks
from balebot.services.checkout_form import default_checkout_form, sanitize_checkout_form
from balebot.services.jalali_datetime import aware_to_jalali_parts, parse_jalali_date_time

_INPUT = 'form-control panel-input'
_SELECT = 'form-select panel-input'


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
        widget=forms.Select(attrs={'class': _SELECT}),
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
            'payment_card_to_card_enabled',
            'payment_bale_enabled',
            'payment_default_method',
            'admin_notify_chat_id',
            'card_to_card_number',
            'card_to_card_sheba',
            'card_to_card_holder',
            'bale_payment_card_number',
            'bale_payment_card_holder',
            'shipping_mode',
            'shipping_flat_cost',
            'free_shipping_threshold',
            'order_notify_shipped_template',
            'order_notify_delivered_template',
            'abandoned_cart_message_template',
            'abandoned_cart_hours',
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
            'payment_card_to_card_enabled': forms.CheckboxInput(attrs={'class': 'form-check-input', 'role': 'switch'}),
            'payment_bale_enabled': forms.CheckboxInput(attrs={'class': 'form-check-input', 'role': 'switch'}),
            'payment_default_method': forms.Select(attrs={'class': _SELECT}),
            'admin_notify_chat_id': forms.NumberInput(attrs={'class': _INPUT, 'dir': 'ltr'}),
            'card_to_card_number': forms.TextInput(attrs={'class': _INPUT, 'dir': 'ltr', 'placeholder': '6037...'}),
            'card_to_card_sheba': forms.TextInput(attrs={'class': _INPUT, 'dir': 'ltr', 'placeholder': 'IR...'}),
            'card_to_card_holder': forms.TextInput(attrs={'class': _INPUT, 'placeholder': 'نام صاحب حساب'}),
            'bale_payment_card_number': forms.TextInput(attrs={'class': _INPUT, 'dir': 'ltr', 'placeholder': '6037...'}),
            'bale_payment_card_holder': forms.TextInput(attrs={'class': _INPUT, 'placeholder': 'نام دارنده کارت'}),
            'shipping_mode': forms.Select(attrs={'class': _SELECT}),
            'shipping_flat_cost': forms.NumberInput(attrs={'class': _INPUT, 'dir': 'ltr'}),
            'free_shipping_threshold': forms.NumberInput(attrs={'class': _INPUT, 'dir': 'ltr'}),
            'order_notify_shipped_template': forms.Textarea(attrs={'class': _INPUT, 'rows': 2}),
            'order_notify_delivered_template': forms.Textarea(attrs={'class': _INPUT, 'rows': 2}),
            'abandoned_cart_message_template': forms.Textarea(attrs={'class': _INPUT, 'rows': 2}),
            'abandoned_cart_hours': forms.NumberInput(attrs={'class': _INPUT, 'dir': 'ltr', 'min': 1}),
            'hero_title': forms.TextInput(attrs={'class': _INPUT, 'placeholder': 'نام ویترین یا کسب‌وکار'}),
            'hero_subtitle': forms.TextInput(attrs={'class': _INPUT, 'placeholder': 'توضیح کوتاه زیر عنوان'}),
            'logo': PersianClearableFileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
            'hero_background': PersianClearableFileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
        }

    def clean(self):
        cleaned = super().clean()
        admin_on = cleaned.get('payment_admin_enabled')
        card_on = cleaned.get('payment_card_to_card_enabled')
        bale_on = cleaned.get('payment_bale_enabled')
        admin_chat = cleaned.get('admin_notify_chat_id')
        card_number = (cleaned.get('card_to_card_number') or '').strip()
        card_sheba = (cleaned.get('card_to_card_sheba') or '').strip()
        card_holder = (cleaned.get('card_to_card_holder') or '').strip()
        is_enabled = cleaned.get('is_enabled')

        from balebot.services.card_to_card import validate_sheba

        card_digits = ''.join(ch for ch in card_number if ch.isdigit())
        if card_on:
            if len(card_digits) < 16:
                self.add_error('card_to_card_number', 'شماره کارت ۱۶ رقمی معتبر وارد کنید.')
            if not validate_sheba(card_sheba):
                self.add_error('card_to_card_sheba', 'شماره شبا معتبر وارد کنید (IR + ۲۴ رقم).')
            if not card_holder:
                self.add_error('card_to_card_holder', 'نام صاحب حساب الزامی است.')
        if admin_on and not admin_chat:
            self.add_error(
                'admin_notify_chat_id',
                'برای ارسال سبد به ادمین، چت‌آیدی ادمین الزامی است.',
            )
        bale_card = (cleaned.get('bale_payment_card_number') or '').strip()
        if bale_on:
            digits = ''.join(ch for ch in bale_card if ch.isdigit())
            if len(digits) < 16:
                self.add_error(
                    'bale_payment_card_number',
                    'برای پرداخت بله، شماره کارت ۱۶ رقمی معتبر وارد کنید.',
                )

        has_admin = bool(admin_on and admin_chat)
        has_card = bool(card_on and len(card_digits) >= 16 and validate_sheba(card_sheba) and card_holder)
        has_bale = bool(bale_on and len(''.join(ch for ch in bale_card if ch.isdigit())) >= 16)

        if is_enabled and not has_admin and not has_card and not has_bale:
            raise forms.ValidationError(
                'برای فعال‌سازی مینی‌اپ، حداقل یک روش پرداخت را کامل تنظیم کنید '
                '(چت‌آیدی ادمین، کارت به کارت، یا شماره کارت بله).',
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
        if has_card:
            enabled.add(CatalogSettings.PaymentMethod.CARD_TO_CARD)
        if has_bale:
            enabled.add(CatalogSettings.PaymentMethod.BALE)
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
        self.fields['card_to_card_number'].help_text = 'شماره کارت مقصد برای واریز مشتری.'
        self.fields['card_to_card_sheba'].help_text = 'شماره شبا (IR + ۲۴ رقم) — در صفحه پرداخت نمایش داده می‌شود.'
        self.fields['card_to_card_holder'].help_text = 'نام دارنده حساب برای نمایش به مشتری.'
        self.fields['bale_payment_card_number'].help_text = (
            'شماره کارت فروشنده — در بله به‌عنوان provider_token استفاده می‌شود و پول مستقیم به کارت واریز می‌شود.'
        )
        self.fields['bale_payment_card_holder'].help_text = 'برای نمایش به مشتری در توضیحات صورت‌حساب.'
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
        self._filter_payment_default_choices()

    def _filter_payment_default_choices(self):
        field = self.fields.get('payment_default_method')
        if not field:
            return
        enabled: set[str] = set()
        if self.instance and self.instance.pk:
            for value, _ in self.instance.enabled_payment_methods():
                enabled.add(value)
        if enabled:
            field.choices = [
                choice for choice in CatalogSettings.PaymentMethod.choices if choice[0] in enabled
            ]
        else:
            field.choices = list(CatalogSettings.PaymentMethod.choices)
            field.help_text = 'پس از تکمیل حداقل یک روش پرداخت، گزینه‌های این فهرست به‌روز می‌شود.'

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
        widget=forms.Select(attrs={'class': _SELECT}),
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
            'parent': forms.Select(attrs={'class': _SELECT}),
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
        widget=forms.HiddenInput(attrs={'id': 'id_metadata_json'}),
    )
    jalali_flash_sale_start_date = forms.CharField(
        required=False,
        label='تاریخ شروع حراج',
        widget=forms.TextInput(
            attrs={
                'class': _INPUT,
                'placeholder': '۱۴۰۳/۰۸/۱۵',
                'dir': 'ltr',
                'autocomplete': 'off',
                'data-jalali-date': '1',
                'readonly': 'readonly',
            },
        ),
    )
    jalali_flash_sale_start_time = forms.CharField(
        required=False,
        label='ساعت شروع',
        widget=forms.TextInput(
            attrs={
                'class': _INPUT,
                'placeholder': '۰۰:۰۰',
                'dir': 'ltr',
                'autocomplete': 'off',
                'data-jalali-time': '1',
            },
        ),
    )
    jalali_flash_sale_end_date = forms.CharField(
        required=False,
        label='تاریخ پایان حراج',
        widget=forms.TextInput(
            attrs={
                'class': _INPUT,
                'placeholder': '۱۴۰۳/۰۸/۲۰',
                'dir': 'ltr',
                'autocomplete': 'off',
                'data-jalali-date': '1',
                'readonly': 'readonly',
            },
        ),
    )
    jalali_flash_sale_end_time = forms.CharField(
        required=False,
        label='ساعت پایان',
        widget=forms.TextInput(
            attrs={
                'class': _INPUT,
                'placeholder': '۲۳:۵۹',
                'dir': 'ltr',
                'autocomplete': 'off',
                'data-jalali-time': '1',
            },
        ),
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
            'compare_at_price',
            'sale_mode',
            'stock',
            'is_flash_sale',
            'is_active',
            'is_featured',
            'sort_order',
            'metadata_json',
        ]
        widgets = {
            'category': forms.Select(attrs={'class': _SELECT}),
            'title': forms.TextInput(attrs={'class': _INPUT, 'placeholder': 'مثلاً دوره آموزشی طراحی'}),
            'slug': forms.TextInput(attrs={'class': _INPUT, 'dir': 'ltr', 'placeholder': 'course-design'}),
            'short_description': forms.TextInput(attrs={'class': _INPUT, 'placeholder': 'توضیح کوتاه برای لیست محصولات'}),
            'description': forms.Textarea(attrs={'class': _INPUT, 'rows': 5, 'placeholder': 'توضیحات کامل آیتم…'}),
            'item_type': forms.Select(attrs={'class': _SELECT, 'id': 'id_item_type'}),
            'cover': PersianClearableFileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
            'download_file': PersianClearableFileInput(attrs={'class': 'form-control'}),
            'download_link': forms.URLInput(attrs={'class': _INPUT, 'dir': 'ltr', 'placeholder': 'https://...'}),
            'price': forms.NumberInput(attrs={'class': _INPUT, 'dir': 'ltr', 'placeholder': 'به ریال'}),
            'compare_at_price': forms.NumberInput(
                attrs={'class': _INPUT, 'dir': 'ltr', 'placeholder': 'قیمت قبل از تخفیف (ریال)'},
            ),
            'sale_mode': forms.Select(attrs={'class': _SELECT, 'id': 'id_sale_mode'}),
            'stock': forms.NumberInput(attrs={'class': _INPUT, 'dir': 'ltr', 'placeholder': 'خالی = نامحدود'}),
            'is_flash_sale': forms.CheckboxInput(
                attrs={'class': 'form-check-input', 'role': 'switch', 'id': 'id_is_flash_sale'},
            ),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input', 'role': 'switch'}),
            'is_featured': forms.CheckboxInput(attrs={'class': 'form-check-input', 'role': 'switch'}),
            'sort_order': forms.NumberInput(attrs={'class': _INPUT, 'placeholder': '۰'}),
        }

    def __init__(self, *args, workspace=None, platform=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['category'].queryset = CatalogCategory.objects.filter(
            workspace=workspace,
            platform=platform,
            is_active=True,
        ).order_by('sort_order', 'name')
        self.fields['category'].required = False
        self.fields['category'].empty_label = '— بدون دسته‌بندی —'

        self.fields['item_type'].choices = [
            (key, str(guide['label'])) for key, guide in ITEM_TYPE_GUIDES.items()
        ]
        if self.instance.pk and self.instance.item_type == 'portfolio':
            self.initial['item_type'] = CatalogItem.ItemType.SHOWCASE

        labels = {
            'category': 'دسته‌بندی',
            'title': 'عنوان',
            'slug': 'نامک آدرس',
            'short_description': 'توضیح کوتاه',
            'description': 'توضیح کامل',
            'item_type': 'نوع آیتم',
            'cover': 'تصویر کاور',
            'download_file': 'فایل دانلود',
            'download_link': 'لینک مستقیم دانلود',
            'price': 'قیمت (ریال)',
            'compare_at_price': 'قیمت قبل از تخفیف',
            'sale_mode': 'نحوه فروش',
            'stock': 'موجودی',
            'is_flash_sale': 'قرارگیری در حراج',
            'is_active': 'نمایش در ویترین',
            'is_featured': 'آیتم ویژه',
            'sort_order': 'ترتیب نمایش',
        }
        for name, label in labels.items():
            if name in self.fields:
                self.fields[name].label = label

        self.fields['slug'].help_text = 'برای آدرس صفحه آیتم — اگر خالی بماند از عنوان ساخته می‌شود.'
        self.fields['cover'].help_text = 'در لیست و صفحه آیتم نمایش داده می‌شود.'
        self.fields['download_file'].help_text = 'فایل روی سرور شما ذخیره می‌شود.'
        self.fields['download_link'].help_text = 'یا لینک مستقیم فایل (گوگل‌درایو، دراپ‌باکس، CDN و…).'
        self.fields['item_type'].help_text = 'نوع آیتم مشخص می‌کند کاربر بتواند بخرد، دانلود کند یا درخواست بدهد.'
        self.fields['sale_mode'].help_text = 'مشخص کنید کاربر بتواند بخرد، درخواست بدهد یا هر دو.'
        self.fields['price'].help_text = 'برای فروش الزامی است. مقدار به ریال وارد شود.'
        self.fields['stock'].help_text = 'اختیاری — خالی بگذارید اگر محدودیت موجودی ندارید.'
        self.fields['sort_order'].help_text = 'عدد کوچک‌تر زودتر نمایش داده می‌شود.'
        self.fields['is_active'].help_text = 'غیرفعال = در مینی‌اپ دیده نمی‌شود.'
        self.fields['is_featured'].help_text = 'در بخش «ویژه» صفحه اصلی نمایش داده می‌شود.'
        self.fields['compare_at_price'].help_text = 'برای نمایش خط‌خورده در کنار قیمت فعلی.'
        self.fields['is_flash_sale'].help_text = 'آیتم در صفحه حراج و کاروسل حراج نمایش داده می‌شود.'

        if self.instance.pk:
            self.fields['metadata_json'].initial = json.dumps(
                self.instance.metadata or {},
                ensure_ascii=False,
                indent=2,
            )
            if self.instance.flash_sale_starts_at:
                d, t = aware_to_jalali_parts(self.instance.flash_sale_starts_at)
                self.fields['jalali_flash_sale_start_date'].initial = d
                self.fields['jalali_flash_sale_start_time'].initial = t
            if self.instance.flash_sale_ends_at:
                d, t = aware_to_jalali_parts(self.instance.flash_sale_ends_at)
                self.fields['jalali_flash_sale_end_date'].initial = d
                self.fields['jalali_flash_sale_end_time'].initial = t

    def clean_download_link(self):
        link = (self.cleaned_data.get('download_link') or '').strip()
        return link

    def clean(self):
        cleaned = super().clean()
        item_type = cleaned.get('item_type')
        if item_type == 'portfolio':
            item_type = CatalogItem.ItemType.SHOWCASE
            cleaned['item_type'] = item_type

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
        elif item_type == CatalogItem.ItemType.SHOWCASE:
            cleaned['sale_mode'] = CatalogItem.SaleMode.REQUEST_ONLY
            cleaned['price'] = None
        elif item_type == CatalogItem.ItemType.VIDEO:
            if cleaned.get('sale_mode') == CatalogItem.SaleMode.BUYABLE and not cleaned.get('price'):
                self.add_error('price', 'برای فروش دوره، قیمت را وارد کنید.')
        elif item_type == CatalogItem.ItemType.PRODUCT:
            if cleaned.get('sale_mode') != CatalogItem.SaleMode.REQUEST_ONLY and not cleaned.get('price'):
                self.add_error('price', 'برای فروش محصول، قیمت را وارد کنید.')

        if cleaned.get('is_flash_sale'):
            for label, d_key, t_key in (
                ('شروع', 'jalali_flash_sale_start_date', 'jalali_flash_sale_start_time'),
                ('پایان', 'jalali_flash_sale_end_date', 'jalali_flash_sale_end_time'),
            ):
                j_date = (cleaned.get(d_key) or '').strip()
                j_time = (cleaned.get(t_key) or '').strip()
                if j_date and not j_time:
                    j_time = '00:00' if d_key.endswith('start_date') else '23:59'
                if j_date:
                    try:
                        dt = parse_jalali_date_time(j_date, j_time or '00:00')
                        if d_key.endswith('start_date'):
                            cleaned['flash_sale_starts_at'] = dt
                        else:
                            cleaned['flash_sale_ends_at'] = dt
                    except ValueError as exc:
                        self.add_error(d_key, str(exc))
                elif j_time:
                    self.add_error(d_key, f'تاریخ {label} حراج را انتخاب کنید.')
            start = cleaned.get('flash_sale_starts_at')
            end = cleaned.get('flash_sale_ends_at')
            if start and end and start >= end:
                self.add_error('jalali_flash_sale_end_date', 'تاریخ پایان باید بعد از شروع باشد.')
        else:
            cleaned['flash_sale_starts_at'] = None
            cleaned['flash_sale_ends_at'] = None

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
            raise forms.ValidationError('ویژگی‌های سفارشی نامعتبر است.') from e
        if not isinstance(data, dict):
            raise forms.ValidationError('ویژگی‌های سفارشی نامعتبر است.')
        cleaned = {}
        for key, value in data.items():
            label = str(key).strip()
            val = str(value).strip() if value is not None else ''
            if label and val:
                cleaned[label[:120]] = val[:500]
        return cleaned

    def save(self, commit=True):
        obj = super().save(commit=False)
        obj.metadata = self.cleaned_data.get('metadata_json') or {}
        if 'flash_sale_starts_at' in self.cleaned_data:
            obj.flash_sale_starts_at = self.cleaned_data.get('flash_sale_starts_at')
        if 'flash_sale_ends_at' in self.cleaned_data:
            obj.flash_sale_ends_at = self.cleaned_data.get('flash_sale_ends_at')
        if not self.cleaned_data.get('is_flash_sale'):
            obj.flash_sale_starts_at = None
            obj.flash_sale_ends_at = None
        if commit:
            obj.save()
        return obj


class CatalogOrderUpdateForm(forms.Form):
    status = forms.ChoiceField(
        label='وضعیت پرداخت',
        choices=CatalogOrder.Status.choices,
        widget=forms.Select(attrs={'class': _SELECT}),
    )
    fulfillment_status = forms.ChoiceField(
        label='وضعیت ارسال / تحویل',
        choices=CatalogOrder.FulfillmentStatus.choices,
        widget=forms.Select(attrs={'class': _SELECT}),
    )
    tracking_code = forms.CharField(
        required=False,
        label='کد رهگیری پستی',
        widget=forms.TextInput(attrs={'class': _INPUT, 'dir': 'ltr'}),
    )
    admin_note = forms.CharField(
        required=False,
        label='یادداشت ادمین',
        widget=forms.Textarea(attrs={
            'class': _INPUT,
            'rows': 3,
            'placeholder': 'یادداشت داخلی برای تیم',
        }),
    )
    note = forms.CharField(
        required=False,
        label='یادداشت سفارش',
        widget=forms.Textarea(attrs={
            'class': _INPUT,
            'rows': 4,
            'placeholder': 'یادداشت برای خودتان — در مینی‌اپ نمایش داده نمی‌شود.',
        }),
    )
