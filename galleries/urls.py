from django.urls import path
from . import views

app_name = 'galleries'

urlpatterns = [
    # ==========================================
    # 1. PUBLIC FACING (The Client's View)
    # ==========================================
    # Example: /collection/the-smith-wedding-ab12cd34/
    path('collection/<slug:slug>/', views.client_gallery_view, name='client_gallery'),

    # ==========================================
    # 2. INTERNAL DASHBOARD (The Photographer's Control Room)
    # ==========================================
    # Example: /delivery/ (The main list with the 3GB tracker)
    path('delivery/', views.dashboard_gallery_list, name='list'),
    
    # Example: /delivery/new/ (The creation form)
    path('delivery/new/', views.dashboard_gallery_create, name='create'),
    
    # Example: /delivery/a1b2c3d4.../manage/ (The drag-and-drop upload zone)
    path('delivery/<uuid:uuid>/manage/', views.dashboard_gallery_manage, name='manage_gallery'),
]