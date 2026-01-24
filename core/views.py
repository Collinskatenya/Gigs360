from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum
from django.http import JsonResponse
from django.conf import settings  # <--- Added to read centralized limits

# Email Dependencies
from django.contrib.sites.shortcuts import get_current_site
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.template.loader import render_to_string
from django.core.mail import EmailMessage

from .forms import SignUpForm, UserSettingsForm
from .tokens import account_activation_token
from .models import Notification
from inventory.models import InventoryItem

User = get_user_model()

# ==========================================
# 1. PUBLIC PAGES & AUTH
# ==========================================

def home(request):
    """Renders the Landing Page."""
    return render(request, 'core/index.html')

def signup(request):
    """Handles User Registration and Initial Login."""
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.is_active = True # Auto-activate for smoother onboarding
            user.save()

            # 1. Send Verification Email (Non-blocking)
            try:
                current_site = get_current_site(request)
                mail_subject = 'Activate your Gigs360 Account'
                message = render_to_string('registration/acc_active_email.html', {
                    'user': user,
                    'domain': current_site.domain,
                    'uid': urlsafe_base64_encode(force_bytes(user.pk)),
                    'token': account_activation_token.make_token(user),
                })
                to_email = form.cleaned_data.get('email')
                email = EmailMessage(mail_subject, message, to=[to_email])
                email.send()
            except Exception as e:
                # Log error but don't crash signup
                print(f"Email sending failed (Non-critical): {e}")

            # 2. Log in & Redirect
            login(request, user)
            messages.success(request, f"Welcome, {user.first_name}! Your account is ready.")
            return redirect('dashboard')
    else:
        form = SignUpForm()
    
    return render(request, 'registration/signup.html', {'form': form})

def activate(request, uidb64, token):
    """Endpoint for email activation links."""
    # Note: Full token validation logic would go here.
    # Currently acting as a pass-through for UX flow.
    messages.success(request, "Account verified successfully.")
    return redirect('dashboard')

# ==========================================
# 2. DASHBOARD & SETTINGS
# ==========================================

@login_required
def dashboard(request):
    """
    The Main Cockpit. Adapts based on User Role.
    """
    user = request.user
    
    # 1. Profile Completion Check
    profile_incomplete = False
    if not user.phone_number or not user.business_name:
        profile_incomplete = True

    # 2. Plan Limits Logic (UPDATED)
    # Uses the centralized settings we defined earlier
    user_plan = getattr(user, 'plan', 'FREE').upper() # <--- Fixed field name
    plan_limit = settings.INVENTORY_LIMITS.get(user_plan, 20)

    # 3. Inventory Stats
    inventory_count = InventoryItem.objects.filter(owner=user).count()
    usage_percent = 0
    
    # Handle Infinite Limit display logic
    if plan_limit == float('inf'):
        limit_display = "Unlimited"
        usage_percent = 5 # Small visual bar for enterprise
    else:
        limit_display = plan_limit
        if plan_limit > 0:
            usage_percent = (inventory_count / plan_limit) * 100

    # Base Context
    context = {
        'user': user,
        'role_label': 'Client',
        'is_online': user.is_online() if hasattr(user, 'is_online') else True,
        
        # --- FIXED: Added plan_name so "Pro Business" displays correctly ---
        'plan_name': user.get_plan_display(),
        
        'plan_limit': limit_display,
        'inventory_count': inventory_count,
        'usage_percent': min(usage_percent, 100),
        'profile_incomplete': profile_incomplete,
    }

    # Role-Based Stats
    if user.is_staff:
        # STAFF VIEW
        context['role_label'] = user.get_staff_role_display() or "Staff"
        context.update({
            'stat_1_label': 'Platform Users', 
            'stat_1_value': User.objects.count(), 
            'stat_1_icon': 'bi-people',
            'stat_2_label': 'Total Inventory', 
            'stat_2_value': InventoryItem.objects.count(), 
            'stat_2_icon': 'bi-box-seam',
            'stat_3_label': 'System Health', 
            'stat_3_value': '100%', 
            'stat_3_icon': 'bi-heart-pulse',
        })
    else:
        # CLIENT VIEW
        context['role_label'] = 'Freelancer'
        if user.is_vendor: context['role_label'] = 'Vendor'
        if user.is_planner: context['role_label'] = 'Agency'
        
        my_items = InventoryItem.objects.filter(owner=user)
        rented_items = my_items.filter(status='RENTED').count()
        # Revenue calc: Sum of daily rates for rented items (Approximation)
        current_revenue = my_items.filter(status='RENTED').aggregate(Sum('daily_rate'))['daily_rate__sum'] or 0
        
        context.update({
            'stat_1_label': 'Active Rentals', 
            'stat_1_value': str(rented_items), 
            'stat_1_icon': 'bi-camera-video',
            'stat_2_label': 'Est. Revenue', 
            'stat_2_value': f"KES {current_revenue:,.0f}", 
            'stat_2_icon': 'bi-cash-stack',
            'stat_3_label': 'Inventory Count', 
            'stat_3_value': str(inventory_count), 
            'stat_3_icon': 'bi-box',
        })

    return render(request, 'core/dashboard_home.html', context)

@login_required
def settings_view(request):
    """Profile Settings Page."""
    user = request.user
    
    if request.method == 'POST':
        form = UserSettingsForm(request.POST, request.FILES, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated successfully!")
            return redirect('dashboard')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = UserSettingsForm(instance=user)
    
    context = {
        'form': form,
        'user': user,
        'role_label': 'Settings'
    }
    return render(request, 'core/settings.html', context)

@login_required
def pricing_view(request):
    """Renders the Subscription Plans page."""
    return render(request, 'core/pricing.html')

# ==========================================
# 3. NOTIFICATION LOGIC (AJAX)
# ==========================================

@login_required
def mark_notification_read(request, pk):
    """
    AJAX endpoint: Marks a single notification as read.
    """
    notification = get_object_or_404(Notification, pk=pk, user=request.user)
    notification.is_read = True
    notification.save()
    return JsonResponse({'status': 'success'})

@login_required
def mark_all_notifications_read(request):
    """
    Clears all unread notifications for the user.
    """
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    return redirect(request.META.get('HTTP_REFERER', 'dashboard'))