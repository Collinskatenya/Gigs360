from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
import json

from .models import InventoryItem
from .forms import InventoryItemForm

# -------------------------------------------------------------------------
# 1. STANDARD INVENTORY MANAGEMENT
# -------------------------------------------------------------------------

@login_required
def inventory_list(request):
    """
    The Gear Locker: Shows all items owned by the user.
    """
    items = InventoryItem.objects.filter(owner=request.user).order_by('-created_at')
    return render(request, 'inventory/inventory_list.html', {'items': items})

@login_required
def add_item(request):
    """
    Form to add a new piece of gear.
    """
    if request.method == 'POST':
        form = InventoryItemForm(request.POST, request.FILES)
        if form.is_valid():
            item = form.save(commit=False)
            item.owner = request.user
            item.save()
            messages.success(request, f"{item.name} added to Gear Locker!")
            return redirect('inventory_list')
    else:
        form = InventoryItemForm()
    
    return render(request, 'inventory/add_item.html', {'form': form})

@login_required
def item_detail(request, item_id):
    """
    Detailed View: Shows Color, Weight, and QR Code for a specific item.
    """
    item = get_object_or_404(InventoryItem, id=item_id, owner=request.user)
    return render(request, 'inventory/item_detail.html', {'item': item})

@login_required
def delete_item(request, pk):
    """
    Deletes an item permanently.
    """
    item = get_object_or_404(InventoryItem, pk=pk, owner=request.user)
    if request.method == 'POST':
        item.delete()
        messages.success(request, 'Item deleted successfully.')
        return redirect('inventory_list')
    
    # If GET request (clicking the link directly), confirm or just delete depending on UX preference.
    # For now, we'll just delete to match your sidebar delete button logic
    item.delete()
    messages.success(request, 'Item deleted successfully.')
    return redirect('inventory_list')


# -------------------------------------------------------------------------
# 2. SCANNER LOGIC (The New Features)
# -------------------------------------------------------------------------

@login_required
def rapid_scan_page(request):
    """
    Renders the Camera Interface.
    """
    return render(request, 'inventory/rapid_scan.html')

@csrf_exempt
@login_required
def scan_api(request):
    """
    The hidden API that processes the QR code scan.
    """
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            raw_data = data.get('qr_data', '')
            mode = data.get('mode') # 'checkout' or 'checkin'
            
            # Extract UUID from URL if necessary
            # (e.g., if QR contains "gigs360.com/scan/abc-123", we just want "abc-123")
            if '/' in raw_data:
                item_uuid = raw_data.rstrip('/').split('/')[-1]
            else:
                item_uuid = raw_data

            # Find Item
            item = get_object_or_404(InventoryItem, id=item_uuid, owner=request.user)
            
            message = ""
            status_code = "success"

            # Check-Out Logic
            if mode == 'checkout':
                if item.status == 'RENTED':
                    message = f"⚠️ {item.name} is ALREADY checked out."
                    status_code = "warning"
                else:
                    item.status = 'RENTED'
                    item.save()
                    message = f"📤 Checked OUT: {item.name}"

            # Check-In Logic
            elif mode == 'checkin':
                if item.status == 'AVAILABLE':
                    message = f"⚠️ {item.name} is ALREADY in stock."
                    status_code = "warning"
                else:
                    item.status = 'AVAILABLE'
                    item.save()
                    message = f"📥 Checked IN: {item.name}"

            # Audit Trail Update
            item.last_scanned_at = timezone.now()
            item.last_scanned_by = request.user
            item.save()

            return JsonResponse({'status': status_code, 'message': message, 'item': item.name})

        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})

    return JsonResponse({'status': 'error', 'message': 'Invalid Method'})