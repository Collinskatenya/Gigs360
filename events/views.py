from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone

# Ensure these match your actual app/model names
from .forms import EventForm
from .models import Event, EventItem
from inventory.models import InventoryItem

# --- URL SYNCHRONIZATION SETUP ---
# CRITICAL: Adjust this variable to match the 'name' attribute in your events/urls.py
DASHBOARD_URL_NAME = 'dashboard' 

@login_required
def event_dashboard(request):
    """
    Displays the Event Operations Dashboard, separating Upcoming and Past events.
    """
    now = timezone.now()
    
    # 1. Upcoming Events (End time is now or in the future)
    upcoming = Event.objects.filter(
        user=request.user, 
        end_time__gte=now
    ).order_by('start_time')
    
    # 2. Past Events (End time is in the past)
    past = Event.objects.filter(
        user=request.user, 
        end_time__lt=now
    ).order_by('-end_time')
    
    return render(request, 'events/dashboard.html', {
        'upcoming': upcoming,
        'past': past
    })

@login_required
def create_event(request):
    """
    Handles Event creation, traceability assignment, manifest generation, 
    and books the inventory.
    """
    if request.method == 'POST':
        form = EventForm(request.POST, user=request.user)
        
        if form.is_valid():
            event = form.save(commit=False)
            
            # --- TRACEABILITY ---
            event.user = request.user
            event.updated_by = request.user
            event.save()
            
            # --- MANIFEST GENERATION & INVENTORY STATUS FIX ---
            selected_gear = form.cleaned_data.get('items')
            if selected_gear:
                for item in selected_gear:
                    EventItem.objects.create(
                        event=event, 
                        item=item,
                        handled_by=request.user, 
                        condition_return='GOOD' 
                    )
                    # 🚨 FIX: Mark the item as RENTED/ON_JOB immediately
                    item.status = 'RENTED'
                    item.save()
            
            messages.success(request, f"Event '{event.title}' created successfully! Inventory booked.")
            return redirect(DASHBOARD_URL_NAME)
            
    else:
        form = EventForm(user=request.user)

    return render(request, 'events/create_event.html', {'form': form})

@login_required
def update_event(request, pk):
    """
    Allows the user to edit an existing event's details, synchronize the gear manifest,
    and update inventory status based on changes.
    """
    event = get_object_or_404(Event, pk=pk, user=request.user)

    if request.method == 'POST':
        form = EventForm(request.POST, instance=event, user=request.user)
        
        if form.is_valid():
            event_obj = form.save(commit=False)
            event_obj.updated_by = request.user 
            event_obj.save()
            
            # 2. HANDLE GEAR CHANGES (Manifest Synchronization)
            new_selection = form.cleaned_data.get('items', [])
            current_manifest = EventItem.objects.filter(event=event)
            current_item_ids = set(current_manifest.values_list('item_id', flat=True))
            new_item_ids = set(item.id for item in new_selection)
            
            # A. Find items to ADD (Book newly checked items)
            items_to_add = new_item_ids - current_item_ids
            for item_id in items_to_add:
                item_obj = InventoryItem.objects.get(id=item_id)
                
                # 🚨 FIX: Mark the new item as RENTED/ON_JOB
                item_obj.status = 'RENTED'
                item_obj.save()
                
                EventItem.objects.create(
                    event=event,
                    item=item_obj,
                    handled_by=request.user # Trace who added it
                )

            # B. Find items to REMOVE (Unbook unchecked items)
            items_to_remove = current_item_ids - new_item_ids
            if items_to_remove:
                # 🚨 FIX: Mark the removed items as AVAILABLE
                InventoryItem.objects.filter(id__in=items_to_remove).update(status='AVAILABLE')
                
                # Delete the manifest records
                EventItem.objects.filter(event=event, item_id__in=items_to_remove).delete()

            messages.success(request, "Event and gear list updated successfully!")
            return redirect(DASHBOARD_URL_NAME)
    else:
        form = EventForm(instance=event, user=request.user)

    return render(request, 'events/create_event.html', {
        'form': form, 
        'title': 'Edit Event'
    })