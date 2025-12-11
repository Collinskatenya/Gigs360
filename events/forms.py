from django import forms
from django.db.models import Q  # <--- NEW: Required for the safe filter logic
from .models import Event
# Ensure 'inventory' app exists and has 'InventoryItem' model
from inventory.models import InventoryItem 

class EventForm(forms.ModelForm):
    # This is your "Shopping Cart"
    items = forms.ModelMultipleChoiceField(
        queryset=InventoryItem.objects.none(), # Empty initially
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
        required=False,
        label="Select Equipment Needed"
    )

    class Meta:
        model = Event
        fields = [
            'title', 'event_type', 'start_time', 'end_time', 'location', 
            'description', 'client_name', 'client_contact', 'staff_in_charge',
            'is_completed'
        ]
        
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Wedding at Karen Manor'}),
            'event_type': forms.Select(attrs={'class': 'form-select'}),
            'location': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Venue Location'}),
            'client_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Client Name'}),
            'client_contact': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Phone/Email'}),
            'staff_in_charge': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Lead Creative'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            
            # HTML5 Date Pickers
            'start_time': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'end_time': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'is_completed': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        # We pop 'user' safely before initializing the form
        user = kwargs.pop('user', None) 
        super(EventForm, self).__init__(*args, **kwargs)

        if user:
            # --- THE FIX FOR EDITING ---
            # 1. Start by finding items that are AVAILABLE and owned by this user
            query = Q(owner=user, status='AVAILABLE')
            
            # 2. If we are Editing (instance.pk exists), ALSO include items 
            #    that are ALREADY assigned to this specific event.
            if self.instance.pk:
                current_item_ids = self.instance.manifest.values_list('item_id', flat=True)
                query = query | Q(id__in=current_item_ids)
            
            # 3. Apply the smart filter
            self.fields['items'].queryset = InventoryItem.objects.filter(query)
            
        # If we are editing an existing event, we need to pre-check the boxes
        if self.instance.pk:
            current_items = self.instance.manifest.values_list('item_id', flat=True)
            self.fields['items'].initial = current_items