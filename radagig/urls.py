from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView  # 🚨 INJECTED: Used for the Admin Trap

urlpatterns = [
    # 🚨 SECURITY: The default admin is now hidden at this random URL
    path('hq-vault-access-99x/', admin.site.urls),
    
    # 🪤 THE HONEYPOT TRAP: Instantly kicks snoops away from /admin/ back to the homepage
    path('admin/', RedirectView.as_view(url='/', permanent=False)),
    
    # 🛡️ THE SECURE TERMINAL: Routing for the Staff-only login page
    path('staff/login/', auth_views.LoginView.as_view(
        template_name='core/staff_login.html',
        redirect_authenticated_user=True,
        next_page='staff_dashboard' 
    ), name='staff_login'),

    # ==========================================
    # GIGS360 PLATFORM APPS
    # ==========================================
    path('', include('core.urls')),                     # Identity & Landing Pages
    path('inventory/', include('inventory.urls')),      # Assets & QR Codes
    path('events/', include('events.urls')),            # Gigs & PDF Invoicing
    
    # 💳 STAGE 4 INJECTED: The Fintech Gateway
    path('finance/', include('finance.urls')),          # Escrow & M-Pesa Webhooks
    
    # 📸 STAGE 5 INJECTED: Client Galleries
    path('galleries/', include('galleries.urls')),      # Escrow-Locked Media Delivery
    
    # 🌐 STAGE 2 INJECTED: The Community Hub
    path('community/', include('community.urls')),      # Discord-style Gig Board & Networking
]

# 📁 LOCAL DEVELOPMENT SERVING (Critical for CSS, QR Codes, and PDFs)
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)