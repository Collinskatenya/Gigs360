from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.http import JsonResponse, HttpResponse
from django.utils.dateparse import parse_datetime
from django.views.decorators.http import require_POST
from django.conf import settings 
from django.db.models import Q  # 🚨 Added for complex calendar queries
import json 

# FORMS & MODELS
from .forms import EventForm, DocumentForm, LineItemFormSet
from .models import Event, EventItem, Document
from inventory.models import InventoryItem 
from core.models import Notification, UserProfile

# UTILS
from .utils import render_to_pdf

# --- CONFIGURATION ---
DASHBOARD_URL_NAME = 'events:event_dashboard' 

# ==========================================
# 1. EVENT DASHBOARD & OPERATIONS
# ==========================================

@login_required
def event_dashboard(request):
    """
    Displays the Event Operations Dashboard.
    🚨 PHASE 4 UPGRADE: Now filters out CANCELLED events from the active timeline.
    """
    now = timezone.now()
    
    upcoming = Event.objects.filter(
        user=request.user, 
        end_time__gte=now
    ).exclude(status='CANCELLED').prefetch_related('manifest__item').order_by('start_time')
    
    past = Event.objects.filter(
        user=request.user, 
        end_time__lt=now
    ).exclude(status='CANCELLED').order_by('-end_time')
    
    # --- INVENTORY STATS & LIMITS ---
    inventory_count = InventoryItem.objects.filter(owner=request.user).count()
    
    try:
        profile = request.user.userprofile
        user_plan = profile.plan.upper()
    except UserProfile.DoesNotExist:
        user_plan = 'FREE'
    
    limits = getattr(settings, 'INVENTORY_LIMITS', {'FREE': 15, 'PRO': 100, 'ENTERPRISE': float('inf')})
    limit = limits.get(user_plan, 15)
    
    # Calculate Progress Bar
    if limit == float('inf'):
        limit_display = "Unlimited"
        progress_width = (inventory_count / 1000) * 100 
    else:
        limit_display = limit
        progress_width = (inventory_count / limit) * 100 if limit > 0 else 100

    return render(request, 'events/dashboard.html', {
        'upcoming': upcoming,
        'past': past,
        'inventory_count': inventory_count,
        'inventory_limit': limit_display,
        'progress_width': min(progress_width, 100),
    })

@login_required
def check_gear_availability(request):
    """
    API Endpoint for Smart Availability check.
    🚨 PHASE 4 UPGRADE: True mathematical overlap prevention. Considers Gig Status!
    """
    start_str = request.GET.get('start')
    end_str = request.GET.get('end')

    if not start_str or not end_str:
        return JsonResponse({'items': []})

    try:
        new_start = parse_datetime(start_str)
        new_end = parse_datetime(end_str)

        # 1. Find overlapping time windows, IGNORING cancelled gigs
        conflicting_events = Event.objects.filter(
            user=request.user,
            start_time__lt=new_end, # Math: Start A < End B
            end_time__gt=new_start  # Math: End A > Start B
        ).exclude(status='CANCELLED')

        # 2. Find gear inside those gigs that is actually locked
        booked_item_ids = EventItem.objects.filter(
            event__in=conflicting_events,
            status__in=['APPROVED', 'DISPATCHED'] # Only block if vendor actually approved it
        ).values_list('item_id', flat=True)

        # 3. Return what is left
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
    if request.method == 'POST':
        form = EventForm(request.POST, user=request.user)
        
        if form.is_valid():
            start_date = form.cleaned_data['start_time']
            end_date = form.cleaned_data['end_time']
            selected_items = form.cleaned_data.get('items', []) 
            
            # --- 🚨 PHASE 4: THE SAAS CART CHECK ---
            if selected_items:
                overlapping_events = Event.objects.filter(
                    user=request.user,
                    start_time__lt=end_date,
                    end_time__gt=start_date
                ).exclude(status='CANCELLED')
                
                conflict_items = EventItem.objects.filter(
                    event__in=overlapping_events,
                    item__in=selected_items,
                    status__in=['APPROVED', 'DISPATCHED']
                ).select_related('item')
                
                if conflict_items.exists():
                    names = ", ".join([r.item.name for r in conflict_items])
                    messages.error(request, f"❌ Booking Failed: The following items are already booked for these dates: {names}")
                    return render(request, 'events/create_event.html', {
                        'form': form,
                        'google_maps_api_key': getattr(settings, 'GOOGLE_MAPS_API_KEY', '')
                    })

            # Save the Anchor (Event)
            event = form.save(commit=False)
            event.user = request.user
            event.updated_by = request.user
            # Automatically set to APPROVED since the Vendor is creating their own gig
            event.status = 'APPROVED' 
            event.save()
            
            # Save the Line Items (Gear)
            if selected_items:
                for item in selected_items:
                    EventItem.objects.create(
                        event=event, 
                        item=item,
                        handled_by=request.user, 
                        status='APPROVED', # Activates the double-booking lock
                        condition_return='GOOD' 
                    )
            
            messages.success(request, f"Gig '{event.title}' created and calendar locked!")
            return redirect(DASHBOARD_URL_NAME)
            
    else:
        form = EventForm(user=request.user)

    return render(request, 'events/create_event.html', {
        'form': form,
        'google_maps_api_key': getattr(settings, 'GOOGLE_MAPS_API_KEY', '') 
    })

