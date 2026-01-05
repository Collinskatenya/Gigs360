from django.urls import path
from . import views

# CRITICAL: This namespace allows tags like {% url 'events:create_event' %} to work.
app_name = 'events'

urlpatterns = [
    # ==========================================
    # 1. EVENT OPERATIONS (CRUD)
    # ==========================================
    path('dashboard/', views.event_dashboard, name='event_dashboard'),
    path('create/', views.create_event, name='create_event'),
    path('update/<int:pk>/', views.update_event, name='update_event'),
    
    # NEW: The Cancellation Path (Required for the "Cancel Gig" button)
    path('delete/<int:pk>/', views.delete_event, name='delete_event'),
    
    path('report/<int:pk>/', views.event_report, name='event_report'),
    
    # ==========================================
    # 2. API ENDPOINTS (AJAX/Fetch)
    # ==========================================
    path('api/check-availability/', views.check_gear_availability, name='check_availability'),

    # ==========================================
    # 3. DOCUMENT ENGINE (Invoices/Quotes)
    # ==========================================
    path('documents/', views.document_list, name='document_list'),
    path('event/<int:event_id>/create-document/', views.create_document, name='create_document'),

    # ==========================================
    # 4. DOCUMENT ACTIONS (PDFs & Deletion)
    # ==========================================
    # Note: Using <uuid:pk> here because Documents use UUIDs, unlike Events which use IDs.
    path('document/<uuid:pk>/pdf/', views.generate_document_pdf, name='generate_pdf'),
    path('document/<uuid:pk>/view/', views.generate_document_pdf, name='view_document'),
    path('document/<uuid:pk>/delete/', views.delete_document, name='delete_document'),
]