from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.core.exceptions import ValidationError
from .models import CustomUser


class PGAdminRegistrationForm(UserCreationForm):
    """
    Registration form for PG Admins
    """
    first_name = forms.CharField(max_length=30, required=True)
    last_name = forms.CharField(max_length=30, required=True)
    email = forms.EmailField(required=True)
    phone = forms.CharField(max_length=15, required=True)
    address = forms.CharField(widget=forms.Textarea(attrs={'rows': 3}), required=True)
    
    # PG specific fields
    pg_name = forms.CharField(max_length=100, required=True, label='PG/Hostel Name')
    pg_address = forms.CharField(widget=forms.Textarea(attrs={'rows': 3}), required=True, label='PG Address')
    contact_phone = forms.CharField(max_length=15, required=True, label='PG Contact Phone')
    contact_email = forms.EmailField(required=True, label='PG Contact Email')
    
    class Meta:
        model = CustomUser
        fields = ('username', 'first_name', 'last_name', 'email', 'phone', 'address', 'password1', 'password2')
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add Bootstrap classes
        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = 'form-control'
            if field.required:
                field.widget.attrs['required'] = True
    
    def clean_username(self):
        username = self.cleaned_data.get('username')
        if username and CustomUser.objects.filter(username=username).exists():
            raise ValidationError('This username is already taken. Please choose a different one.')
        return username
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email and CustomUser.objects.filter(email=email).exists():
            raise ValidationError('This email is already registered. Please use a different email.')
        return email
    
    def clean_contact_email(self):
        contact_email = self.cleaned_data.get('contact_email')
        if contact_email and CustomUser.objects.filter(email=contact_email).exists():
            raise ValidationError('This email is already registered. Please use a different email.')
        return contact_email


class GuestRegistrationForm(UserCreationForm):
    """
    Registration form for Guests (used by PG Admin)
    """
    first_name = forms.CharField(max_length=30, required=True)
    last_name = forms.CharField(max_length=30, required=True)
    email = forms.EmailField(required=True)
    phone = forms.CharField(max_length=15, required=True)
    address = forms.CharField(widget=forms.Textarea(attrs={'rows': 3}), required=True)
    
    class Meta:
        model = CustomUser
        fields = ('username', 'first_name', 'last_name', 'email', 'phone', 'address', 'password1', 'password2')
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add Bootstrap classes
        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = 'form-control'
            if field.required:
                field.widget.attrs['required'] = True