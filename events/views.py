from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.http import JsonResponse, HttpResponse
from django.utils.dateparse import parse_datetime
import json # <--- Added for Smart Autocomplete

# Import forms and models
from .forms import EventForm, DocumentForm, LineItemFormSet
from .models import Event, EventItem, Document
from inventory.models import InventoryItem 
from .utils import render_to_pdf

# --- CONFIGURATION ---
DASHBOARD_URL_NAME = 'event_dashboard' 

# ==========================================
# 1. EVENT DASHBOARD & OPERATIONS
# ==========================================

@login_required
def event_dashboard(request):
    """
    Displays the Event Operations Dashboard.
    """
    now = timezone.now()
    
    upcoming = Event.objects.filter(
        user=request.user, 
        end_time__gte=now
    ).prefetch_related('manifest__item').order_by('start_time')
    
    past = Event.objects.filter(
        user=request.user, 
        end_time__lt=now
    ).order_by('-end_time')
    
    return render(request, 'events/dashboard.html', {
        'upcoming': upcoming,
        'past': past
    })

@login_required
def check_gear_availability(request):
    """
    API Endpoint for Smart Availability check.
    """
    start_str = request.GET.get('start')
    end_str = request.GET.get('end')

    if not start_str or not end_str:
        return JsonResponse({'items': []})

    try:
        new_start = parse_datetime(start_str)
        new_end = parse_datetime(end_str)

        conflicting_events = Event.objects.filter(
            user=request.user,
            start_time__lt=new_end,
            end_time__gt=new_start
        )

        booked_item_ids = EventItem.objects.filter(
            event__in=conflicting_events
        ).values_list('item_id', flat=True)

        available_items = InventoryItem.objects.filter(
            owner=request.user
        ).exclude(
            id__in=booked_item_ids
        ).exclude(
            status__in=['LOST', 'DAMAGED']
        ).values('id')

        return JsonResponse({'items': list(available_items)})

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
def create_event(request):
    """
    Creates an event with conflict checks.
    """
    if request.method == 'POST':
        form = EventForm(request.POST, user=request.user)
        
        if form.is_valid():
            start_date = form.cleaned_data['start_time']
            end_date = form.cleaned_data['end_time']
            selected_items = form.cleaned_data.get('items', []) 
            
            overlapping_events = Event.objects.filter(
                user=request.user,
                start_time__lte=end_date,
                end_time__gte=start_date
            )
            
            conflict_items = EventItem.objects.filter(
                event__in=overlapping_events,
                item__in=selected_items
            ).select_related('item')
            
            if conflict_items.exists():
                names = ", ".join([r.item.name for r in conflict_items])
                messages.error(request, f"❌ Booking Failed: The following items are already booked: {names}")
                return render(request, 'events/create_event.html', {'form': form})

            event = form.save(commit=False)
            event.user = request.user
            event.updated_by = request.user
            event.save()
            
            for item in selected_items:
                EventItem.objects.create(
                    event=event, 
                    item=item,
                    handled_by=request.user, 
                    condition_return='GOOD' 
                )
            
            messages.success(request, f"Event '{event.title}' created successfully!")
            return redirect(DASHBOARD_URL_NAME)
            
    else:
        form = EventForm(user=request.user)

    return render(request, 'events/create_event.html', {'form': form})

