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
# 1. GEAR LOCKER MANAGEMENT (List, Add, Edit, Delete)
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
    
    return render(request, 'inventory/add_item.html', {'form': form, 'title': 'Add New Item'})

@login_required
def edit_item(request, pk):
    """
    FIX: Allows editing details like Status, Serial, or Photo.
    Connects to the 'Edit' button in the list view.
    """
    item = get_object_or_404(InventoryItem, pk=pk, owner=request.user)
    
    if request.method == 'POST':
        form = InventoryItemForm(request.POST, request.FILES, instance=item)
        if form.is_valid():
            form.save()
            messages.success(request, f"{item.name} updated successfully!")
            return redirect('inventory_list')
    else:
        form = InventoryItemForm(instance=item)
    
    # Reuses the add_item template but changes the title context
    return render(request, 'inventory/add_item.html', {'form': form, 'title': f'Edit {item.name}'})

@login_required
def item_detail(request, pk):
    """
    FIX: Shows the full profile (Specs, QR, History) that doesn't fit in the list table.
    """
    item = get_object_or_404(InventoryItem, pk=pk, owner=request.user)
    return render(request, 'inventory/item_detail.html', {'item': item})

@login_required
def delete_item(request, pk):
    """
    Deletes an item permanently.
    """
    item = get_object_or_404(InventoryItem, pk=pk, owner=request.user)
    
    # Optional Safety: Prevent deleting rented items
    # if item.status == 'RENTED':
    #     messages.error(request, "Cannot delete item while it is currently rented/on job.")
    #     return redirect('inventory_list')

    item.delete()
    messages.success(request, f"{item.name} deleted.")
    return redirect('inventory_list')


# -------------------------------------------------------------------------
# 2. RAPID SCANNER (API & View)
# -------------------------------------------------------------------------

@login_required
def rapid_scan_page(request):
    """
    Renders the Camera Interface for mobile scanning.
    """
    return render(request, 'inventory/rapid_scan.html')

@csrf_exempt
@login_required
def scan_api(request):
    """
    The hidden API that processes the QR code scan from the JS frontend.
    Handles 'Check-Out' and 'Check-In' logic based on the 'mode' parameter.
    """
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            raw_data = data.get('qr_data', '')
            mode = data.get('mode') # 'checkout' or 'checkin'
            
            # 1. Parse UUID from URL (e.g. gigs360.com/scan/<UUID>)
            if '/' in raw_data:
                item_uuid = raw_data.rstrip('/').split('/')[-1]
            else:
                item_uuid = raw_data

            # 2. Find Item
            item = get_object_or_404(InventoryItem, id=item_uuid, owner=request.user)
            
            message = ""
            status_code = "success"

            # 3. Check-Out Logic
            if mode == 'checkout':
                if item.status == 'RENTED':
                    message = f"⚠️ {item.name} is ALREADY checked out."
                    status_code = "warning"
                else:
                    item.status = 'RENTED'
                    item.save()
                    message = f"📤 Checked OUT: {item.name}"

            # 4. Check-In Logic
            elif mode == 'checkin':
                if item.status == 'AVAILABLE':
                    message = f"⚠️ {item.name} is ALREADY in stock."
                    status_code = "warning"
                else:
                    item.status = 'AVAILABLE'
                    item.save()
                    message = f"📥 Checked IN: {item.name}"

            # 5. Audit Trail Update (Record who scanned it and when)
            item.last_scanned_at = timezone.now()
            item.last_scanned_by = request.user
            item.save()

            return JsonResponse({'status': status_code, 'message': message, 'item': item.name})

        except Exception as e:
            return JsonResponse({'status': 'error', 'message': f"Scan Error: {str(e)}"})

    return JsonResponse({'status': 'error', 'message': 'Invalid Request Method'})