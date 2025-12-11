from django.urls import path
from . import views

urlpatterns = [
    # --- Standard Inventory Actions ---
    # List all items (The Gear Locker)
    path('', views.inventory_list, name='inventory_list'),
    
    # Add new item
    path('add/', views.add_item, name='add_item'),
    
    # View Single Item Details
    # FIX: Changed 'item_id' to 'pk' to match standard Django Views and your delete/edit paths
    path('item/<uuid:pk>/', views.item_detail, name='item_detail'),
    
    # FIX: Added MISSING Edit Path (Required for the Edit button to work)
    path('edit/<uuid:pk>/', views.edit_item, name='edit_item'),
    
    # Delete item
    path('delete/<uuid:pk>/', views.delete_item, name='delete_item'),

    # --- QR Scanner Features ---
    # The Camera Interface Page
    # Name changed to 'rapid_scan' to match common template tags, but 'rapid_scanner' works if your template matches.
    path('scanner/', views.rapid_scan_page, name='rapid_scan'),
    
    # The Hidden API that processes the scan (AJAX)
    path('api/scan/', views.scan_api, name='scan_api'),
]