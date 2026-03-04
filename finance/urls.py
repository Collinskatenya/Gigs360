from django.urls import path
from . import views

app_name = 'finance'

urlpatterns = [
    # The AJAX endpoint to trigger the STK Push
    path('api/pay/<uuid:document_id>/', views.initiate_payment, name='initiate_payment'),
    
    # The secure webhook Daraja will call
    path('api/webhook/mpesa/', views.mpesa_webhook, name='mpesa_webhook'),
    
    # The Dev Helper to simulate a successful payment
    path('dev/simulate-payment/<uuid:transaction_id>/', views.simulate_callback, name='simulate_callback'),
]