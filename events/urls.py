from django.urls import path
from . import views

urlpatterns = [
    # The Event Dashboard (Upcoming vs Past)
    path('dashboard/', views.event_dashboard, name='event_dashboard'),
    
    # The Create Event Form
    path('create/', views.create_event, name='create_event'),
]