from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    # ==========================================
    # 1. PUBLIC & B2C AUTHENTICATION
    # ==========================================
    path('', views.home, name='home'),
    path('signup/', views.signup, name='signup'),
    
    # Standard Consumer Login/Logout
    # Note: Staff login is securely handled at the project level in radagig/urls.py
    path('login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='home'), name='logout'),
    
    # Account Activation
    path('activate/<uidb64>/<token>/', views.activate, name='activate'),

    # Password Reset Pipeline
    path('password_reset/', auth_views.PasswordResetView.as_view(template_name='registration/password_reset_form.html'), name='password_reset'),
    path('password_reset/done/', auth_views.PasswordResetDoneView.as_view(template_name='registration/password_reset_done.html'), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(template_name='registration/password_reset_confirm.html'), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(template_name='registration/password_reset_complete.html'), name='password_reset_complete'),

    # ==========================================
    # 2. CONSUMER DASHBOARD & SETTINGS
    # ==========================================
    # If Staff hits this, core/views.py will auto-redirect them to staff_dashboard
    path('dashboard/', views.dashboard, name='dashboard'),
    path('dashboard/settings/', views.settings_view, name='settings'),
    path('dashboard/pricing/', views.pricing_view, name='pricing'), 
    path('dashboard/support/', views.support_history, name='support_history'), # 🚨 UPGRADED: Professional Messaging Inbox

    # ==========================================
    # 3. NOTIFICATION SYSTEM
    # ==========================================
    path('notifications/read/<int:pk>/', views.mark_notification_read, name='mark_notification_read'),
    # 🚨 FIX: Matched the name to the template tag exactly
    path('notifications/read-all/', views.mark_all_notifications_read, name='mark_all_notifications_read'),

    # ==========================================
    # 4. ENTERPRISE GOVERNANCE (STAFF)
    # ==========================================
    # Secured by @staff_member_required in views.py
    path('staff/', views.staff_dashboard, name='staff_dashboard'),
    path('staff/verify/<int:user_id>/', views.verify_user, name='verify_user'),
    
    # Support Resolution Engine & Command Consoles
    path('staff/ticket/<int:ticket_id>/resolve/', views.resolve_ticket, name='resolve_ticket'),
    path('staff/ticket/<int:ticket_id>/chat/', views.staff_ticket_detail, name='staff_ticket_detail'), # 🚨 UPGRADED: HQ Command Terminal
    path('staff/users/', views.staff_user_manager, name='staff_user_manager'),
    path('staff/users/<int:user_id>/edit/', views.staff_edit_user, name='staff_edit_user'),
    path('staff/inventory/', views.staff_master_inventory, name='staff_master_inventory'),
    path('staff/logs/', views.staff_security_logs, name='staff_security_logs'),
    path('staff/gigs/', views.staff_gigs_tracker, name='staff_gigs_tracker'),
    
    # 🚨 SECURITY KILL SWITCHES
    path('staff/users/<int:user_id>/suspend/', views.suspend_user, name='suspend_user'),
    path('staff/inventory/<uuid:item_id>/flag/', views.flag_asset, name='flag_asset'), # 🚨 FIXED: Changed 'int' to 'uuid'

    # ==========================================
    # 5. HELPDESK & SUPPORT
    # ==========================================
    path('ticket/create/', views.create_ticket, name='create_ticket'),

    # ==========================================
    # 6. HQ VAULT (THE INNOVATIVE FIX)
    # ==========================================
    path('staff/comms/', views.staff_comms_module, name='staff_comms_module'),
    path('staff/comms/search-users/', views.search_users_ajax, name='search_users_ajax'), # 🚨 ADDED: Live Search Endpoint
    path('staff/settings/', views.staff_settings, name='staff_settings'),
]