from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction
from django.conf import settings # <--- Critical: Needed to read limits from settings.py
import json

from .models import InventoryItem
from .forms import InventoryItemForm
from core.models import Notification  # <--- CRITICAL IMPORT FOR BELL ALERTS

# -------------------------------------------------------------------------
# 1. GEAR LOCKER MANAGEMENT
# -------------------------------------------------------------------------

# --- HELPER: CHECK LIMITS ---
def check_inventory_limit(user):
    """
    Returns (True, limit) if user can add more items.
    Returns (False, limit) if user reached their cap.
    """
    # 1. Get current count
    current_count = InventoryItem.objects.filter(owner=user).count()
    
    # 2. Get user's plan (Defaults to 'FREE' if not set)
    user_plan = getattr(user, 'plan', 'FREE').upper() 
    
    # 3. Get the limit from settings.py (Defaults to 20)
    limit = settings.INVENTORY_LIMITS.get(user_plan, 20)
    
    # 4. Check status
    # Note: Enterprise limit is float('inf'), so this check is always False for them (Safe)
    if current_count >= limit:
        return False, limit
    return True, limit

@login_required
def inventory_list(request):
    """ Shows all items owned by the user. """
    items = InventoryItem.objects.filter(owner=request.user).order_by('-created_at')
    return render(request, 'inventory/inventory_list.html', {'items': items})

@login_required
def add_item(request):
    # 1. RUN THE CHECK IMMEDIATELY
    can_add, limit = check_inventory_limit(request.user)
    
    if not can_add:
        # Determine current plan and identify the next upgrade
        user_plan = getattr(request.user, 'plan', 'FREE').upper()
        
        if user_plan == 'FREE':
            next_package = "Pro"
        else:
            next_package = "Enterprise"

        # A. Browser Alert (Immediate Red Box)
        messages.error(
            request, 
            f"🔒 Limit Reached: You have hit the {limit} item limit. Update to the {next_package} package to add more gear."
        )

        # B. Notification Bell (Persistent Alert)
        # This adds the red dot to the bell icon in the dashboard
        Notification.objects.create(
            user=request.user,
            title="Inventory Limit Reached",
            message=f"Your gear locker is full ({limit} items). Update to the {next_package} package to continue growing your inventory.",
            notification_type='warning', # Warning icon
            link='/upgrade-plan/' # Link to upgrade page
        )

        return redirect('inventory:inventory_list')

    if request.method == 'POST':
        form = InventoryItemForm(request.POST, request.FILES)
        if form.is_valid():
            item = form.save(commit=False)
            item.owner = request.user
            item.save()
            messages.success(request, f"{item.name} added to Gear Locker!")
            return redirect('inventory:inventory_list')
    else:
        form = InventoryItemForm()
    
    return render(request, 'inventory/add_item.html', {'form': form, 'title': 'Add New Item'})

@login_required
def update_item(request, pk):
    """ 
    Standard Edit View: Uses get_object_or_404 for clean code.
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
    SAFE MODE: Redirects if item is missing.
    Crucial for handling clicks on notifications for deleted items.
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
    SAFE MODE: Redirects if item is already deleted.
    Prevents 404 errors if a user double-clicks the delete button.
    """
    try:
        item = InventoryItem.objects.get(pk=pk, owner=request.user)
        item.delete()
        messages.success(request, f"{item.name} deleted.")
    except (InventoryItem.DoesNotExist, ValueError):
        messages.warning(request, "⚠️ Item was already deleted.")
        
    return redirect('inventory:inventory_list')


# -------------------------------------------------------------------------
# 2. RAPID SCANNER API
# -------------------------------------------------------------------------

@login_required
def rapid_scan(request):
    return render(request, 'inventory/rapid_scan.html')

@csrf_exempt
@login_required
def process_scan_api(request):
    """ 
    Processes QR code scans safely with database locking.
    """
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Invalid Method'}, status=405)

    try:
        data = json.loads(request.body)
        raw_data = data.get('uuid') or data.get('qr_data', '')

        if not raw_data:
            return JsonResponse({'status': 'error', 'message': 'No Data'}, status=400)

        # Handle full URL scans if necessary
        item_id = raw_data.rstrip('/').split('/')[-1] if '/' in raw_data else raw_data

        with transaction.atomic():
            try:
                # Lock row to prevent race conditions (Double Scans)
                item = InventoryItem.objects.select_for_update().get(id=item_id, owner=request.user)
            except (InventoryItem.DoesNotExist, ValueError):
                return JsonResponse({'status': 'error', 'message': 'Item not found.'}, status=404)

            # Toggle Status Logic
            current_status = str(item.status).capitalize()
            action = ""
            color = ""

            if current_status == 'Available':
                item.status = 'Rented'
                action = "Checked OUT"
                color = "warning"
            elif current_status == 'Rented':
                item.status = 'Available'
                action = "Checked IN"
                color = "success"
            else:
                return JsonResponse({'status': 'error', 'message': f"Item is {item.status}"}, status=400)

            item.save()
            
            return JsonResponse({
                'status': 'success', 
                'message': f"{item.name} {action}",
                'new_state': item.status,
                'color': color
            })

    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)