@login_required
def update_event(request, pk):
    try:
        event = Event.objects.get(pk=pk, user=request.user)
    except Event.DoesNotExist:
        messages.warning(request, "⚠️ That gig could not be found.")
        return redirect(DASHBOARD_URL_NAME)

    if request.method == 'POST':
        form = EventForm(request.POST, instance=event, user=request.user)
        
        if form.is_valid():
            new_start = form.cleaned_data['start_time']
            new_end = form.cleaned_data['end_time']
            new_items = form.cleaned_data.get('items', []) 

            if new_items:
                overlapping_events = Event.objects.filter(
                    user=request.user,
                    start_time__lt=new_end,
                    end_time__gt=new_start
                ).exclude(id=event.id).exclude(status='CANCELLED')
                
                conflict_items = EventItem.objects.filter(
                    event__in=overlapping_events,
                    item__in=new_items,
                    status__in=['APPROVED', 'DISPATCHED']
                )
                
                if conflict_items.exists():
                    names = ", ".join([r.item.name for r in conflict_items])
                    messages.error(request, f"❌ Update Failed: Time conflict with items: {names}")
                    return render(request, 'events/create_event.html', {
                        'form': form, 
                        'title': 'Edit Gig Ops',
                        'google_maps_api_key': getattr(settings, 'GOOGLE_MAPS_API_KEY', '')
                    })

            event_obj = form.save()
            
            # Sync Manifest Items
            current_manifest_ids = set(EventItem.objects.filter(event=event).values_list('item_id', flat=True))
            new_item_ids = set(item.id for item in new_items)
            
            items_to_add = new_item_ids - current_manifest_ids
            for item_id in items_to_add:
                item_obj = next(i for i in new_items if i.id == item_id)
                EventItem.objects.create(event=event, item=item_obj, handled_by=request.user, status='APPROVED')

            items_to_remove = current_manifest_ids - new_item_ids
            if items_to_remove:
                # Instead of deleting, we could mark them 'REJECTED', but deletion is fine for Vendor self-management.
                EventItem.objects.filter(event=event, item_id__in=items_to_remove).delete()

            messages.success(request, "Gig parameters updated successfully!")
            return redirect(DASHBOARD_URL_NAME)
    else:
        form = EventForm(instance=event, user=request.user)

    return render(request, 'events/create_event.html', {
        'form': form, 
        'title': 'Edit Gig Ops',
        'google_maps_api_key': getattr(settings, 'GOOGLE_MAPS_API_KEY', '')
    })

@login_required
@require_POST
def delete_event(request, pk):
    """
    🚨 PHASE 4 UPGRADE: Safe Deletion Protocol.
    Do not delete historical data; soft-cancel it instead if it has financial weight.
    """
    event = get_object_or_404(Event, pk=pk, user=request.user)
    title = event.title
    
    # If the gig has generated invoices or is already completed, Soft Cancel it to preserve the ledger.
    if event.status in ['COMPLETED', 'ACTIVE'] or event.documents.exists():
        event.status = 'CANCELLED'
        event.save()
        # Release the gear back to the calendar
        event.manifest.update(status='REJECTED')
        
        Notification.objects.create(
            user=request.user, title="Gig Cancelled",
            message=f"Gig '{title}' was cancelled. The accounting ledger was preserved and gear was released.",
            notification_type='warning'
        )
        messages.success(request, f"Gig '{title}' safely cancelled.")
    else:
        # Hard delete is fine for drafts or mistakes
        event.delete()
        messages.success(request, f"Draft Gig '{title}' deleted permanently.")

    return redirect('events:event_dashboard')

