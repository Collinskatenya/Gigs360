from django.urls import path
from . import views

urlpatterns = [
    # 1. Dashboard
    path('dashboard/', views.event_dashboard, name='event_dashboard'),
    
    # 2. Create Event
    path('create/', views.create_event, name='create_event'),

    # 3. Edit Event
    path('update/<int:pk>/', views.update_event, name='update_event'),

    # 4. Audit Report (Internal View)
    path('report/<int:pk>/', views.event_report, name='event_report'),

    # 5. API Endpoint (Required for "Smart Availability" check in forms)
    path('api/check-availability/', views.check_gear_availability, name='check_availability'),

    # 6. PDF GENERATOR (The "Smart Contract" Engine)
    # Generates the actual PDF file
    path('document/<uuid:pk>/pdf/', views.generate_document_pdf, name='generate_pdf'),

    # 7. CREATE DOCUMENT INTERFACE (The Missing Piece!)
    # This is the page where you fill in the Quote details before generating the PDF
    path('event/<int:event_id>/create-document/', views.create_document, name='create_document'),
]