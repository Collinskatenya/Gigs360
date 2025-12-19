from django.urls import path
from . import views

# CRITICAL: This namespace is required for sidebar links to work
app_name = 'inventory'

urlpatterns = [
    # --- Standard Inventory Actions ---
    # List all items (The Gear Locker)
    path('', views.inventory_list, name='inventory_list'),
    
    # Add new item
    path('add/', views.add_item, name='add_item'),
    
    # View Single Item Details
    # Uses <uuid:pk> to match your database IDs
    path('item/<uuid:pk>/', views.item_detail, name='item_detail'),
    
    # Edit Item (View function is 'update_item', URL name is 'update_item')
    path('update/<uuid:pk>/', views.update_item, name='update_item'),
    
    # Delete item
    path('delete/<uuid:pk>/', views.delete_item, name='delete_item'),

    # --- QR Scanner Features ---
    path('rapid-scan/', views.rapid_scan, name='rapid_scan'),
    
    # API for AJAX calls
    # Name must be 'scan_api' to match your rapid_scan.html template
    path('api/scan/', views.process_scan_api, name='scan_api'),
]