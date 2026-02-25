from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # 🚨 SECURITY: The default admin is now hidden at this random URL
    path('hq-vault-access-99x/', admin.site.urls),
    
    # 🛡️ THE SECURE TERMINAL: Routing for the Staff-only login page
    path('staff/login/', auth_views.LoginView.as_view(
        template_name='core/staff_login.html',
        redirect_authenticated_user=True,
        next_page='staff_dashboard' 
    ), name='staff_login'),

    # Standard App URLs
    path('', include('core.urls')),
    path('inventory/', include('inventory.urls')),
    path('events/', include('events.urls')),
]

# 📁 LOCAL DEVELOPMENT SERVING (Critical for CSS, QR Codes, and PDFs)
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)