from django.urls import path
from . import views

app_name = 'events'

urlpatterns = [
    # ==========================================
    # 1. EVENT OPERATIONS (Integer IDs)
    # ==========================================
    path('dashboard/', views.event_dashboard, name='event_dashboard'),
    path('create/', views.create_event, name='create_event'),
    path('update/<int:pk>/', views.update_event, name='update_event'),
    path('delete/<int:pk>/', views.delete_event, name='delete_event'),
    path('report/<int:pk>/', views.event_report, name='event_report'),
    
    # ==========================================
    # 2. API ENDPOINTS (AJAX)
    # ==========================================
    path('api/check-availability/', views.check_gear_availability, name='check_availability'),

    # ==========================================
    # 3. DOCUMENT ENGINE
    # ==========================================
    path('documents/', views.document_list, name='document_list'),
    
    # Creates a document linked to a specific event
    path('event/<int:event_id>/create-document/', views.create_document, name='create_document'),

    # ==========================================
    # 4. DOCUMENT ACTIONS
    # ==========================================
    # FIX: Changed <uuid:pk> to <int:pk> to ensure compatibility with standard Django models.
    # If your Document model explicitly uses UUIDs, you can switch this back.
    path('document/<int:pk>/pdf/', views.generate_document_pdf, name='generate_pdf'),
    path('document/<int:pk>/view/', views.generate_document_pdf, name='view_document'), # Re-uses generator for viewing
    path('document/<int:pk>/delete/', views.delete_document, name='delete_document'),
]