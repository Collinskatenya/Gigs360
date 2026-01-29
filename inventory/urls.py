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
    
    # Edit Item
    path('update/<uuid:pk>/', views.update_item, name='update_item'),
    
    # Delete item
    path('delete/<uuid:pk>/', views.delete_item, name='delete_item'),

    # --- QR Scanner Features ---
    # 1. The In-App Scanner UI (For You/Staff)
    path('rapid-scan/', views.rapid_scan, name='rapid_scan'),
    
    # 2. The Secure API Endpoint (Processed via AJAX)
    path('api/scan/', views.api_process_scan, name='api_process_scan'),

    # 3. Public Verification Page (Lost & Found / Stranger Scans)
    # Uses the secure UUID we added to models.py, NOT the database PK
    path('verify/<uuid:qr_uuid>/', views.public_item_verify, name='public_verify'),
]