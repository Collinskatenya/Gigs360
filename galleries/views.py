from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from .models import Gallery, Photo, GalleryActivity
from events.models import Event

# --- UTILITY: CAPTURE CLIENT IP ---
def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

# ==========================================
# 1. VENDOR OPERATIONS (Command Center Aware)
# ==========================================

@login_required
def manage_gallery(request, event_id):
    event = get_object_or_404(Event, id=event_id, user=request.user)
    
    gallery, created = Gallery.objects.get_or_create(
        event=event,
        vendor=request.user,
        defaults={
            'name': f"{event.title} - Final Delivery",
            'is_published': True
        }
    )

    # 🚨 TRIPWIRE: Log Gallery Creation
    if created:
        GalleryActivity.objects.create(
            gallery=gallery,
            action_type='CREATED',
            actor=request.user.username,
            details="Gallery initialized for event."
        )

    if request.method == 'POST':
        new_pin = request.POST.get('update_pin')
        if new_pin:
            gallery.access_pin = new_pin.strip().upper()
            gallery.save()
            GalleryActivity.objects.create(
                gallery=gallery,
                action_type='PIN_CHANGED',
                actor=request.user.username,
                details=f"PIN updated to {gallery.access_pin}"
            )
            messages.success(request, "Security PIN updated.")
        
        files = request.FILES.getlist('photos')
        if files:
            for f in files:
                Photo.objects.create(
                    gallery=gallery,
                    high_res_file=f,
                    file_size_bytes=f.size
                )
            messages.success(request, f"Successfully uploaded {len(files)} photos.")
            return redirect('galleries:manage_gallery', event_id=event.id)

    photos = gallery.photos.all()
    activities = gallery.activities.all()[:10]
    
    context = {
        'event': event,
        'gallery': gallery,
        'photos': photos,
        'activities': activities,
    }
    return render(request, 'galleries/manage_gallery.html', context)


# ==========================================
# 2. CLIENT PORTAL (Telemetry Tripwires)
# ==========================================

def client_gallery_view(request, gallery_id):
    gallery = get_object_or_404(Gallery, id=gallery_id)
    client_ip = get_client_ip(request)
    
    if not gallery.is_published:
        return render(request, 'galleries/not_published.html')

    pin_entered = request.session.get(f'gallery_auth_{gallery.id}', False)
    
    if request.method == 'POST':
        submitted_pin = request.POST.get('pin', '').strip().upper()
        if submitted_pin == gallery.access_pin:
            request.session[f'gallery_auth_{gallery.id}'] = True
            pin_entered = True
            
            # 🚨 TRIPWIRE: Log Client Entry
            GalleryActivity.objects.create(
                gallery=gallery,
                action_type='VIEWED',
                actor=f"Client ({client_ip})",
                details="Access granted via PIN."
            )
            messages.success(request, "Access Granted.")
        else:
            messages.error(request, "Invalid PIN. Please try again.")

    if not pin_entered:
        return render(request, 'galleries/pin_entry.html', {'gallery': gallery})

    photos = gallery.photos.all()
    is_unlocked = gallery.is_escrow_unlocked
    
    context = {
        'gallery': gallery,
        'photos': photos,
        'is_unlocked': is_unlocked,
    }
    return render(request, 'galleries/client_view.html', context)


# ==========================================
# 3. MASTER DASHBOARD (All Galleries)
# ==========================================
# 🚨 THIS IS THE VIEW THAT WAS MISSING!

@login_required
def gallery_list(request):
    """
    Displays all active client delivery galleries for the vendor.
    """
    galleries = Gallery.objects.filter(vendor=request.user)
    return render(request, 'galleries/gallery_list.html', {'galleries': galleries})