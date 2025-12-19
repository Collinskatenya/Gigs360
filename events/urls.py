from django.urls import path
from . import views

# 1. CRITICAL: Namespace is required for {% url 'events:...' %} tags
app_name = 'events'

urlpatterns = [
    # --- Dashboard & Event Operations ---
    # Events likely use standard IDs (Integers), so we keep these as <int:pk>
    path('dashboard/', views.event_dashboard, name='event_dashboard'),
    path('create/', views.create_event, name='create_event'),
    path('update/<int:pk>/', views.update_event, name='update_event'),
    path('report/<int:pk>/', views.event_report, name='event_report'),
    
    # --- API (Availability Logic) ---
    path('api/check-availability/', views.check_gear_availability, name='check_availability'),

    # --- Document Engine (Invoices/Quotes) ---
    path('documents/', views.document_list, name='document_list'),
    path('event/<int:event_id>/create-document/', views.create_document, name='create_document'),

    # --- PDF & Actions ---
    # FIX: Changed <int:pk> back to <uuid:pk> because your logs prove Documents use UUIDs.
    
    # 1. Download/Generate PDF
    path('document/<uuid:pk>/pdf/', views.generate_document_pdf, name='generate_pdf'),
    
    # 2. View/Preview (Maps to the same PDF view for inline viewing)
    path('document/<uuid:pk>/view/', views.generate_document_pdf, name='view_document'),

    # 3. CRITICAL: The Delete Path
    path('document/<uuid:pk>/delete/', views.delete_document, name='delete_document'),
]