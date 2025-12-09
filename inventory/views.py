from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import InventoryItem
from .forms import InventoryItemForm

@login_required
def inventory_list(request):
    """
    Displays the Gear Locker.
    Filters: Only show items owned by the logged-in user.
    """
    items = InventoryItem.objects.filter(owner=request.user).order_by('-created_at')
    return render(request, 'inventory/inventory_list.html', {'items': items})

@login_required
def add_item(request):
    """
    Logic to add new equipment with STRICT Subscription Limits.
    Strategy:
    - Free: Max 5 Items
    - Pro: Max 50 Items
    - Enterprise: Unlimited
    """
    # ---------------------------------------------------------
    # 1. SUBSCRIPTION LIMIT CHECK
    # ---------------------------------------------------------
    user_plan = getattr(request.user, 'subscription_plan', 'Free')
    current_count = InventoryItem.objects.filter(owner=request.user).count()
    
    limit = 5  # Default Free Limit
    if user_plan == 'Pro':
        limit = 50
    elif user_plan == 'Enterprise':
        limit = 1000000 

    if current_count >= limit:
        messages.error(request, f"Plan limit reached ({limit} items). Upgrade to Pro to add more.")
        return redirect('pricing')

    # ---------------------------------------------------------
    # 2. FORM LOGIC
    # ---------------------------------------------------------
    if request.method == 'POST':
        form = InventoryItemForm(request.POST, request.FILES)
        if form.is_valid():
            item = form.save(commit=False)
            item.owner = request.user 
            item.status = 'AVAILABLE' 
            item.save()
            messages.success(request, f"{item.name} added successfully!")
            return redirect('inventory_list')
    else:
        form = InventoryItemForm()
    
    return render(request, 'inventory/add_item.html', {'form': form})

@login_required
def delete_item(request, pk):
    """
    Deletes an item from the inventory.
    Security: Ensures user can only delete their OWN items.
    """
    item = get_object_or_404(InventoryItem, pk=pk, owner=request.user)
    
    if request.method == 'POST':
        item.delete()
        messages.success(request, "Item deleted successfully.")
        return redirect('inventory_list')
        
    # Safety redirect if accessed via GET
    return redirect('inventory_list')