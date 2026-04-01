from django.urls import path
from . import views

# CRITICAL: This namespace is required for sidebar links to work
app_name = 'inventory'

urlpatterns = [
    # =========================================================================
    # 0. PUBLIC MARKETPLACE (Phase 3: The Discovery Hub)
    # =========================================================================
    # The Global Search Engine (TikTok-style public access)
    path('discover/', views.marketplace_hub, name='marketplace_hub'),
    
    # The Dynamic Asset Showroom (SEO-friendly URL using the item slug)
    path('rent/<slug:slug>/', views.public_asset_showroom, name='public_asset_showroom'),


    # =========================================================================
    # 1. GEAR LOCKER MANAGEMENT (Internal Vendor Operations)
    # =========================================================================
    # List all items (The Gear Locker)
    path('', views.inventory_list, name='inventory_list'),
    
    # Add new item
    path('add/', views.add_item, name='add_item'),
    
    # View Single Item Details (Internal)
    # CRITICAL FIX: Uses <uuid:pk> because the database uses UUIDs, not integers
    path('item/<uuid:pk>/', views.item_detail, name='item_detail'),
    
    # Edit Item
    path('update/<uuid:pk>/', views.update_item, name='update_item'),
    
    # Delete item
    path('delete/<uuid:pk>/', views.delete_item, name='delete_item'),


    # =========================================================================
    # 2. RAPID SCANNER & HARDWARE APIs
    # =========================================================================
    # 1. The In-App Scanner UI (For You/Staff)
    path('rapid-scan/', views.rapid_scan, name='rapid_scan'),
    
    # 2. The Secure API Endpoint (Processed via AJAX)
    path('api/scan/', views.api_process_scan, name='api_process_scan'),

    # 3. Public Verification Page (Lost & Found / Stranger Scans)
    # CRITICAL: This uses the specific 'qr_code_id' UUID field, NOT the database PK
    path('verify/<uuid:qr_uuid>/', views.public_item_verify, name='public_item_verify'),
]