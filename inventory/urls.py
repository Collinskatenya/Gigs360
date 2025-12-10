from django.urls import path
from . import views

urlpatterns = [
    # --- Standard Inventory Actions ---
    # List all items (The Gear Locker)
    path('', views.inventory_list, name='inventory_list'),
    
    # Add new item
    path('add/', views.add_item, name='add_item'),
    
    # View Single Item Details (To see Color, Weight, & Download QR)
    # NOTE: We use <uuid:item_id> because your model uses UUIDs
    path('item/<uuid:item_id>/', views.item_detail, name='item_detail'),
    
    # Delete item
    path('delete/<uuid:pk>/', views.delete_item, name='delete_item'),

    # --- QR Scanner Features (The New Stuff) ---
    # The Camera Interface Page
    path('scanner/', views.rapid_scan_page, name='rapid_scanner'),
    
    # The Hidden API that processes the scan (AJAX)
    path('api/scan/', views.scan_api, name='scan_api'),
]