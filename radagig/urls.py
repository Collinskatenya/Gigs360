from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # 1. Admin Panel
    path('admin/', admin.site.urls),
    
    # 2. Django Built-in Auth (Password reset, etc.)
    path('accounts/', include('django.contrib.auth.urls')),
    
    # 3. Core App URLs (Home, Dashboard, Settings, Auth)
    path('', include('core.urls')),
    
    # 4. Feature Apps
    path('inventory/', include('inventory.urls')),
    path('events/', include('events.urls')),
]

# Serve Media Files (Images) in Development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)