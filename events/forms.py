from django import forms
from .models import Event
# Using string reference to avoid circular imports is safer, 
# but direct import works if your project structure is standard.
from inventory.models import InventoryItem

class EventForm(forms.ModelForm):
    # This creates the "Shopping Cart" checklist.
    # It is NOT a direct field of the Event model anymore, but a helper 
    # that we use in the view to create 'EventItem' records.
    items = forms.ModelMultipleChoiceField(
        queryset=InventoryItem.objects.none(), # Empty by default, filled in __init__
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
        required=False,
        label="Select Equipment Needed"
    )

    class Meta:
        model = Event
        # FIX 1: Updated 'start_date'/'end_date' to 'start_time'/'end_time' to match Model.
        # FIX 2: Removed 'items' from this list because it is not a direct database column on Event.
        fields = [
            'title', 'event_type', 'start_time', 'end_time', 'location', 
            'description', 'client_name', 'client_contact', 'staff_in_charge'
        ]
        
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Wedding at Karen Manor'}),
            'event_type': forms.Select(attrs={'class': 'form-select'}),
            'location': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Venue Location'}),
            'client_name': forms.TextInput(attrs={'class': 'form-control'}),
            'client_contact': forms.TextInput(attrs={'class': 'form-control'}),
            'staff_in_charge': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            
            # FIX 3: HTML5 Date Pickers matched to new field names
            'start_time': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'end_time': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
        }

    def __init__(self, *args, **kwargs):
        """
        Overriding init to filter the Inventory items by the logged-in user.
        """
        # Pop the user from kwargs so the form doesn't crash
        user = kwargs.pop('user', None) 
        super(EventForm, self).__init__(*args, **kwargs)

        if user:
            # FIX 4: Only show items owned by the logged-in user that are AVAILABLE
            self.fields['items'].queryset = InventoryItem.objects.filter(
                owner=user, 
                status='AVAILABLE'
            )