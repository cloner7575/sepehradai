from django import forms

from instagram.models import ActivityDomain


class ActivityDomainForm(forms.ModelForm):
    class Meta:
        model = ActivityDomain
        fields = ['name']
        widgets = {
            'name': forms.TextInput(
                attrs={
                    'class': 'form-control panel-input',
                    'placeholder': 'مثلاً املاک، آموزش زبان',
                    'maxlength': '120',
                },
            ),
        }
        labels = {'name': 'نام حوزه فعالیت'}

    def clean_name(self):
        name = (self.cleaned_data.get('name') or '').strip()
        if not name:
            raise forms.ValidationError('نام حوزه الزامی است.')
        return name[:120]