@login_required
def event_report(request, pk):
    try:
        event = Event.objects.get(pk=pk, user=request.user)
    except Event.DoesNotExist:
        messages.warning(request, "⚠️ Gig not found.")
        return redirect(DASHBOARD_URL_NAME)

    manifest_items = event.manifest.select_related('item').all()
    # 🚨 PHASE 4: Use the locked_daily_rate for accurate historical reporting
    total_gear_value = sum(record.locked_daily_rate for record in manifest_items)
    
    # Correct duration calculation
    duration = (event.end_time.date() - event.start_time.date()).days + 1
    
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
    Generates Quotes/Invoices for a specific Event.
    """
    try:
        event = Event.objects.get(pk=event_id, user=request.user)
    except Event.DoesNotExist:
        messages.warning(request, "⚠️ Event not found.")
        return redirect(DASHBOARD_URL_NAME)

    inventory_qs = InventoryItem.objects.filter(owner=request.user).values('name', 'daily_rate', 'description')
    inventory_json = json.dumps(list(inventory_qs), default=str)

    if request.method == 'POST':
        form = DocumentForm(request.POST)
        formset = LineItemFormSet(request.POST)

        if form.is_valid() and formset.is_valid():
            # 1. Save Parent Document
            doc = form.save(commit=False)
            doc.event = event
            doc.user = request.user
            doc.save() 

            # 2. CAPTURE BRAND COLOR
            brand_color = form.cleaned_data.get('brand_color')
            if brand_color:
                profile = request.user.userprofile
                profile.invoice_color_theme = brand_color
                profile.save()

            # 3. Bind Formset
            formset.instance = doc
            formset.save() 

            # 4. Calculate Totals
            total = sum(item.total_price for item in doc.items.all())
            doc.subtotal = total
            doc.total_amount = total
            doc.save()

            messages.success(request, f"{doc.get_doc_type_display()} created successfully!")
            return redirect('events:document_list')
    else:
        # Pre-fill data
        initial_data = {
            'client_name': event.client_name,
            'client_phone': event.client_contact,
            'client_email': getattr(event, 'client_email', ''),
            'issue_date': timezone.now().date(),
            'due_date': timezone.now().date() + timezone.timedelta(days=7),
            'brand_color': request.user.userprofile.invoice_color_theme or '#0f172a'
        }
        
        formset_initial = []
        if request.GET.get('populate') == 'true':
            manifest_items = event.manifest.all()
            for record in manifest_items:
                formset_initial.append({
                    'description': record.item.name if record.item else record.item_name_snapshot,
                    'details': record.item.description[:100] if record.item and record.item.description else "", 
                    'quantity': 1,
                    # 🚨 PHASE 4: Pull from the locked rate, not the current inventory rate!
                    'unit_price': record.locked_daily_rate,
                })
                
        form = DocumentForm(initial=initial_data)
        formset = LineItemFormSet(initial=formset_initial)
        formset.extra = 0 if formset_initial else 1

    return render(request, 'events/create_quote.html', {
        'form': form,
        'formset': formset,
        'event': event,
        'inventory_json': inventory_json,
    })

@login_required
def document_list(request):
    documents = Document.objects.filter(user=request.user).order_by('-created_at')
    context = {'documents': documents}
    return render(request, 'events/document_list.html', context)

@login_required
def generate_document_pdf(request, pk):
    """
    Generates a professional PDF.
    """
    try:
        doc = Document.objects.get(pk=pk, user=request.user)
    except (Document.DoesNotExist, ValueError):
        messages.warning(request, "⚠️ Document not found.")
        return redirect('events:document_list')
    
    context = {
        'doc': doc,
        'items': doc.items.all(),
        'user': request.user,
        'profile': request.user.userprofile, # CRITICAL FOR TRACEABILITY
        'company_name': "Gigs360 Creative Services", 
        'company_email': request.user.email,
        'brand_color': request.user.userprofile.invoice_color_theme or '#0f172a'
    }
    
    pdf = render_to_pdf('events/invoice_pdf.html', context)
    
    if pdf:
        filename = f"{doc.doc_number}_{doc.client_name}.pdf"
        response = HttpResponse(pdf, content_type='application/pdf')
        
        if request.GET.get('download'):
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
        else:
            response['Content-Disposition'] = f'inline; filename="{filename}"'
            
        return response
        
    return HttpResponse("Error generating PDF", status=500)

@login_required
@require_POST 
def delete_document(request, pk):
    doc = get_object_or_404(Document, pk=pk, user=request.user)
    
    if str(doc.status).upper() != 'DRAFT':
        messages.error(request, f"⛔ Restricted: Cannot delete {doc.doc_number} because it is {doc.status}.")
        return redirect('events:document_list')

    doc_number = doc.doc_number
    doc.delete()
    
    Notification.objects.create(
        user=request.user,
        title="Document Deleted",
        message=f"Draft document {doc_number} was permanently deleted.",
        notification_type='success'
    )

    messages.success(request, f"✅ Document {doc_number} deleted successfully.")
    return redirect('events:document_list')