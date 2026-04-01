from django import forms
from .models import Gallery

class GalleryForm(forms.ModelForm):
    class Meta:
        model = Gallery
        # We now include 'event' in the fields so they can choose to lock it to an invoice!
        fields = ['title', 'event', 'event_date', 'client_email', 'access_pin', 'cover_image']
        
        # Premium Gigs360 UI Styling matching your dashboard
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control border-0 bg-transparent', 
                'placeholder': 'e.g., The Smith Wedding'
            }),
            'event': forms.Select(attrs={
                'class': 'form-control border-0 bg-transparent'
            }),
            'event_date': forms.DateInput(attrs={
                'class': 'form-control border-0 bg-transparent', 
                'type': 'date'
            }),
            'client_email': forms.EmailInput(attrs={
                'class': 'form-control border-0 bg-transparent', 
                'placeholder': 'client@example.com'
            }),
            'access_pin': forms.TextInput(attrs={
                'class': 'form-control border-0 bg-transparent', 
                'placeholder': 'Optional 6-digit PIN', 
                'maxlength': '6'
            }),
            'cover_image': forms.FileInput(attrs={
                'class': 'form-control border-0 bg-transparent'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Rename the default "---------" empty choice to something SaaS-friendly
        if 'event' in self.fields:
            self.fields['event'].empty_label = "None (Standalone Pixieset Mode)"