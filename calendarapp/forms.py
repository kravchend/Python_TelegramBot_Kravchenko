from django import forms
from .models import Event, User


class EventForm(forms.ModelForm):
    class Meta:
        model = Event
        fields = ['name', 'date', 'time', 'details', 'is_public']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'time': forms.TimeInput(attrs={
                'type': 'time',
                'class': 'form-control',
                'value': '12:00'
            }),
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Введите название события',
                'value': 'Новое событие',
            }),
            'details': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'is_public': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class SiteRegistrationForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control'}), label="Пароль")
    password_confirm = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control'}),
                                       label="Подтвердите пароль")

    class Meta:
        model = User
        fields = ['username', 'email', 'password']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
        }

    def clean_password_confirm(self):
        password = self.cleaned_data.get('password')
        password_confirm = self.cleaned_data.get('password_confirm')
        if password and password_confirm and password != password_confirm:
            raise forms.ValidationError("Пароли не совпадают!")
        return password_confirm
