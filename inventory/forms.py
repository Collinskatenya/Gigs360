from django import forms
from .models import InventoryItem

# 🚨 DJANGO 5.x FIX: Custom widget explicitly allowing multiple files
class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True

class InventoryItemForm(forms.ModelForm):
    # Using the custom Django 5 widget for the showroom gallery
    gallery_images = forms.FileField(
        widget=MultipleFileInput(attrs={'multiple': True, 'class': 'form-control'}),
        required=False,
        label="Showroom Gallery (Optional)",
        help_text="Upload up to 5 additional angles for the public marketplace."
    )

    class Meta:
        model = InventoryItem
        fields = [
            'name', 'category', 'tracking_type', 'quantity', 
            'daily_rate', 'replacement_value', 
            'serial_number', 'asset_tag', 'color', 'weight',
            'condition', 'status', 'description', 'image', # 🚨 Added 'status'
            'is_published', 'search_location'
        ]
        
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Item Name (e.g. Sony A7S III)'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'tracking_type': forms.Select(attrs={'class': 'form-select'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control'}),
            
            # Financials
            'daily_rate': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'KES (Optional)'}),
            'replacement_value': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Insurance Value (Optional)'}),
            
            # Traceability & Lifecycle
            'serial_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Manufacturer S/N'}),
            'asset_tag': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Internal ID (e.g. CAM-01)'}),
            'color': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Matte Black'}),
            'weight': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. 2.5kg'}),
            'condition': forms.Select(attrs={'class': 'form-select'}),
            'status': forms.Select(attrs={'class': 'form-select'}), # 🚨 Added explicit widget for Status
            
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Notes on condition or specs...'}),
            'image': forms.FileInput(attrs={'class': 'form-control'}),

            # Marketplace Hub Toggles
            'is_published': forms.CheckboxInput(attrs={'class': 'form-check-input', 'role': 'switch'}),
            'search_location': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Nairobi, Nakuru'}),
        }