from django.urls import path
from . import views

app_name = 'galleries'

urlpatterns = [
    # 🚨 CRITICAL FIX: Master List (Resolves the NoReverseMatch error)
    path('', views.gallery_list, name='gallery_list'),
    
    # Vendor Route: e.g., /galleries/manage/2/
    path('manage/<int:event_id>/', views.manage_gallery, name='manage_gallery'),
    
    # Client Route: e.g., /galleries/view/abc12345-def6.../
    path('view/<uuid:gallery_id>/', views.client_gallery_view, name='client_gallery_view'),
]