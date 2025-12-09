from django import forms
from .models import InventoryItem

class InventoryItemForm(forms.ModelForm):
    class Meta:
        model = InventoryItem
        fields = [
            'name', 'category', 'tracking_type', 'quantity', 
            'daily_rate', 'replacement_value', 
            'serial_number', 'asset_tag', 'color', 'weight', # New Traceability Fields
            'condition', 'description', 'image'
        ]
        
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Item Name (e.g. Sony A7S III)'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'tracking_type': forms.Select(attrs={'class': 'form-select'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control'}),
            
            # Financials (Updated placeholders to show they are optional)
            'daily_rate': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'KES (Optional)'}),
            'replacement_value': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Insurance Value (Optional)'}),
            
            # Traceability & Identification
            'serial_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Manufacturer S/N'}),
            'asset_tag': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Internal ID (e.g. CAM-01)'}),
            'color': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Matte Black'}),
            'weight': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. 2.5kg'}),
            'condition': forms.Select(attrs={'class': 'form-select'}),
            
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Notes on condition or specs...'}),
            'image': forms.FileInput(attrs={'class': 'form-control'}),
        }