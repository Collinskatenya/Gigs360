import json
import uuid
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.contrib import messages
from django.utils.crypto import get_random_string

from .models import MpesaTransaction
from events.models import Document

# ==========================================
# 1. TRIGGER PAYMENT (MOCKED STK PUSH)
# ==========================================

@login_required
@require_POST
def initiate_payment(request, document_id):
    """
    Simulates triggering an M-Pesa STK Push.
    Creates a PENDING ledger entry before the money even moves.
    """
    document = get_object_or_404(Document, pk=document_id)
    
    # 1. Security Check: Prevent double payments
    if document.status == 'PAID' or document.escrow_status in ['LOCKED', 'RELEASED']:
        return JsonResponse({'error': 'This invoice is already paid or locked in escrow.'}, status=400)

    phone_number = request.POST.get('phone_number', document.client_phone)
    if not phone_number:
        return JsonResponse({'error': 'A valid M-Pesa phone number is required.'}, status=400)

    # 2. Generate Fake Safaricom Trackers
    mock_merchant_id = f"REQ-{get_random_string(8).upper()}"
    mock_checkout_id = f"ws_CO_{get_random_string(12).upper()}"

    # 3. Create the Escrow Ledger Entry
    mpesa_txn = MpesaTransaction.objects.create(
        document=document,
        user=request.user, # The Client making the payment
        transaction_type='C2B_ESCROW',
        amount=document.balance_due,
        phone_number=phone_number,
        merchant_request_id=mock_merchant_id,
        checkout_request_id=mock_checkout_id,
        status='PENDING'
    )

    # 4. Update the Document to show it's awaiting auth
    document.escrow_status = 'PENDING'
    document.save()

    return JsonResponse({
        'success': True,
        'message': f'STK Push sent to {phone_number}. Please enter your M-Pesa PIN.',
        'checkout_request_id': mock_checkout_id,
        'transaction_id': str(mpesa_txn.id)
    })

# ==========================================
# 2. THE ESCROW LOCK (WEBHOOK RECEIVER)
# ==========================================

@csrf_exempt
@require_POST
def mpesa_webhook(request):
    """
    The secure endpoint Safaricom calls when the user enters their PIN.
    MUST be CSRF exempt because Safaricom does not have our CSRF tokens.
    """
    try:
        # In production, Safaricom sends a complex JSON payload here.
        # For our mock, we just look for the checkout_request_id and result code.
        data = json.loads(request.body)
        checkout_id = data.get('checkout_request_id')
        result_code = data.get('result_code', 0) # 0 means success in Daraja
        
        # 🚨 ACID COMPLIANCE: Lock the database while we update the money
        with transaction.atomic():
            mpesa_txn = MpesaTransaction.objects.get(checkout_request_id=checkout_id)
            document = mpesa_txn.document

            if result_code == 0:
                # 1. Update the Ledger
                mpesa_txn.status = 'SUCCESS'
                mpesa_txn.receipt_number = f"MOCK{get_random_string(8).upper()}"
                mpesa_txn.result_desc = "The service request is processed successfully."
                mpesa_txn.save()

                # 2. Update the Invoice & Lock the Escrow
                document.amount_paid = document.amount_paid + mpesa_txn.amount
                document.daraja_receipt_number = mpesa_txn.receipt_number
                document.escrow_status = 'LOCKED'
                # Document model's save() method will automatically switch status to 'PAID'
                document.save() 
            else:
                # Handle Cancelled / Failed PIN
                mpesa_txn.status = 'FAILED'
                mpesa_txn.result_desc = "Request cancelled by user."
                mpesa_txn.save()
                
                document.escrow_status = 'NONE'
                document.save()

        # Safaricom requires a specific JSON response acknowledging receipt
        return JsonResponse({"ResultCode": 0, "ResultDesc": "Accepted"})

    except Exception as e:
        return JsonResponse({"ResultCode": 1, "ResultDesc": str(e)})

# ==========================================
# 3. LOCAL TESTING HELPER
# ==========================================

@login_required
def simulate_callback(request, transaction_id):
    """
    A Dev-Only helper to manually trigger the webhook without Safaricom.
    Allows us to test the UI flow locally.
    """
    mpesa_txn = get_object_or_404(MpesaTransaction, id=transaction_id)
    
    # Create the fake Safaricom payload
    mock_payload = {
        'checkout_request_id': mpesa_txn.checkout_request_id,
        'result_code': 0
    }
    
    # Internal request to our own webhook
    request._body = json.dumps(mock_payload).encode('utf-8')
    response = mpesa_webhook(request)
    
    if response.status_code == 200:
        messages.success(request, f"💰 KES {mpesa_txn.amount} successfully locked in Gigs360 Escrow Vault!")
    else:
        messages.error(request, "Failed to simulate payment lock.")
        
    return redirect('events:document_list')