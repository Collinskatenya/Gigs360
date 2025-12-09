from django.contrib import admin
from .models import Category, InventoryItem

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'icon')

@admin.register(InventoryItem)
class InventoryItemAdmin(admin.ModelAdmin):
    list_display = ('name', 'tracking_type', 'quantity', 'daily_rate', 'status', 'owner')
    list_filter = ('tracking_type', 'status', 'category')
    search_fields = ('name', 'serial_number')
    readonly_fields = ('id', 'qr_code') # Protect the system fields