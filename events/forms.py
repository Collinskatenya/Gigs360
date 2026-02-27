from django import forms
from django.db.models import Q
from django.utils import timezone
from django.forms import inlineformset_factory
from .models import Event, Document, LineItem
from inventory.models import InventoryItem

# ==========================================
# 1. EVENT PLANNING FORM
# ==========================================

class EventForm(forms.ModelForm):
    # Virtual field for display only. Saving is handled in the view.
    items = forms.ModelMultipleChoiceField(
        queryset=InventoryItem.objects.none(), 
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
        required=False, 
        label="Select Equipment"
    )

    class Meta:
        model = Event
        fields = [
            'title', 'event_type', 'start_time', 'end_time', 'location', 
            'description', 'client_name', 'client_contact', 'client_email',
            'staff_in_charge', 'transport_cost', 'labor_cost', 'miscellaneous_cost',
            'status', 'is_completed' # 🚨 PHASE 4 INJECTION: Added 'status'
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
            'status': forms.Select(attrs={'class': 'form-select fw-bold text-primary'}), # 🚨 PHASE 4 UI
            'is_completed': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None) 
        super(EventForm, self).__init__(*args, **kwargs)

        if user:
            # 1. Filter Inventory: Show User's items + Exclude Broken/Lost
            query = Q(owner=user) & ~Q(status__in=['LOST', 'DAMAGED'])
            
            # 2. Logic: If editing, include items that are currently assigned to this event
            if self.instance.pk:
                current_item_ids = self.instance.manifest.values_list('item__id', flat=True)
                if current_item_ids:
                    query = query | Q(id__in=current_item_ids)
            
            self.fields['items'].queryset = InventoryItem.objects.filter(query).distinct()
            
            # 3. Pre-select checkboxes if editing
            if self.instance.pk:
                self.fields['items'].initial = self.instance.manifest.values_list('item', flat=True)

    def clean(self):
        cleaned_data = super().clean()
        start_time = cleaned_data.get("start_time")
        end_time = cleaned_data.get("end_time")

        if start_time and end_time:
            # End before Start
            if end_time <= start_time:
                self.add_error('end_time', "End time must be after the start time.")

            # Past booking check (with 15 min buffer)
            cutoff = timezone.now() - timezone.timedelta(minutes=15)
            # Only trigger past booking error if it's a NEW event being created
            if not self.instance.pk and start_time < cutoff:
                self.add_error('start_time', "You cannot book an event in the past.")

        return cleaned_data


# ==========================================
# 2. DOCUMENT (QUOTE/INVOICE) FORM
# ==========================================

class DocumentForm(forms.ModelForm):
    # Brand Color Picker
    brand_color = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'type': 'color', 'class': 'form-control form-control-color', 'title': 'Choose PDF Color'}),
        label="Document Theme"
    )

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


# ==========================================
# 3. LINE ITEM FORMSET
# ==========================================

LineItemFormSet = inlineformset_factory(
    Document, LineItem,
    fields=('description', 'details', 'quantity', 'unit_price'),
    extra=1,
    can_delete=True,
    widgets={
        'description': forms.TextInput(attrs={'class': 'form-control fw-bold item-search', 'placeholder': 'Item / Package Name'}),
        'details': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Specs/Notes'}),
        'quantity': forms.NumberInput(attrs={'class': 'form-control text-center', 'min': 1}),
        'unit_price': forms.NumberInput(attrs={'class': 'form-control text-end', 'placeholder': '0.00'}),
    }
)