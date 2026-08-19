from decimal import Decimal

from django import forms

from .models import SavingsAccount


class SavingsAccountForm(forms.ModelForm):
    initial_deposit = forms.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=Decimal('1000.00'),
        label='Initial Deposit (min ₹1000)',
        error_messages={
            'required': 'Initial deposit is required.',
            'min_value': 'Minimum initial deposit is ₹1000.',
            'invalid': 'Enter a valid amount.',
        },
        widget=forms.NumberInput(attrs={
            'step': '0.01',
            'min': '1000',
            'class': 'form-control',
            'placeholder': '1000.00',
        }),
    )

    class Meta:
        model = SavingsAccount
        fields = [
            'full_name',
            'mobile_number',
            'email',
            'address',
            'aadhaar_number',
            'pan_number',
            'mpin',
            'tpin',
        ]
        widgets = {
            'full_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Rahul Sharma'}),
            'mobile_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '9876543210'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'you@email.com'}),
            'address': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'House no, Street, City, State, PIN'}),
            'aadhaar_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '123412341234'}),
            'pan_number': forms.TextInput(attrs={'class': 'form-control text-uppercase', 'placeholder': 'ABCDE1234F'}),
            'mpin': forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': '4-digit MPIN', 'maxlength': '4'}),
            'tpin': forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': '4-digit TPIN', 'maxlength': '4'}),
        }
