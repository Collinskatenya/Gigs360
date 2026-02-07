from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.db import transaction
from django.conf import settings 
import json
from django.utils import timezone

from .models import InventoryItem
from .forms import InventoryItemForm
# Ensure Notification model exists in core/models.py
from core.models import Notification

# -------------------------------------------------------------------------
# 1. GEAR LOCKER MANAGEMENT (With Paywall Logic)
# -------------------------------------------------------------------------

# --- HELPER: CHECK LIMITS ---
def check_inventory_limit(user):
    """
    Returns (True, limit) if user can add more items.
    Returns (False, limit) if user reached their cap.
    """
    # 1. Get Current Count
    current_count = InventoryItem.objects.filter(owner=user).count()
    
    # 2. Get User Plan (Safely from UserProfile)
    try:
        # Assuming OneToOne relationship: User -> UserProfile -> plan
        user_plan = user.userprofile.plan.upper()
    except AttributeError:
        # Fallback if UserProfile doesn't exist yet
        user_plan = 'FREE'

    # 3. Get Limit from Settings (Default to 15 for Free)
    # Define this in settings.py: INVENTORY_LIMITS = {'FREE': 15, 'PRO': 100, 'ENTERPRISE': float('inf')}
    limits = getattr(settings, 'INVENTORY_LIMITS', {'FREE': 15, 'PRO': 100, 'ENTERPRISE': float('inf')})
    limit = limits.get(user_plan, 15)
    
    # 4. Check Limit
    if limit != float('inf') and current_count >= limit:
        return False, limit
    return True, limit

@login_required
def inventory_list(request):
    """ Shows all items owned by the user. """
    items = InventoryItem.objects.filter(owner=request.user).order_by('-created_at')
    
    # Optional: Context for progress bar
    can_add, limit = check_inventory_limit(request.user)
    current_count = items.count()
    
    context = {
        'items': items,
        'current_count': current_count,
        'limit': limit if limit != float('inf') else "Unlimited"
    }
    return render(request, 'inventory/inventory_list.html', context)

@login_required
def add_item(request):
    # --- PAYWALL ENFORCEMENT START (Task 3) ---
    can_add, limit = check_inventory_limit(request.user)
    
    if not can_add:
        try:
            user_plan = request.user.userprofile.plan.upper()
        except:
            user_plan = 'FREE'
            
        next_package = "Pro" if user_plan == 'FREE' else "Enterprise"

        messages.error(
            request, 
            f"🔒 Limit Reached: You have hit the {limit} item limit. Upgrade to {next_package} to add more gear."
        )

        # Auto-Create Notification
        Notification.objects.create(
            user=request.user,
            title="Inventory Limit Reached",
            message=f"Your gear locker is full ({limit} items). Upgrade to {next_package} to continue growing.",
            notification_type='warning',
            link='/upgrade-plan/' 
        )
        return redirect('inventory:inventory_list')
    # --- PAYWALL ENFORCEMENT END ---

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
    try:
        item = InventoryItem.objects.get(pk=pk, owner=request.user)
    except (InventoryItem.DoesNotExist, ValueError):
        messages.warning(request, "⚠️ That item no longer exists or has been deleted.")
        return redirect('inventory:inventory_list')

    return render(request, 'inventory/item_detail.html', {'item': item})

@login_required
def delete_item(request, pk):
    try:
        item = InventoryItem.objects.get(pk=pk, owner=request.user)
        item.delete()
        messages.success(request, f"{item.name} deleted.")
    except (InventoryItem.DoesNotExist, ValueError):
        messages.warning(request, "⚠️ Item was already deleted.")
        
    return redirect('inventory:inventory_list')


# -------------------------------------------------------------------------
# 2. RAPID SCANNER (SECURE & ROBUST)
# -------------------------------------------------------------------------

@login_required
def rapid_scan(request):
    """ Renders the In-App Scanner UI. """
    return render(request, 'inventory/rapid_scan.html')

@login_required
@require_POST
def api_process_scan(request):
    """ 
    Secure API: Toggles item status (Available <-> Rented).
    Uses qr_code_id (UUID) to prevent ID guessing.
    """
    try:
        data = json.loads(request.body)
        qr_uuid = data.get('qr_uuid') # JS sends 'qr_uuid'

        if not qr_uuid:
            return JsonResponse({'success': False, 'message': 'No QR data received.'})

        # 1. SECURITY: Lookup by UUID AND Owner
        # This ensures only the owner can change the status.
        # Use select_for_update to handle rapid-fire scans gracefully (DB Locking).
        with transaction.atomic():
            item = InventoryItem.objects.select_for_update().get(
                qr_code_id=qr_uuid, 
                owner=request.user
            )
            
            # 2. TOGGLE LOGIC
            # Case-insensitive check just to be safe
            status_upper = str(item.status).upper()
            
            if status_upper == 'AVAILABLE':
                item.status = 'RENTED'
                msg = "Checked Out"
                new_status = 'RENTED'
            else:
                # If RENTED, LOST, etc -> Return to Stock
                item.status = 'AVAILABLE'
                msg = "Returned to Stock"
                new_status = 'AVAILABLE'
            
            item.last_scanned_at = timezone.now()
            item.last_scanned_by = request.user
            item.save()

            return JsonResponse({
                'success': True,
                'item_name': item.name,
                'new_status': new_status,
                'message': msg,
                'time': timezone.now().strftime('%H:%M:%S')
            })

    except InventoryItem.DoesNotExist:
        return JsonResponse({
            'success': False, 
            'message': "Item not found or you are not the owner."
        })
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})

# --- PUBLIC LOST & FOUND VIEW ---

def public_item_verify(request, qr_uuid):
    """
    Public page for strangers who scan the QR code.
    """
    item = get_object_or_404(InventoryItem, qr_code_id=qr_uuid)

    # 1. If Owner scans with standard camera -> Redirect to secure management
    if request.user.is_authenticated and item.owner == request.user:
        return redirect('inventory:item_detail', pk=item.id)

    # 2. If Stranger -> Show Lost & Found info
    context = {
        'item_name': item.name,
        # Fallback if owner has no email configured
        'owner_contact': item.owner.email or "support@gigs360.co.ke", 
        'company_name': "Gigs360 Creative Services",
    }
    return render(request, 'inventory/public_lost_found.html', context)