from django.contrib import admin
from .models import Category, InventoryItem

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'icon')
    search_fields = ('name',)

@admin.register(InventoryItem)
class InventoryItemAdmin(admin.ModelAdmin):
    # 1. What columns show up in the list
    list_display = (
        'name', 
        'category', # Added category here for better visibility
        'serial_number', 
        'status', 
        'owner', 
        'last_scanned_at'
    )
    
    # 2. Filters on the right side
    list_filter = ('status', 'tracking_type', 'category', 'condition')
    
    # 3. CRITICAL: This enables the 'autocomplete_fields' in your Events App
    search_fields = ('name', 'serial_number', 'asset_tag', 'owner__username')
    
    # 4. Protect system-generated fields
    readonly_fields = (
        'id', 
        'qr_code', 
        'created_at', 
        'updated_at', 
        'last_scanned_at', 
        'last_scanned_by'
    )

    # 5. Organize the detail view nicely
    fieldsets = (
        ('Identification', {
            'fields': ('id', 'owner', 'name', 'category', 'image', 'qr_code') # Added 'image' if you have it
        }),
        ('Traceability', {
            'fields': ('tracking_type', 'serial_number', 'asset_tag', 'color', 'weight')
        }),
        ('State & Financials', {
            'fields': ('status', 'condition', 'quantity', 'daily_rate')
        }),
        ('Audit Log (System Generated)', {
            'fields': ('last_scanned_at', 'last_scanned_by', 'created_at', 'updated_at'),
            'classes': ('collapse',), # Hide by default to keep UI clean
        }),
    )