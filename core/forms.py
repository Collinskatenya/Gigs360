from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm
from django.core.validators import RegexValidator
from .models import UserProfile
from datetime import date, timedelta

User = get_user_model()

# ==========================================
# 1. SIGNUP FORM (Smart Link to Profile)
# ==========================================

class SignUpForm(UserCreationForm):
    """
    Creates the User AND automatically sets the Role in UserProfile.
    """
    ROLE_CHOICES = [
        ('freelancer', 'Freelancer (Photographer, DJ, Model)'),
        ('vendor', 'Vendor (Gear Rental, Decor, Catering)'),
        ('agency', 'Agency (Event Planner, Organizer)'),
    ]
    
    role = forms.ChoiceField(
        choices=ROLE_CHOICES, 
        widget=forms.Select(attrs={'class': 'form-select', 'style': 'height: 58px;'}),
        label="I want to join as a..."
    )

    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'name@example.com'}))
    first_name = forms.CharField(required=True, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'First Name'}))
    last_name = forms.CharField(required=True, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Last Name'}))

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('username', 'email', 'first_name', 'last_name')

    def __init__(self, *args, **kwargs):
        super(SignUpForm, self).__init__(*args, **kwargs)
        for field in self.fields:
            if field != 'role':
                self.fields[field].widget.attrs['class'] = 'form-control'

    def save(self, commit=True):
        # 1. Save the User Auth Data
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        
        if commit:
            user.save()
            # 2. Update the Linked Profile (Created by Signal)
            if hasattr(user, 'userprofile'):
                profile = user.userprofile
                role = self.cleaned_data.get('role')
                
                # Reset flags
                profile.is_freelancer = False
                profile.is_vendor = False
                profile.is_agency = False
                
                # Set new flag
                if role == 'vendor':
                    profile.is_vendor = True
                elif role == 'agency':
                    profile.is_agency = True
                else:
                    profile.is_freelancer = True
                
                profile.save()
        return user


# ==========================================
# 2. COMMAND VAULT FORMS (Segregated for UI & Security)
# ==========================================

class UserBaseUpdateForm(forms.ModelForm):
    """Updates Core Login Details (Name, Email)"""
    email = forms.CharField(
        disabled=True, 
        widget=forms.EmailInput(attrs={'class': 'form-control bg-light text-muted', 'readonly': 'readonly'})
    )
    first_name = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'First Name'}))
    last_name = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Last Name'}))

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']


class ProfileDemographicsForm(forms.ModelForm):
    """Tab 1: Personal Demographics"""
    
    # 🚨 INNOVATION: Clean Custom Image Widget (Hides messy default button)
    profile_picture = forms.ImageField(
        required=False,
        widget=forms.FileInput(attrs={'class': 'd-none', 'id': 'id_profile_picture_input'}),
        label="Profile Photo"
    )

    # 🚨 INNOVATION: HTML5 Calendar locked to 18+ years ago
    dob = forms.DateField(
        required=False, 
        widget=forms.DateInput(attrs={
            'type': 'date', 
            'class': 'form-control',
            'max': (date.today() - timedelta(days=18*365.25)).strftime('%Y-%m-%d')
        }),
        label="Date of Birth"
    )

    class Meta:
        model = UserProfile
        fields = [
            'profile_picture', 'middle_name', 'gender', 
            'phone_number', 'dob', 'bio'
        ]
        widgets = {
            'gender': forms.Select(attrs={'class': 'form-select'}),
            'bio': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Tell clients about yourself...'}),
            'middle_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Middle Name (Optional)'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def clean_dob(self):
        # 🚨 SECURITY: Backend execution to ensure users cannot bypass the HTML calendar lock
        dob = self.cleaned_data.get('dob')
        if dob:
            age = (date.today() - dob).days / 365.25
            if age < 18:
                raise forms.ValidationError("You must be at least 18 years old to register on Gigs360.")
        return dob


class BusinessOperationsForm(forms.ModelForm):
    """Tab 2: The MIS Engine (Location, Scale, Category)"""
    
    # 🚨 INNOVATION: Clean Custom Image Widget
    company_logo = forms.ImageField(
        required=False,
        widget=forms.FileInput(attrs={'class': 'd-none', 'id': 'id_company_logo_input'}),
        label="Company Logo"
    )

    invoice_color_theme = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'type': 'color', 'class': 'form-control form-control-color'}),
        label="Default Brand Color"
    )

    class Meta:
        model = UserProfile
        fields = [
            'company_logo', 'business_name', 'business_category',
            'current_city', 'county_of_residence', 'office_number', 
            'employee_count', 'invoice_color_theme'
        ]
        widgets = {
            'business_name': forms.TextInput(attrs={'class': 'form-control'}),
            'business_category': forms.Select(attrs={'class': 'form-select'}),
            'current_city': forms.TextInput(attrs={'class': 'form-control'}),
            'county_of_residence': forms.TextInput(attrs={'class': 'form-control'}),
            'office_number': forms.TextInput(attrs={'class': 'form-control'}),
            'employee_count': forms.Select(attrs={'class': 'form-select'}),
        }


class LegalIdentityForm(forms.ModelForm):
    """Tab 3: The Zero-Upload KYC Vault with Auto-Lock Logic"""
    
    # 🚨 SECURITY: Add Password Confirmation Field
    current_password = forms.CharField(
        label="Confirm Password to Save",
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Enter current password'}),
        help_text="Required to update sensitive legal details."
    )

    class Meta:
        model = UserProfile
        fields = ['id_number', 'kra_pin']
        widgets = {
            'id_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. 12345678'}),
            'kra_pin': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. A000000000Z'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 🚨 THE INNOVATION: The Identity Lock Protocol
        if self.instance and self.instance.is_identity_locked:
            self.fields['id_number'].disabled = True
            self.fields['id_number'].widget.attrs.update({'class': 'form-control bg-light text-muted', 'readonly': 'readonly'})
            self.fields['id_number'].help_text = "🔒 Verified and Locked."
            
            self.fields['kra_pin'].disabled = True
            self.fields['kra_pin'].widget.attrs.update({'class': 'form-control bg-light text-muted', 'readonly': 'readonly'})
            self.fields['kra_pin'].help_text = "🔒 Verified and Locked."
            
            self.fields['current_password'].required = False # Password not required if fields are already locked


class FinancialPayoutForm(forms.ModelForm):
    """Tab 4: Financial Routing"""
    
    # 🚨 SECURITY: Add Password Confirmation Field
    current_password = forms.CharField(
        label="Confirm Password to Save",
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Enter current password'}),
        help_text="Required to update financial routing."
    )

    # 🚨 INNOVATION: Restricts Bank Name to Letters and Spaces ONLY
    bank_name = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. KCB Bank or Equity'}),
        validators=[RegexValidator(r'^[a-zA-Z\s]*$', message="Bank name must only contain letters.")]
    )

    class Meta:
        model = UserProfile
        fields = ['bank_name', 'account_number', 'mpesa_number']
        widgets = {
            'account_number': forms.TextInput(attrs={'class': 'form-control'}),
            'mpesa_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Till or Phone Number'}),
        }