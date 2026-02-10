from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm
from .models import UserProfile

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
            # We must use getattr because the signal creates it instantly
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
# 2. SETTINGS FORMS (Split for Security)
# ==========================================

class UserUpdateForm(forms.ModelForm):
    """Updates Login Details (Name, Email)"""
    email = forms.EmailField(widget=forms.EmailInput(attrs={'class': 'form-control'}))
    first_name = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control'}))
    last_name = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control'}))

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']


class UserProfileForm(forms.ModelForm):
    """
    Updates Business Data (KYC, Banking, Logos).
    Connects to the UserProfile model.
    """
    # Custom Date Picker
    dob = forms.DateField(
        required=False, 
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        label="Date of Birth"
    )
    # Custom Color Picker
    invoice_color_theme = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'type': 'color', 'class': 'form-control form-control-color', 'title': 'Choose your brand color'}),
        label="Invoice Brand Color"
    )

    class Meta:
        model = UserProfile
        fields = [
            'profile_picture', 'company_logo', 
            'phone_number', 'bio',
            'business_name', 'business_category',
            'kra_pin', 'id_number', 'dob',
            'bank_name', 'account_number', 'mpesa_number',
            'invoice_color_theme'
        ]
        
    def __init__(self, *args, **kwargs):
        super(UserProfileForm, self).__init__(*args, **kwargs)
        # Apply bootstrap style to all standard inputs
        for field in self.fields:
            if 'class' not in self.fields[field].widget.attrs:
                self.fields[field].widget.attrs.update({'class': 'form-control'})