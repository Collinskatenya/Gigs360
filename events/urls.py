from django.urls import path
from . import views

urlpatterns = [
    # 1. Dashboard (The name must match your template/navigation)
    # FIX: Using 'event_dashboard' as the name to satisfy template links 
    # (e.g., {% url 'event_dashboard' %}) and the error you previously received.
    path('dashboard/', views.event_dashboard, name='event_dashboard'),
    
    # 2. Create Event
    path('create/', views.create_event, name='create_event'),

    # 3. Edit Event
    path('update/<int:pk>/', views.update_event, name='update_event'),
]