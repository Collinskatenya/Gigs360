# events/urls.py

from django.urls import path
from . import views

urlpatterns = [
    # ... existing dashboard, create, update, report, api ...
    path('dashboard/', views.event_dashboard, name='event_dashboard'),
    path('create/', views.create_event, name='create_event'),
    path('update/<int:pk>/', views.update_event, name='update_event'),
    path('report/<int:pk>/', views.event_report, name='event_report'),
    path('api/check-availability/', views.check_gear_availability, name='check_availability'),

    # PDF Logic
    path('document/<uuid:pk>/pdf/', views.generate_document_pdf, name='generate_pdf'),
    path('event/<int:event_id>/create-document/', views.create_document, name='create_document'),

    # 8. DOCUMENT LIST (The "Invoices" Page) - NEW
    path('documents/', views.document_list, name='document_list'),
]