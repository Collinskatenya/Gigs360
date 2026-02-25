from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.http import JsonResponse, HttpResponse
from django.utils.dateparse import parse_datetime
from django.views.decorators.http import require_POST
from django.conf import settings 
import json 

# FORMS & MODELS
from .forms import EventForm, DocumentForm, LineItemFormSet
from .models import Event, EventItem, Document
from inventory.models import InventoryItem 
from core.models import Notification, UserProfile

# UTILS (We will create this next)
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
    if request.method == 'POST':
        form = EventForm(request.POST, user=request.user)
        
        if form.is_valid():
            start_date = form.cleaned_data['start_time']
            end_date = form.cleaned_data['end_time']
            selected_items = form.cleaned_data.get('items', []) 
            
            # --- SMART CHECK ---
            if selected_items:
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
                    return render(request, 'events/create_event.html', {
                        'form': form,
                        'google_maps_api_key': settings.GOOGLE_MAPS_API_KEY 
                    })

            event = form.save(commit=False)
            event.user = request.user
            event.updated_by = request.user
            event.save()
            
            if selected_items:
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

    return render(request, 'events/create_event.html', {
        'form': form,
        'google_maps_api_key': settings.GOOGLE_MAPS_API_KEY 
    })

@login_required
def update_event(request, pk):
    try:
        event = Event.objects.get(pk=pk, user=request.user)
    except Event.DoesNotExist:
        messages.warning(request, "⚠️ That event could not be found.")
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
                    return render(request, 'events/create_event.html', {
                        'form': form, 
                        'title': 'Edit Event',
                        'google_maps_api_key': settings.GOOGLE_MAPS_API_KEY
                    })

            event_obj = form.save()
            
            # Sync Manifest Items
            current_manifest_ids = set(EventItem.objects.filter(event=event).values_list('item_id', flat=True))
            new_item_ids = set(item.id for item in new_items)
            
            items_to_add = new_item_ids - current_manifest_ids
            for item_id in items_to_add:
                item_obj = next(i for i in new_items if i.id == item_id)
                EventItem.objects.create(event=event, item=item_obj, handled_by=request.user)

            items_to_remove = current_manifest_ids - new_item_ids
            if items_to_remove:
                EventItem.objects.filter(event=event, item_id__in=items_to_remove).delete()

            messages.success(request, "Event updated successfully!")
            return redirect(DASHBOARD_URL_NAME)
    else:
        form = EventForm(instance=event, user=request.user)

    return render(request, 'events/create_event.html', {
        'form': form, 
        'title': 'Edit Event',
        'google_maps_api_key': settings.GOOGLE_MAPS_API_KEY
    })

@login_required
@require_POST
def delete_event(request, pk):
    event = get_object_or_404(Event, pk=pk, user=request.user)
    title = event.title
    event.delete()
    
    Notification.objects.create(
        user=request.user,
        title="Event Cancelled",
        message=f"Event '{title}' was cancelled. Gear returned to inventory.",
        notification_type='warning'
    )

    messages.success(request, f"Event '{title}' deleted.")
    return redirect('events:event_dashboard')

@login_required
def event_report(request, pk):
    try:
        event = Event.objects.get(pk=pk, user=request.user)
    except Event.DoesNotExist:
        messages.warning(request, "⚠️ Event not found.")
        return redirect(DASHBOARD_URL_NAME)

    manifest_items = event.manifest.select_related('item').all()
    total_gear_value = sum(record.item.daily_rate or 0 for record in manifest_items)
    duration = max((event.end_time - event.start_time).days, 1)
    
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
                    'description': record.item.name,
                    'details': record.item.description[:100] if record.item.description else "", 
                    'quantity': 1,
                    'unit_price': record.item.daily_rate or 0,
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