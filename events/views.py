from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import EventForm

@login_required
def create_event(request):
    # 1. REMOVED ROLE CHECK: Now allowed for ALL logged-in users (Vendor, Agency, Freelancer)
    
    if request.method == 'POST':
        # 2. CRITICAL FIX: Pass 'user=request.user' so the form knows whose inventory to show
        form = EventForm(request.POST, user=request.user)
        
        if form.is_valid():
            event = form.save(commit=False)
            event.planner = request.user # The logged-in user is the planner
            event.save()
            
            # Save the Many-to-Many data (The selected gear checklist)
            form.save_m2m() 
            
            messages.success(request, f"Event '{event.title}' created successfully!")
            return redirect('dashboard')
    else:
        # 3. CRITICAL FIX: Pass 'user' for GET requests too
        form = EventForm(user=request.user)

    # 4. Verify your template name is 'create_event.html'
    return render(request, 'events/create_event.html', {'form': form})