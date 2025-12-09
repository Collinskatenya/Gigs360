from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    # Landing Page
    path('', views.home, name='home'),

    # Authentication
    path('signup/', views.signup, name='signup'),
    path('login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='home'), name='logout'),
    
    # Account Activation
    path('activate/<uidb64>/<token>/', views.activate, name='activate'),

    # Dashboard & Features
    path('dashboard/', views.dashboard, name='dashboard'),
    path('dashboard/settings/', views.settings_view, name='settings'),
    path('dashboard/pricing/', views.pricing_view, name='pricing'), # Ensure this view exists in core/views.py!
]