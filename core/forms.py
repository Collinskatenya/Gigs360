from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm

User = get_user_model()

class SignUpForm(UserCreationForm):
    """
    Signup Form with Role Selection.
    Captures basic info + Business Role immediately.
    """
    # 1. Add Role Selection Dropdown
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

    # 2. Add Styling to existing fields
    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'name@example.com'}))
    first_name = forms.CharField(required=True, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'First Name'}))
    last_name = forms.CharField(required=True, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Last Name'}))

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('username', 'email', 'first_name', 'last_name', 'role')

    def __init__(self, *args, **kwargs):
        """
        Add Bootstrap classes to ALL fields, including inherited ones.
        """
        super(SignUpForm, self).__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            if 'role' not in field_name:
                field.widget.attrs['class'] = 'form-control'
                field.widget.attrs['placeholder'] = field.label

    # 3. Logic to save the Boolean Flags based on the dropdown choice
    def save(self, commit=True):
        user = super().save(commit=False)
        role = self.cleaned_data.get('role')
        
        # Reset flags first
        user.is_vendor = False
        user.is_planner = False
        user.is_client = False

        if role == 'vendor':
            user.is_vendor = True
        elif role == 'agency':
            user.is_planner = True
        else:
            user.is_client = True # Default to Freelancer logic
            
        if commit:
            user.save()
        return user

class UserSettingsForm(forms.ModelForm):
    """
    The Master Form for the 'Settings' page.
    Allows users to update Profile, Business, and Bank details.
    """
    
    # We keep the field definition to retain structure, but make it optional below
    ROLE_CHOICES = [
        ('vendor', 'Vendor (Equipment Rental, Decor)'),
        ('agency', 'Agency (Event Planner, Organizer)'),
        ('freelancer', 'Freelancer (Service Provider)'),
    ]
    selected_role = forms.ChoiceField(
        choices=ROLE_CHOICES, 
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'}),
        label="Primary Business Role"
    )

    class Meta:
        model = User
        fields = [
            'first_name', 'last_name', 'phone_number', 'profile_picture',
            'business_name', 'business_type', 'number_of_employees',
            'bank_name', 'account_number', 'mpesa_number',
            'theme_preference'
        ]
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control'}),
            
            'business_name': forms.TextInput(attrs={'class': 'form-control'}),
            'business_type': forms.Select(attrs={'class': 'form-select'}),
            'number_of_employees': forms.NumberInput(attrs={'class': 'form-control'}),
            
            'bank_name': forms.TextInput(attrs={'class': 'form-control'}),
            'account_number': forms.TextInput(attrs={'class': 'form-control'}),
            'mpesa_number': forms.TextInput(attrs={'class': 'form-control'}),
            
            'theme_preference': forms.Select(attrs={'class': 'form-select'}),
            'profile_picture': forms.FileInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # FIX 1: Make theme_preference optional (since we removed it from HTML)
        self.fields['theme_preference'].required = False

        # FIX 2: Make selected_role optional (since we removed it from HTML to fix redundancy)
        self.fields['selected_role'].required = False

        # Determine current role for pre-selection (if needed)
        if self.instance.pk:
            if self.instance.is_vendor:
                self.fields['selected_role'].initial = 'vendor'
            elif self.instance.is_planner:
                self.fields['selected_role'].initial = 'agency'
            elif self.instance.is_client:
                self.fields['selected_role'].initial = 'freelancer'

    def save(self, commit=True):
        user = super().save(commit=False)
        role = self.cleaned_data.get('selected_role')

        # FIX 3: Only update flags if a role was actually selected/sent
        if role:
            user.is_vendor = False
            user.is_planner = False
            user.is_client = False

            if role == 'vendor':
                user.is_vendor = True
            elif role == 'agency':
                user.is_planner = True
            elif role == 'freelancer':
                user.is_client = True
        
        if commit:
            user.save()
        return user