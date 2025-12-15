from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    # ==========================================
    # 1. PUBLIC & AUTH
    # ==========================================
    path('', views.home, name='home'),
    path('signup/', views.signup, name='signup'),
    
    # Built-in Login/Logout
    path('login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='home'), name='logout'),
    
    # Account Activation
    path('activate/<uidb64>/<token>/', views.activate, name='activate'),

    # ==========================================
    # 2. DASHBOARD & SETTINGS
    # ==========================================
    path('dashboard/', views.dashboard, name='dashboard'),
    path('dashboard/settings/', views.settings_view, name='settings'),
    path('dashboard/pricing/', views.pricing_view, name='pricing'), 

    # ==========================================
    # 3. NOTIFICATION SYSTEM (New)
    # ==========================================
    # These endpoints are called by the Bell Icon JavaScript
    path('notifications/read/<int:pk>/', views.mark_notification_read, name='mark_notification_read'),
    path('notifications/read-all/', views.mark_all_notifications_read, name='mark_all_read'),
]