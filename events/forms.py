from django import forms
from .models import Event
from inventory.models import InventoryItem

class EventForm(forms.ModelForm):
    # This creates a checklist of available items
    # We set queryset to none() initially for security; it gets populated in __init__
    items = forms.ModelMultipleChoiceField(
        queryset=InventoryItem.objects.none(), 
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
        required=False,
        label="Select Equipment Needed"
    )

    class Meta:
        model = Event
        fields = ['title', 'event_type', 'start_date', 'end_date', 'location', 
                  'client_name', 'client_contact', 'staff_in_charge', 'items']
        
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Wedding at Karen Manor'}),
            'event_type': forms.Select(attrs={'class': 'form-select'}),
            'location': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Venue Location'}),
            'client_name': forms.TextInput(attrs={'class': 'form-control'}),
            'client_contact': forms.TextInput(attrs={'class': 'form-control'}),
            'staff_in_charge': forms.TextInput(attrs={'class': 'form-control'}),
            # HTML5 Date Pickers
            'start_date': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'end_date': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
        }

    def __init__(self, *args, **kwargs):
        """
        Overriding init to filter the Inventory items by the logged-in user.
        """
        # Pop the user from kwargs so the form doesn't crash
        user = kwargs.pop('user', None) 
        super(EventForm, self).__init__(*args, **kwargs)

        if user:
            # FIX: Only show items owned by the logged-in user that are AVAILABLE
            self.fields['items'].queryset = InventoryItem.objects.filter(
                owner=user, 
                status='AVAILABLE'
            )