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

    # Password Reset (Required for the link in login.html)
    path('password_reset/', auth_views.PasswordResetView.as_view(template_name='registration/password_reset_form.html'), name='password_reset'),
    path('password_reset/done/', auth_views.PasswordResetDoneView.as_view(template_name='registration/password_reset_done.html'), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(template_name='registration/password_reset_confirm.html'), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(template_name='registration/password_reset_complete.html'), name='password_reset_complete'),

    # ==========================================
    # 2. DASHBOARD & SETTINGS
    # ==========================================
    path('dashboard/', views.dashboard, name='dashboard'),
    path('dashboard/settings/', views.settings_view, name='settings'),
    path('dashboard/pricing/', views.pricing_view, name='pricing'), 

    # ==========================================
    # 3. NOTIFICATION SYSTEM
    # ==========================================
    path('notifications/read/<int:pk>/', views.mark_notification_read, name='mark_notification_read'),
    path('notifications/read-all/', views.mark_all_notifications_read, name='mark_all_read'),

    # ==========================================
    # 4. STAFF OPERATIONS
    # ==========================================
    path('staff/', views.staff_dashboard, name='staff_dashboard'),
    path('staff/verify/<int:user_id>/', views.verify_user, name='verify_user'),

    # ==========================================
    # 5. HELPDESK
    # ==========================================
    path('ticket/create/', views.create_ticket, name='create_ticket'),
]