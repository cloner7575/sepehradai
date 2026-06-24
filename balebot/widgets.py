from django import forms


class PersianClearableFileInput(forms.ClearableFileInput):
    initial_text = 'فایل فعلی'
    input_text = 'تغییر فایل'
    clear_checkbox_label = 'حذف فایل'
