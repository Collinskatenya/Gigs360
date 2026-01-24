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
    # 2. API ENDPOINTS
    # ==========================================
    path('api/check-availability/', views.check_gear_availability, name='check_availability'),

    # ==========================================
    # 3. DOCUMENT ENGINE (Mixed IDs)
    # ==========================================
    path('documents/', views.document_list, name='document_list'),
    
    # NOTE: <int:event_id> because it refers to the Event (Integer)
    path('event/<int:event_id>/create-document/', views.create_document, name='create_document'),

    # ==========================================
    # 4. DOCUMENT ACTIONS (UUIDs)
    # ==========================================
    # CRITICAL: Must use <uuid:pk> because your Document model uses UUIDField
    path('document/<uuid:pk>/pdf/', views.generate_document_pdf, name='generate_pdf'),
    path('document/<uuid:pk>/view/', views.generate_document_pdf, name='view_document'),
    path('document/<uuid:pk>/delete/', views.delete_document, name='delete_document'),
]