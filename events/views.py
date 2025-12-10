from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from .forms import EventForm
from .models import Event, EventItem
from inventory.models import InventoryItem

@login_required
def event_dashboard(request):
    """
    Displays the Event Operations Dashboard.
    Shows 'Upcoming' vs 'Past' tabs.
    """
    now = timezone.now()
    
    # 1. Upcoming Events (Future)
    upcoming = Event.objects.filter(
        user=request.user, 
        end_time__gte=now
    ).order_by('start_time')
    
    # 2. Past Events (History)
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
    Handles Event creation and generates the Gear Manifest.
    """
    if request.method == 'POST':
        # 1. Pass 'user' so the form can verify ownership of selected items
        form = EventForm(request.POST, user=request.user)
        
        if form.is_valid():
            # 2. Create the Event (Don't save to DB yet)
            event = form.save(commit=False)
            event.user = request.user  # Assign logged-in user
            event.save()
            
            # 3. Generate the Audit Manifest
            selected_gear = form.cleaned_data.get('items')
            
            if selected_gear:
                for item in selected_gear:
                    EventItem.objects.create(event=event, item=item)
            
            messages.success(request, f"Event '{event.title}' created successfully!")
            return redirect('event_dashboard') # Redirect to the dashboard we just defined above
            
    else:
        # 4. Pass 'user' for GET requests so dropdown filters correctly
        form = EventForm(user=request.user)

    return render(request, 'events/create_event.html', {'form': form})