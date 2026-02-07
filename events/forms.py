from django import forms
from django.db.models import Q
from django.utils import timezone  # <--- CRITICAL IMPORT FOR TIME LOGIC
from django.forms import inlineformset_factory
from .models import Event, Document, LineItem
from inventory.models import InventoryItem 

# ==========================================
# 1. EVENT PLANNING FORM (Refined)
# ==========================================

class EventForm(forms.ModelForm):
    # ROBUSTNESS: Start with empty queryset to optimize page load speed.
    items = forms.ModelMultipleChoiceField(
        queryset=InventoryItem.objects.none(), 
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
        required=False, 
        label="Select Equipment (Optional - Can be added later)"
    )

    class Meta:
        model = Event
        fields = [
            'title', 'event_type', 'start_time', 'end_time', 'location', 
            'description', 'client_name', 'client_contact', 'client_email',
            'staff_in_charge', 'transport_cost', 'labor_cost', 'miscellaneous_cost',
            'items', 'is_completed'
        ]
        
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Wedding at Karen Manor'}),
            'event_type': forms.Select(attrs={'class': 'form-select'}),
            'location': forms.TextInput(attrs={'id': 'id_location', 'class': 'form-control', 'placeholder': 'Venue Location'}),
            'client_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Client Name'}),
            'client_contact': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Phone/Email'}),
            'client_email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'client@email.com'}),
            'staff_in_charge': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Lead Creative'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'start_time': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'end_time': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'transport_cost': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '0.00'}),
            'labor_cost': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '0.00'}),
            'miscellaneous_cost': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '0.00'}),
            'is_completed': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        # Safely extract user to filter their specific inventory
        user = kwargs.pop('user', None) 
        super(EventForm, self).__init__(*args, **kwargs)

        if user:
            # --- INTELLIGENT INVENTORY FILTER ---
            # 1. Show items owned by user
            # 2. Exclude broken items (LOST/DAMAGED)
            query = Q(owner=user) & ~Q(status__in=['LOST', 'DAMAGED'])
            
            # ROBUSTNESS: If editing an event, ensure currently booked items remain 
            # visible in the list, even if they were marked DAMAGED after booking.
            if self.instance.pk:
                # We access the ManyToMany field directly
                current_items = self.instance.items.all() 
                if current_items.exists():
                     query = query | Q(id__in=current_items.values_list('id', flat=True))
            
            # Apply the filter to the form field
            self.fields['items'].queryset = InventoryItem.objects.filter(query).distinct()
            
            # Pre-check boxes if editing
            if self.instance.pk:
                self.fields['items'].initial = self.instance.items.all()

    # --- TASK 1: FIX TIME TRAVEL BUG ---
    def clean(self):
        cleaned_data = super().clean()
        start_time = cleaned_data.get("start_time")
        end_time = cleaned_data.get("end_time")

        if start_time and end_time:
            # 1. LOGIC CHECK: End before Start?
            if end_time <= start_time:
                self.add_error('end_time', "End time must be after the start time.")

            # 2. REALITY CHECK: Booking in the past?
            # We allow a small 15-minute buffer for 'just now' bookings to prevent frustration
            cutoff = timezone.now() - timezone.timedelta(minutes=15)
            if start_time < cutoff:
                self.add_error('start_time', "You cannot book an event in the past.")

        return cleaned_data


# ==========================================
# 2. INVOICING & QUOTE FORMS (Polished)
# ==========================================

class DocumentForm(forms.ModelForm):
    class Meta:
        model = Document
        fields = ['doc_type', 'client_name', 'client_email', 'client_phone', 'issue_date', 'due_date', 'terms', 'notes']
        widgets = {
            'doc_type': forms.Select(attrs={'class': 'form-select'}),
            'client_name': forms.TextInput(attrs={'class': 'form-control'}),
            'client_email': forms.EmailInput(attrs={'class': 'form-control'}),
            'client_phone': forms.TextInput(attrs={'class': 'form-control'}),
            'issue_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'due_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'terms': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Bank Details, M-Pesa, etc.'}),
        }

# Formset for adding multiple items dynamically
LineItemFormSet = inlineformset_factory(
    Document, LineItem,
    fields=('description', 'details', 'quantity', 'unit_price'),
    extra=1,
    can_delete=True,
    widgets={
        'description': forms.TextInput(attrs={'class': 'form-control fw-bold', 'placeholder': 'Item / Package Name'}),
        'details': forms.Textarea(attrs={'class': 'form-control', 'rows': 1, 'placeholder': 'Details (e.g. 2 Cameras...)'}),
        'quantity': forms.NumberInput(attrs={'class': 'form-control text-center', 'min': 1}),
        'unit_price': forms.NumberInput(attrs={'class': 'form-control text-end', 'placeholder': '0.00'}),
    }
)