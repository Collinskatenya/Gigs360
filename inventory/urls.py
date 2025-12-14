from django.urls import path
from . import views

# CRITICAL: This namespace is required for {% url 'inventory:inventory_list' %} to work
app_name = 'inventory'

urlpatterns = [
    # --- Standard Inventory Actions ---
    # List all items (The Gear Locker)
    path('', views.inventory_list, name='inventory_list'),
    
    # Add new item
    path('add/', views.add_item, name='add_item'),
    
    # View Single Item Details
    # FIX: Changed <int:pk> to <uuid:pk> to match your database schema (UUIDs)
    path('item/<uuid:pk>/', views.item_detail, name='item_detail'),
    
    # Edit Item
    path('edit/<uuid:pk>/', views.edit_item, name='edit_item'),
    
    # Delete item
    path('delete/<uuid:pk>/', views.delete_item, name='delete_item'),

    # --- QR Scanner Features ---
    # Matches 'rapid_scan' view name
    path('rapid-scan/', views.rapid_scan, name='rapid_scan'),
    
    # The Hidden API that processes the scan (AJAX)
    path('api/scan/', views.scan_api, name='scan_api'),
]