@login_required
def update_event(request, pk):
    """
    Updates an event with conflict checks.
    """
    event = get_object_or_404(Event, pk=pk, user=request.user)

    if request.method == 'POST':
        form = EventForm(request.POST, instance=event, user=request.user)
        
        if form.is_valid():
            new_start = form.cleaned_data['start_time']
            new_end = form.cleaned_data['end_time']
            new_items = form.cleaned_data.get('items', []) 

            overlapping_events = Event.objects.filter(
                user=request.user,
                start_time__lte=new_end,
                end_time__gte=new_start
            ).exclude(id=event.id)
            
            conflict_items = EventItem.objects.filter(
                event__in=overlapping_events,
                item__in=new_items
            )
            
            if conflict_items.exists():
                names = ", ".join([r.item.name for r in conflict_items])
                messages.error(request, f"❌ Update Failed: Conflict with items: {names}")
                return render(request, 'events/create_event.html', {'form': form, 'title': 'Edit Event'})

            event_obj = form.save()
            
            current_manifest_ids = set(EventItem.objects.filter(event=event).values_list('item_id', flat=True))
            new_item_ids = set(item.id for item in new_items)
            
            # Add new items
            items_to_add = new_item_ids - current_manifest_ids
            for item_id in items_to_add:
                item_obj = next(i for i in new_items if i.id == item_id)
                EventItem.objects.create(event=event, item=item_obj, handled_by=request.user)

            # Remove unchecked items
            items_to_remove = current_manifest_ids - new_item_ids
            if items_to_remove:
                EventItem.objects.filter(event=event, item_id__in=items_to_remove).delete()

            messages.success(request, "Event updated successfully!")
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
    Read-Only Audit Report.
    """
    event = get_object_or_404(Event, pk=pk, user=request.user)
    manifest_items = event.manifest.select_related('item').all()
    
    total_gear_value = sum(record.item.daily_rate or 0 for record in manifest_items)
    duration = (event.end_time - event.start_time).days
    if duration < 1: duration = 1
    
    context = {
        'event': event,
        'manifest_items': manifest_items,
        'total_gear_value': total_gear_value * duration,
        'duration': duration,
        'today': timezone.now(),
    }
    return render(request, 'events/event_report.html', context)


# ==========================================
# 2. SMART CONTRACT ENGINE (Quotes & Invoices)
# ==========================================

@login_required
def create_document(request, event_id):
    """
    Frontend view: Generates Quotes/Invoices for a specific Event.
    Includes Smart Logic to pre-fill data from the Event Manifest and Inventory.
    """
    event = get_object_or_404(Event, pk=event_id, user=request.user)

    # 1. Fetch Inventory for "Quick-Add" Autocomplete (Serialize for JS)
    # This allows Vendors/Agencies to quickly pick services they added to their locker
    inventory_qs = InventoryItem.objects.filter(owner=request.user).values('name', 'daily_rate', 'description')
    inventory_json = json.dumps(list(inventory_qs), default=str)

    if request.method == 'POST':
        form = DocumentForm(request.POST)
        formset = LineItemFormSet(request.POST)

        if form.is_valid() and formset.is_valid():
            # 1. Save Document
            doc = form.save(commit=False)
            doc.event = event
            doc.user = request.user
            doc.save()

            # 2. Save Line Items
            items = formset.save(commit=False)
            for item in items:
                item.document = doc
                item.save()
            formset.save() # Handle deletions

            # 3. Recalculate Totals
            total = sum(item.quantity * item.unit_price for item in doc.items.all())
            doc.subtotal = total
            doc.total_amount = total
            doc.save()

            messages.success(request, f"{doc.get_doc_type_display()} created successfully!")
            # Redirect to PDF for instant download/preview
            return redirect('generate_pdf', pk=doc.pk)
    else:
        # Pre-fill data from Event
        initial_data = {
            'client_name': event.client_name,
            'client_phone': event.client_contact,
            'issue_date': timezone.now().date(),
            'due_date': timezone.now().date() + timezone.timedelta(days=7),
        }
        
        # SMART UX: Check if user clicked "Import from Manifest"
        formset_initial = []
        if request.GET.get('populate') == 'true':
            manifest_items = event.manifest.all()
            for record in manifest_items:
                # Vendors/Agencies: This works for "Services" too if they are in the locker
                formset_initial.append({
                    'description': record.item.name,
                    'details': record.item.description[:100] if record.item.description else "", 
                    'quantity': 1,
                    'unit_price': record.item.daily_rate or 0,
                })
                
        form = DocumentForm(initial=initial_data)
        
        # Initialize Formset with data (if any)
        formset = LineItemFormSet(initial=formset_initial)
        # If we pre-filled data, don't show extra empty rows
        formset.extra = 0 if formset_initial else 1

    return render(request, 'events/create_document.html', {
        'form': form,
        'formset': formset,
        'event': event,
        'inventory_json': inventory_json, # Pass inventory data to JS for autocomplete
    })

@login_required
def document_list(request):
    """
    The 'Filing Cabinet': Lists all Quotes, Invoices, and Receipts.
    """
    documents = Document.objects.filter(user=request.user).order_by('-created_at')
    
    context = {
        'documents': documents
    }
    return render(request, 'events/document_list.html', context)

@login_required
def generate_document_pdf(request, pk):
    """
    Generates a professional PDF (KK Photography Style).
    """
    doc = get_object_or_404(Document, pk=pk, user=request.user)
    
    context = {
        'doc': doc,
        'items': doc.items.all(),
        'user': request.user,
        'company_name': "Gigs360 Creative Services", 
        'company_email': request.user.email,
    }
    
    pdf = render_to_pdf('events/invoice_pdf.html', context)
    
    if pdf:
        filename = f"{doc.doc_number}_{doc.client_name}.pdf"
        response = HttpResponse(pdf, content_type='application/pdf')
        
        # SMART TOGGLE: Check if user wants to Download or Preview
        if request.GET.get('download'):
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
        else:
            response['Content-Disposition'] = f'inline; filename="{filename}"'
            
        return response
        
    return HttpResponse("Error generating PDF", status=500)