from django import forms
from .models import Post
from inventory.models import InventoryItem

class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ['title', 'content', 'linked_gear', 'is_gig_offer', 'budget']
        
        # 🎨 INNOVATION: Stripped of backgrounds so the HTML CSS wrappers can style them flawlessly
        widgets = {
            'title': forms.TextInput(attrs={
                'placeholder': 'Give your post a catchy title...', 
                'class': 'form-control border-0 bg-transparent px-0 fw-bold',
                'style': 'font-size: 1.1rem; box-shadow: none;'
            }),
            'content': forms.Textarea(attrs={
                'placeholder': "What's on your mind? Share an update, ask for help, or drop a tip...", 
                'rows': 4, 
                'class': 'form-control border-0 bg-transparent px-0',
                'style': 'resize: none; box-shadow: none;'
            }),
            'linked_gear': forms.Select(attrs={
                'class': 'form-select border-0 bg-transparent fw-bold text-dark',
                'style': 'box-shadow: none;'
            }),
            'is_gig_offer': forms.CheckboxInput(attrs={
                'class': 'form-check-input mt-0'
            }),
            'budget': forms.NumberInput(attrs={
                'placeholder': 'e.g. 15000', 
                'class': 'form-control border-0 bg-transparent',
                'min': '0',
                'style': 'box-shadow: none;'
            }),
        }

    def __init__(self, *args, **kwargs):
        # 🚨 SECURITY: Extract the user before initializing the form
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        if user:
            # Only allow the user to attach gear they actually own and that is available
            self.fields['linked_gear'].queryset = InventoryItem.objects.filter(owner=user, status='AVAILABLE')
            self.fields['linked_gear'].empty_label = "--- Do not attach an asset ---"
            
        # 🚨 UI FIX: Remove default Django labels so our beautiful HTML labels don't get duplicated
        for field in self.fields:
            self.fields[field].label = ''