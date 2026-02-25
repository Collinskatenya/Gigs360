from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.db import transaction
from django.db.models import Q
from django.conf import settings 
import json
from django.utils import timezone

# MODELS & FORMS
from .models import InventoryItem, Category, ItemImage # 🚨 Added ItemImage and Category
from .forms import InventoryItemForm
from core.models import Notification

# =========================================================================
# 0. THE DISCOVERY HUB (Phase 3: Public Marketplace)
# =========================================================================

def marketplace_hub(request):
    """ 
    Open-Door Browsing: No login required. TikTok-style public access to view gear.
    Includes the Global Search Engine (Filters for categories, dates, locations).
    """
    # Only show gear that vendors have marked as 'published'
    items = InventoryItem.objects.filter(is_published=True).select_related('owner', 'category').order_by('-created_at')
    
    # Global Search Engine Logic
    query = request.GET.get('q')
    location = request.GET.get('location')
    category_slug = request.GET.get('category')

    if query:
        items = items.filter(Q(name__icontains=query) | Q(description__icontains=query))
    if location:
        items = items.filter(search_location__icontains=location)
    if category_slug:
        items = items.filter(category__slug=category_slug)

    context = {
        'items': items,
        'categories': Category.objects.all(),
        'search_query': query,
        'location_query': location,
        'title': 'Discovery Hub | Gigs360'
    }
    return render(request, 'inventory/marketplace.html', context)

def public_asset_showroom(request, slug):
    """ 
    Dynamic Asset Showroom: High-converting public product page. 
    Uses the SEO Slug for clean URLs.
    """
    item = get_object_or_404(InventoryItem, slug=slug, is_published=True)
    gallery = item.gallery_images.all() # Fetch the new multi-image gallery
    
    context = {
        'item': item,
        'gallery': gallery,
        'title': f"Rent {item.name} | Gigs360"
    }
    return render(request, 'inventory/asset_showroom.html', context)


# =========================================================================
# 1. GEAR LOCKER MANAGEMENT (Internal Vendor Operations)
# =========================================================================

# --- HELPER: CHECK LIMITS ---
def check_inventory_limit(user):
    """ Returns (True, limit) if user can add more items. """
    current_count = InventoryItem.objects.filter(owner=user).count()
    try:
        user_plan = user.userprofile.plan.upper() 
    except AttributeError:
        user_plan = 'FREE'

    limits = getattr(settings, 'INVENTORY_LIMITS', {'FREE': 15, 'PRO': 100, 'ENTERPRISE': float('inf')})
    limit = limits.get(user_plan, 15)
    
    if limit != float('inf') and current_count >= limit:
        return False, limit
    return True, limit

@login_required
def inventory_list(request):
    """ Shows all items owned by the user. """
    items = InventoryItem.objects.filter(owner=request.user).order_by('-created_at')
    can_add, limit = check_inventory_limit(request.user)
    
    context = {
        'items': items,
        'current_count': items.count(),
        'limit': limit if limit != float('inf') else "Unlimited"
    }
    return render(request, 'inventory/inventory_list.html', context)

@login_required
def add_item(request):
    # --- PAYWALL ENFORCEMENT ---
    can_add, limit = check_inventory_limit(request.user)
    
    if not can_add:
        try:
            user_plan = request.user.userprofile.plan.upper()
        except:
            user_plan = 'FREE'
            
        next_package = "Pro" if user_plan == 'FREE' else "Enterprise"
        messages.error(request, f"🔒 Limit Reached: You have hit the {limit} item limit. Upgrade to {next_package} to add more gear.")
        Notification.objects.create(
            user=request.user, title="Inventory Limit Reached",
            message=f"Your gear locker is full ({limit} items). Upgrade to {next_package} to continue growing.",
            notification_type='warning'
        )
        return redirect('inventory:inventory_list')
    # ---------------------------

    if request.method == 'POST':
        form = InventoryItemForm(request.POST, request.FILES)
        if form.is_valid():
            item = form.save(commit=False)
            item.owner = request.user
            item.save()
            
            # 🚨 INNOVATION: Save multiple gallery images if uploaded
            if 'gallery_images' in request.FILES:
                for f in request.FILES.getlist('gallery_images'):
                    ItemImage.objects.create(item=item, image=f)

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
            
            # 🚨 INNOVATION: Append new gallery images
            if 'gallery_images' in request.FILES:
                for f in request.FILES.getlist('gallery_images'):
                    ItemImage.objects.create(item=item, image=f)
                    
            messages.success(request, f"{item.name} updated successfully!")
            return redirect('inventory:inventory_list')
    else:
        form = InventoryItemForm(instance=item)
    
    return render(request, 'inventory/add_item.html', {'form': form, 'title': f'Edit {item.name}'})

@login_required
def item_detail(request, pk):
    """ INTERNAL detail view for the gear owner. """
    try:
        item = InventoryItem.objects.get(pk=pk, owner=request.user)
    except (InventoryItem.DoesNotExist, ValueError):
        messages.warning(request, "⚠️ That item no longer exists or has been deleted.")
        return redirect('inventory:inventory_list')

    return render(request, 'inventory/item_detail.html', {'item': item})

@login_required
def delete_item(request, pk):
    if request.method == "POST":
        try:
            item = InventoryItem.objects.get(pk=pk, owner=request.user)
            item.delete()
            messages.success(request, f"{item.name} deleted.")
        except (InventoryItem.DoesNotExist, ValueError):
            messages.warning(request, "⚠️ Item was already deleted.")
            
    return redirect('inventory:inventory_list')


# =========================================================================
# 2. RAPID SCANNER (SECURE & ROBUST)
# =========================================================================

@login_required
def rapid_scan(request):
    return render(request, 'inventory/rapid_scan.html')

@login_required
@require_POST
def api_process_scan(request):
    """ Secure API: Toggles item status (Available <-> Rented). """
    try:
        data = json.loads(request.body)
        qr_uuid = data.get('qr_uuid') 

        if not qr_uuid:
            return JsonResponse({'success': False, 'message': 'No QR data received.'})

        with transaction.atomic():
            item = InventoryItem.objects.select_for_update().get(qr_code_id=qr_uuid, owner=request.user)
            
            status_upper = str(item.status).upper()
            if status_upper == 'AVAILABLE':
                item.status = 'RENTED'
                msg = "Checked Out"
                new_status = 'RENTED'
            else:
                item.status = 'AVAILABLE'
                msg = "Returned to Stock"
                new_status = 'AVAILABLE'
            
            item.last_scanned_at = timezone.now()
            item.save()

            return JsonResponse({
                'success': True,
                'item_name': item.name,
                'new_status': new_status,
                'message': msg,
                'time': timezone.now().strftime('%H:%M:%S')
            })

    except InventoryItem.DoesNotExist:
        return JsonResponse({'success': False, 'message': "Item not found or you are not the owner."})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})

# --- PUBLIC LOST & FOUND VIEW ---

def public_item_verify(request, qr_uuid):
    """ Public page for strangers who scan the QR code. """
    item = get_object_or_404(InventoryItem, qr_code_id=qr_uuid)

    if request.user.is_authenticated and item.owner == request.user:
        return redirect('inventory:item_detail', pk=item.id)

    context = {
        'item': item,
        'item_name': item.name,
        'owner_contact': item.owner.email or "support@gigs360.co.ke", 
        'company_name': "Gigs360 Creative Services",
    }
    return render(request, 'inventory/verify_asset.html', context)