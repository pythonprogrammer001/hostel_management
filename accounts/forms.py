from django import forms
from django.contrib.auth.forms import UserCreationForm
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