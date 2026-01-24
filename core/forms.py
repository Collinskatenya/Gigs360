from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm

User = get_user_model()

# ==========================================
# 1. SIGNUP FORM (PUBLIC)
# ==========================================

class SignUpForm(UserCreationForm):
    """
    Public Signup Form.
    RESTRICTED: Only allows Clients (Freelancers, Vendors, Agencies).
    Staff accounts must be created by Super Admin.
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

    email = forms.EmailField(
        required=True, 
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'name@example.com'})
    )
    first_name = forms.CharField(
        required=True, 
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'First Name'})
    )
    last_name = forms.CharField(
        required=True, 
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Last Name'})
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('username', 'email', 'first_name', 'last_name', 'role')

    def __init__(self, *args, **kwargs):
        super(SignUpForm, self).__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            if 'role' not in field_name:
                field.widget.attrs['class'] = 'form-control'
                field.widget.attrs['placeholder'] = field.label

    # --- NEW: PREVENT DUPLICATE EMAILS ---
    def clean_email(self):
        email = self.cleaned_data.get('email')
        # Check if email exists in DB (Case insensitive)
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("This email address is already registered. Please login instead.")
        return email

    def save(self, commit=True):
        """
        Maps the dropdown choice to the specific User Boolean flags.
        """
        user = super().save(commit=False)
        role = self.cleaned_data.get('role')
        
        # 1. Reset all Client flags (Safe default)
        user.is_vendor = False
        user.is_planner = False
        user.is_client = False
        
        # 2. Force Staff flags to False (Security)
        user.is_staff = False
        user.is_superuser = False

        # 3. Set the specific flag
        if role == 'vendor':
            user.is_vendor = True
        elif role == 'agency':
            user.is_planner = True
        else:
            user.is_client = True 
            
        if commit:
            user.save()
        return user


# ==========================================
# 2. SETTINGS FORM (AUTHENTICATED)
# ==========================================

class UserSettingsForm(forms.ModelForm):
    """
    Settings Form for authenticated users.
    Handles Profile Picture, Bio, and Business Data.
    Includes new Invoice Theme and Birthday fields.
    """
    class Meta:
        model = User
        fields = [
            'first_name', 'last_name', 'phone_number', 'profile_picture',
            'business_name', 'business_type', 'number_of_employees',
            'bank_name', 'account_number', 'mpesa_number',
            # --- NEW FIELDS ADDED ---
            'invoice_color_theme', 'date_of_birth'
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
            
            'profile_picture': forms.FileInput(attrs={'class': 'form-control'}),
            
            # --- NEW WIDGETS ---
            'invoice_color_theme': forms.TextInput(attrs={
                'type': 'color', 
                'class': 'form-control form-control-color', 
                'title': 'Choose your invoice theme color'
            }),
            'date_of_birth': forms.DateInput(attrs={
                'type': 'date', 
                'class': 'form-control'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Ensure optional fields don't block validation
        self.fields['profile_picture'].required = False
        self.fields['business_name'].required = False
        self.fields['business_type'].required = False
        self.fields['invoice_color_theme'].required = False
        self.fields['date_of_birth'].required = False