from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Space, Post, Comment
from .forms import PostForm
from inventory.models import InventoryItem 

# 🚨 REMOVED @login_required: The global feed is now open to the public!
def community_hub(request):
    """
    Public landing page for the Community. Shows all spaces, global feed, and the Market Hub.
    """
    spaces = Space.objects.all().order_by('cluster', 'order')
    market_gear = InventoryItem.objects.filter(status='AVAILABLE').select_related('owner')[:8]
    posts = Post.objects.select_related('author', 'space', 'linked_gear').all()[:15]
    
    context = {
        'spaces': spaces,
        'posts': posts,
        'market_gear': market_gear,
        'active_space': 'home' 
    }
    return render(request, 'community/hub.html', context)

# 🚨 REMOVED @login_required: Guests can view specific channels!
def space_detail(request, slug):
    """
    Public feed for a single space (e.g., 'The Gig-Board')
    """
    space = get_object_or_404(Space, slug=slug)
    spaces = Space.objects.all().order_by('cluster', 'order')
    market_gear = InventoryItem.objects.filter(status='AVAILABLE').select_related('owner')[:8]
    
    # 🚨 MONETIZATION & SECURITY TRIPWIRE FOR GUESTS
    if space.is_premium_only:
        if not request.user.is_authenticated:
            messages.warning(request, "This is a Premium space. Please log in to view it.")
            return redirect('login')
        elif not hasattr(request.user, 'userprofile') or not request.user.userprofile.is_verified:
            messages.warning(request, "This space is reserved for Pro and Verified members.")
            return redirect('community:hub')

    posts = space.posts.select_related('author', 'linked_gear').all()
    
    context = {
        'space': space,
        'spaces': spaces,
        'posts': posts,
        'market_gear': market_gear,
        'active_space': space.slug
    }
    return render(request, 'community/hub.html', context)

# 🔒 KEPT @login_required: You MUST be logged in to actually post!
@login_required
def create_post(request, slug):
    """
    The creation engine where users draft posts and attach gear. (Protected)
    """
    space = get_object_or_404(Space, slug=slug)
    
    # SECURITY: Prevent unverified users from posting in admin-only channels (e.g., Announcements)
    if space.admin_only_post and not request.user.is_staff:
        messages.error(request, "Only Gigs360 Admins can post in this channel.")
        return redirect('community:space_detail', slug=space.slug)
        
    if space.is_premium_only and (not hasattr(request.user, 'userprofile') or not request.user.userprofile.is_verified):
        messages.error(request, "You need a verified account to post in this premium space.")
        return redirect('community:hub')

    if request.method == 'POST':
        form = PostForm(request.POST, user=request.user)
        if form.is_valid():
            new_post = form.save(commit=False)
            new_post.space = space
            new_post.author = request.user
            new_post.save()
            messages.success(request, f"Your message was sent to #{space.slug}!")
            return redirect('community:space_detail', slug=space.slug)
    else:
        form = PostForm(user=request.user)

    context = {
        'form': form,
        'space': space,
    }
    return render(request, 'community/create_post.html', context)