from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone

# Import forms and models
from .forms import EventForm
from .models import Event, EventItem
from inventory.models import InventoryItem

# --- CONFIGURATION ---
# FIX: This matches name='event_dashboard' in your urls.py
DASHBOARD_URL_NAME = 'event_dashboard' 

@login_required
def event_dashboard(request):
    """
    Displays the Event Operations Dashboard.
    Splits events into 'Upcoming' and 'Past' based on the current time.
    """
    now = timezone.now()
    
    # 1. Upcoming Events (Active or Future)
    upcoming = Event.objects.filter(
        user=request.user, 
        end_time__gte=now
    ).order_by('start_time')
    
    # 2. Past Events (Completed)
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
    Handles Event creation.
    1. Saves Event details & Traceability.
    2. Creates the Gear Manifest.
    3. Updates Inventory Status to 'RENTED' to prevent double-booking.
    """
    if request.method == 'POST':
        form = EventForm(request.POST, user=request.user)
        
        if form.is_valid():
            # A. Save Event & Traceability
            event = form.save(commit=False)
            event.user = request.user          # Owner
            event.updated_by = request.user    # Auditor
            event.save()
            
            # B. Handle Gear Selection
            selected_gear = form.cleaned_data.get('items')
            if selected_gear:
                for item in selected_gear:
                    # 1. Add to Event Manifest
                    EventItem.objects.create(
                        event=event, 
                        item=item,
                        handled_by=request.user, 
                        condition_return='GOOD' 
                    )
                    # 2. Lock Item Status (Automation)
                    item.status = 'RENTED'
                    item.save()
            
            messages.success(request, f"Event '{event.title}' created and gear booked successfully!")
            return redirect(DASHBOARD_URL_NAME)
            
    else:
        form = EventForm(user=request.user)

    return render(request, 'events/create_event.html', {'form': form})

@login_required
def update_event(request, pk):
    """
    Handles Event updates.
    Crucially, it syncs the gear list:
    - Adds new items (and marks them RENTED).
    - Removes unchecked items (and marks them AVAILABLE).
    """
    # Security: Ensure user owns the event
    event = get_object_or_404(Event, pk=pk, user=request.user)

    if request.method == 'POST':
        form = EventForm(request.POST, instance=event, user=request.user)
        
        if form.is_valid():
            # A. Save Event Details
            event_obj = form.save(commit=False)
            event_obj.updated_by = request.user 
            event_obj.save()
            
            # B. Sync Inventory Manifest
            # 1. Identify Changes
            new_selection = form.cleaned_data.get('items', [])
            current_manifest = EventItem.objects.filter(event=event)
            
            current_item_ids = set(current_manifest.values_list('item_id', flat=True))
            new_item_ids = set(item.id for item in new_selection)
            
            # 2. Process ADDITIONS (Items checked in the form)
            items_to_add = new_item_ids - current_item_ids
            for item_id in items_to_add:
                item_obj = InventoryItem.objects.get(id=item_id)
                
                # Lock status
                item_obj.status = 'RENTED'
                item_obj.save()
                
                # Add to manifest
                EventItem.objects.create(
                    event=event,
                    item=item_obj,
                    handled_by=request.user
                )

            # 3. Process REMOVALS (Items unchecked in the form)
            items_to_remove = current_item_ids - new_item_ids
            if items_to_remove:
                # Release status back to AVAILABLE
                InventoryItem.objects.filter(id__in=items_to_remove).update(status='AVAILABLE')
                
                # Remove from manifest
                EventItem.objects.filter(event=event, item_id__in=items_to_remove).delete()

            messages.success(request, "Event details and inventory updated successfully!")
            return redirect(DASHBOARD_URL_NAME)
    else:
        form = EventForm(instance=event, user=request.user)

    return render(request, 'events/create_event.html', {
        'form': form, 
        'title': 'Edit Event'
    })

@login_required
def event_report(request, pk):
    """
    Read-Only Audit Report for Past Events.
    Calculates financials and lists gear usage.
    Required for the 'Past History' tab in the dashboard.
    """
    event = get_object_or_404(Event, pk=pk, user=request.user)
    
    # Efficiently fetch manifest items with their parent inventory details
    manifest_items = event.manifest.select_related('item').all()
    
    # Calculate 'Internal Cost' (How much your gear was worth for this gig)
    # Checks if daily_rate is None (0) to avoid errors
    total_gear_value = sum(record.item.daily_rate or 0 for record in manifest_items)
    
    # Calculate Duration (At least 1 day)
    duration = (event.end_time - event.start_time).days
    if duration < 1: 
        duration = 1
    
    estimated_rental_value = total_gear_value * duration

    context = {
        'event': event,
        'manifest_items': manifest_items,
        'total_gear_value': estimated_rental_value,
        'duration': duration,
    }
    return render(request, 'events/event_report.html', context)