from django.urls import path
from . import views

app_name = 'events'

urlpatterns = [
    # ==========================================
    # 1. EVENT OPERATIONS (Internal Routing - INT)
    # ==========================================
    path('dashboard/', views.event_dashboard, name='event_dashboard'),
    path('create/', views.create_event, name='create_event'),
    path('update/<int:pk>/', views.update_event, name='update_event'),
    path('delete/<int:pk>/', views.delete_event, name='delete_event'),
    path('report/<int:pk>/', views.event_report, name='event_report'),
    
    # ==========================================
    # 2. API ENDPOINTS (Mathematical Validation)
    # ==========================================
    path('api/check-availability/', views.check_gear_availability, name='check_availability'),

    # ==========================================
    # 3. STAGE 3: SMART DOCUMENT ENGINE (Invoices & Quotes)
    # ==========================================
    path('documents/', views.document_list, name='document_list'),
    path('event/<int:event_id>/create-document/', views.create_document, name='create_document'),

    # ==========================================
    # 4. FINANCIAL DOCUMENT SECURITY (External Routing - UUID)
    # ==========================================
    # Triggers an automatic file download
    path('document/<uuid:pk>/pdf/', views.generate_document_pdf, name='generate_pdf'),
    
    # Triggers an inline browser view (no download parameter)
    path('document/<uuid:pk>/view/', views.generate_document_pdf, name='view_document'), 
    
    # Safe Deletion Protocol
    path('document/<uuid:pk>/delete/', views.delete_document, name='delete_document'),
]