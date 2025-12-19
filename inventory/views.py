from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.db import transaction  # Import for database safety
import json

# VERIFIED: Correct Model Import
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
            # VERIFIED: Namespace 'inventory:' used correctly
            return redirect('inventory:inventory_list')
    else:
        form = InventoryItemForm()
    
    return render(request, 'inventory/add_item.html', {'form': form, 'title': 'Add New Item'})

@login_required
def edit_item(request, pk):
    """
    Allows editing details like Status, Serial, or Photo.
    """
    item = get_object_or_404(InventoryItem, pk=pk, owner=request.user)
    
    if request.method == 'POST':
        form = InventoryItemForm(request.POST, request.FILES, instance=item)
        if form.is_valid():
            form.save()
            messages.success(request, f"{item.name} updated successfully!")
            return redirect('inventory:inventory_list')
    else:
        form = InventoryItemForm(instance=item)
    
    return render(request, 'inventory/add_item.html', {'form': form, 'title': f'Edit {item.name}'})

@login_required
def item_detail(request, pk):
    """
    Shows the full profile (Specs, QR, History).
    SAFE MODE: Redirects to locker if item is missing (Fixes 404 Crash).
    """
    try:
        item = InventoryItem.objects.get(pk=pk, owner=request.user)
    except (InventoryItem.DoesNotExist, ValueError):
        messages.warning(request, "⚠️ That item no longer exists or has been deleted.")
        return redirect('inventory:inventory_list')

    return render(request, 'inventory/item_detail.html', {'item': item})

@login_required
def delete_item(request, pk):
    """
    Deletes an item permanently.
    """
    item = get_object_or_404(InventoryItem, pk=pk, owner=request.user)
    item.delete()
    messages.success(request, f"{item.name} deleted.")
    return redirect('inventory:inventory_list')


# -------------------------------------------------------------------------
# 2. RAPID SCANNER (API & View)
# -------------------------------------------------------------------------

@login_required
def rapid_scan(request):
    """
    Renders the Camera Interface for mobile scanning.
    """
    return render(request, 'inventory/rapid_scan.html')

@csrf_exempt
@login_required
def scan_api(request):
    """
    The hidden API that processes the QR code scan from the JS frontend.
    ROBUST VERSION: Handles JSON errors, DB locking, and invalid UUIDs.
    """
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Invalid Request Method'}, status=405)

    try:
        data = json.loads(request.body)
        # Matches the JS payload key 'uuid' from the frontend script we wrote
        raw_data = data.get('uuid') 
        
        # Fallback if frontend sends 'qr_data' (legacy compatibility)
        if not raw_data:
            raw_data = data.get('qr_data', '')

        if not raw_data:
            return JsonResponse({'status': 'error', 'message': 'No QR data provided'}, status=400)

        # 1. Parse ID safely
        # Handle cases where scan is a full URL "https://gigs360.com/view/UUID/"
        if '/' in raw_data:
            item_id = raw_data.rstrip('/').split('/')[-1]
        else:
            item_id = raw_data

        # 2. Atomic Transaction for Safety (Concurrency Check)
        with transaction.atomic():
            # Lock the row so no one else can edit it while we are checking it
            try:
                # select_for_update() locks the row in the DB until this block finishes
                item = InventoryItem.objects.select_for_update().get(id=item_id, owner=request.user)
            except (InventoryItem.DoesNotExist, ValueError):
                return JsonResponse({'status': 'error', 'message': 'Item not found in your locker.'}, status=404)

            # 3. Robust Toggle Logic (Smart Check-In/Out)
            previous_status = item.status
            message = ""
            status_code = "success"
            color = "success"

            if item.status == 'Available':
                item.status = 'Rented'
                action = "Checked OUT"
                color = "warning" # Orange for rented
            elif item.status == 'Rented':
                item.status = 'Available'
                action = "Checked IN"
                color = "success" # Green for available
            else:
                # Edge case for 'Lost' or 'Maintenance' - Don't auto-toggle
                return JsonResponse({
                    'status': 'error', 
                    'message': f"Item is marked as {item.status}. Cannot auto-scan."
                }, status=400)

            # 4. Save & Audit (You can extend this to save to a History Log model later)
            item.save()
            
            return JsonResponse({
                'status': 'success', 
                'message': f"{item.name} successfully {action}",
                'new_state': item.status,
                'item_name': item.name,
                'color': color
            })

    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Invalid JSON Data'}, status=400)
    except Exception as e:
        # Catch-all for unexpected server errors
        return JsonResponse({'status': 'error', 'message': f"Server Error: {str(e)}"}, status=500)