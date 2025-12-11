from django import forms
from django.db.models import Q 
from .models import Event
from inventory.models import InventoryItem 

class EventForm(forms.ModelForm):
    # The "Shopping Cart" for gear
    items = forms.ModelMultipleChoiceField(
        queryset=InventoryItem.objects.none(), # Empty initially, populated in __init__
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
        required=False,
        label="Select Equipment Needed"
    )

    class Meta:
        model = Event
        # Includes Logistics, Traceability, and the NEW Financial fields
        fields = [
            'title', 'event_type', 'start_time', 'end_time', 'location', 
            'description', 'client_name', 'client_contact', 'staff_in_charge',
            'transport_cost', 'labor_cost', 'miscellaneous_cost',
            'is_completed'
        ]
        
        widgets = {
            # Text Inputs
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Wedding at Karen Manor'}),
            'event_type': forms.Select(attrs={'class': 'form-select'}),
            'location': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Venue Location'}),
            
            # Client & Staff
            'client_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Client Name'}),
            'client_contact': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Phone/Email'}),
            'staff_in_charge': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Lead Creative'}),
            
            # Description
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            
            # Date/Time (HTML5 Pickers)
            'start_time': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'end_time': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            
            # Financials (Numeric inputs)
            'transport_cost': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '0.00'}),
            'labor_cost': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '0.00'}),
            'miscellaneous_cost': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '0.00'}),
            
            # Checkbox
            'is_completed': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        # Pop user safely to prevent init errors
        user = kwargs.pop('user', None) 
        super(EventForm, self).__init__(*args, **kwargs)

        if user:
            # --- INTELLIGENT INVENTORY FILTER ---
            # 1. Base Logic: Show items that are AVAILABLE and owned by this user
            query = Q(owner=user, status='AVAILABLE')
            
            # 2. Edit Logic: If editing an event, ALSO show items that are already 
            #    assigned to this specific event (even if they are marked 'RENTED').
            #    This prevents booked items from disappearing when you edit the form.
            if self.instance.pk:
                current_item_ids = self.instance.manifest.values_list('item_id', flat=True)
                query = query | Q(id__in=current_item_ids)
            
            # 3. Apply the combined filter
            self.fields['items'].queryset = InventoryItem.objects.filter(query)
            
        # Pre-check the boxes if editing an existing event
        if self.instance.pk:
            current_items = self.instance.manifest.values_list('item_id', flat=True)
            self.fields['items'].initial = current_items