from django.shortcuts import render, get_object_or_404, redirect
from django.http import Http404, HttpResponseForbidden
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum
from .models import Gallery, Photo
from .forms import GalleryForm

# ==========================================
# 1. PUBLIC CLIENT PORTAL (The Vault)
# ==========================================
def client_gallery_view(request, slug):
    """The isolated, Pixieset-style viewing portal for the client."""
    gallery = get_object_or_404(Gallery, slug=slug)
    
    # Security: If the photographer hasn't published it, hide it completely.
    if not gallery.is_published:
        raise Http404("This collection is currently unavailable or being curated.")

    # Security: The PIN Protection Vault
    session_key = f"gallery_auth_{gallery.id}"
    
    if gallery.access_pin:
        # If they submit a PIN
        if request.method == 'POST':
            entered_pin = request.POST.get('pin', '').strip()
            if entered_pin == gallery.access_pin:
                # Unlock the vault for this session
                request.session[session_key] = True
                return redirect('galleries:client_gallery', slug=slug)
            else:
                return render(request, 'galleries/client_pin.html', {
                    'gallery': gallery, 
                    'error': 'Incorrect PIN. Please try again.'
                })
        
        # If they haven't unlocked the vault yet, show the lock screen
        if not request.session.get(session_key, False):
            return render(request, 'galleries/client_pin.html', {'gallery': gallery})

    # If no PIN is required, or they successfully unlocked it, fetch the photos!
    photos = gallery.photos.all()
    
    return render(request, 'galleries/client_gallery.html', {
        'gallery': gallery,
        'photos': photos,
    })


# ==========================================
# 2. PHOTOGRAPHER DASHBOARD (The Command Center)
# ==========================================

def check_creator_access(user):
    """
    SECURITY BYPASS: Temporarily allowing all logged-in users to access the UI.
    We will lock this down once we confirm your UserProfile role field name!
    """
    return True

def get_storage_stats(user):
    """Calculates the user's total AWS S3 storage usage against their 3GB limit"""
    total_bytes = Photo.objects.filter(gallery__photographer=user).aggregate(total=Sum('file_size'))['total'] or 0
    used_gb = total_bytes / (1024 ** 3) # Convert Bytes to Gigabytes
    limit_gb = 3.0 # The Free Tier Limit!
    percentage = min((used_gb / limit_gb) * 100, 100)
    
    return round(used_gb, 2), limit_gb, round(percentage, 1)

@login_required
def dashboard_gallery_list(request):
    """Displays all active collections for the photographer."""
    if not check_creator_access(request.user):
        messages.error(request, "The Client Delivery module is restricted to Photographers and Creators.")
        return redirect('dashboard')

    galleries = Gallery.objects.filter(photographer=request.user)
    used_gb, limit_gb, storage_pct = get_storage_stats(request.user)

    return render(request, 'galleries/dashboard_list.html', {
        'galleries': galleries,
        'used_gb': used_gb,
        'limit_gb': limit_gb,
        'storage_pct': storage_pct,
    })

@login_required
def dashboard_gallery_create(request):
    """Handles the creation of a new client collection."""
    if not check_creator_access(request.user):
        return redirect('dashboard')

    if request.method == 'POST':
        form = GalleryForm(request.POST, request.FILES)
        if form.is_valid():
            gallery = form.save(commit=False)
            gallery.photographer = request.user
            gallery.save()
            messages.success(request, "Collection created! Start uploading your assets.")
            return redirect('galleries:manage_gallery', uuid=gallery.id)
    else:
        form = GalleryForm()

    return render(request, 'galleries/dashboard_form.html', {'form': form})

@login_required
def dashboard_gallery_manage(request, uuid):
    """The Pixieset-style drag-and-drop management zone for a specific gallery."""
    if not check_creator_access(request.user):
        return redirect('dashboard')

    # Security: Ensure they can only load THEIR specific gallery
    gallery = get_object_or_404(Gallery, id=uuid, photographer=request.user)

    # --- THE UPLOAD & PIN UPDATE ENGINE ---
    if request.method == 'POST':
        
        # 1. Handle PIN updates from the settings sidebar
        if 'update_pin' in request.POST:
            new_pin = request.POST.get('pin', '').strip()
            gallery.access_pin = new_pin
            gallery.save()
            messages.success(request, "Gallery Security PIN updated.")
            return redirect('galleries:manage_gallery', uuid=gallery.id)
            
        # 2. Handle asynchronous multi-file Drag & Drop uploads
        files = request.FILES.getlist('photos')
        if files:
            for f in files:
                Photo.objects.create(
                    gallery=gallery,
                    image=f,
                    original_filename=f.name,
                    file_size=f.size
                )
            messages.success(request, f"Successfully processed {len(files)} high-res photos.")
            return redirect('galleries:manage_gallery', uuid=gallery.id)

    # Fetch stats and photos for the render
    photos = gallery.photos.all()
    used_gb, limit_gb, storage_pct = get_storage_stats(request.user)

    return render(request, 'galleries/dashboard_manage.html', {
        'gallery': gallery,
        'photos': photos,
        'used_gb': used_gb,
        'limit_gb': limit_gb,
        'storage_pct': storage_pct,
    })