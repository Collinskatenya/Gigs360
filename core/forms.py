from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import get_user_model  # <--- NEW IMPORT

# Get the correct user model (core.User) dynamically
User = get_user_model()

class SignUpForm(UserCreationForm):
    ACCOUNT_TYPES = [
        ('freelancer', 'Freelancer (Photographer, DJ, MC)'),
        ('vendor', 'Vendor (Gear Rental, Decor, Catering)'),
        ('agency', 'Agency (Event Planner, Marketing)'),
    ]

    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'name@example.com'}))
    first_name = forms.CharField(required=True, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'First Name'}))
    last_name = forms.CharField(required=True, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Last Name'}))
    
    account_type = forms.ChoiceField(
        choices=ACCOUNT_TYPES, 
        widget=forms.Select(attrs={'class': 'form-select', 'style': 'height: 50px;'})
    )

    class Meta:
        model = User  # <--- Points to your Custom User Model now
        fields = ('username', 'email', 'first_name', 'last_name', 'account_type')

    def __init__(self, *args, **kwargs):
        super(SignUpForm, self).__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            if field_name != 'account_type': 
                field.widget.attrs['class'] = 'form-control'
                field.widget.attrs['placeholder'] = field.label