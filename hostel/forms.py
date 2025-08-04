from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import (
    Room, GuestProfile, SecurityDeposit, MonthlyBill, 
    Expense, Issue
)
from accounts.models import CustomUser


class GuestCheckInForm(forms.Form):
    """
    Form for checking in new guests
    """
    # User details
    username = forms.CharField(max_length=150)
    password = forms.CharField(widget=forms.PasswordInput())
    first_name = forms.CharField(max_length=30)
    last_name = forms.CharField(max_length=30)
    email = forms.EmailField()
    phone = forms.CharField(max_length=15)
    address = forms.CharField(widget=forms.Textarea(attrs={'rows': 3}))
    
    # Guest profile details
    room = forms.ModelChoiceField(queryset=Room.objects.none())
    rent_amount = forms.DecimalField(max_digits=10, decimal_places=2)
    check_in_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
    emergency_contact_name = forms.CharField(max_length=100)
    emergency_contact_phone = forms.CharField(max_length=15)
    
    # ID Proof
    id_proof_type = forms.ChoiceField(choices=GuestProfile._meta.get_field('id_proof_type').choices)
    id_proof_number = forms.CharField(max_length=50)
    id_proof_document = forms.FileField(required=False)
    profile_photo = forms.ImageField(required=False)
    
    # Security deposit
    security_deposit = forms.DecimalField(max_digits=10, decimal_places=2)
    deposit_paid = forms.BooleanField(required=False, initial=True)
    
    def __init__(self, *args, **kwargs):
        pg = kwargs.pop('pg', None)
        super().__init__(*args, **kwargs)
        
        if pg:
            # Filter rooms by PG and availability
            self.fields['room'].queryset = Room.objects.filter(
                pg=pg, 
                is_available=True
            )
        
        # Add Bootstrap classes
        for field_name, field in self.fields.items():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs['class'] = 'form-check-input'
            else:
                field.widget.attrs['class'] = 'form-control'
    
    def clean_username(self):
        username = self.cleaned_data['username']
        if CustomUser.objects.filter(username=username).exists():
            raise forms.ValidationError('Username already exists.')
        return username
    
    def clean_email(self):
        email = self.cleaned_data['email']
        if CustomUser.objects.filter(email=email).exists():
            raise forms.ValidationError('Email already exists.')
        return email


class RoomForm(forms.ModelForm):
    """
    Form for creating/updating rooms
    """
    class Meta:
        model = Room
        fields = ['room_number', 'capacity', 'rent_amount', 'meter_type', 'is_available']
        widgets = {
            'room_number': forms.TextInput(attrs={'class': 'form-control'}),
            'capacity': forms.NumberInput(attrs={'class': 'form-control'}),
            'rent_amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'meter_type': forms.Select(attrs={'class': 'form-control'}),
            'is_available': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class ExpenseForm(forms.ModelForm):
    """
    Form for adding expenses
    """
    class Meta:
        model = Expense
        fields = ['category', 'amount', 'date', 'description', 'receipt']
        widgets = {
            'category': forms.Select(attrs={'class': 'form-control'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'receipt': forms.FileInput(attrs={'class': 'form-control'}),
        }


class IssueForm(forms.ModelForm):
    """
    Form for creating issues (used by guests)
    """
    class Meta:
        model = Issue
        fields = ['title', 'description', 'category', 'priority']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'category': forms.Select(attrs={'class': 'form-control'}),
            'priority': forms.Select(attrs={'class': 'form-control'}),
        }


class MonthlyBillForm(forms.ModelForm):
    """
    Form for creating/updating monthly bills
    """
    class Meta:
        model = MonthlyBill
        fields = [
            'rent_amount', 'electricity_units', 'electricity_rate', 
            'water_charges', 'maintenance_charges', 'other_charges', 
            'other_charges_description', 'due_date'
        ]
        widgets = {
            'rent_amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'electricity_units': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'electricity_rate': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'water_charges': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'maintenance_charges': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'other_charges': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'other_charges_description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'due_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }


class GuestProfileUpdateForm(forms.ModelForm):
    """
    Form for updating guest profile information
    """
    class Meta:
        model = GuestProfile
        fields = [
            'emergency_contact_name', 'emergency_contact_phone',
            'profile_photo'
        ]
        widgets = {
            'emergency_contact_name': forms.TextInput(attrs={'class': 'form-control'}),
            'emergency_contact_phone': forms.TextInput(attrs={'class': 'form-control'}),
            'profile_photo': forms.FileInput(attrs={'class': 'form-control'}),
        }