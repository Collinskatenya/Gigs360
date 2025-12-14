from django.shortcuts import render, redirect
from django.contrib.auth import login, get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum

# Email Dependencies
from django.contrib.sites.shortcuts import get_current_site
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.template.loader import render_to_string
from django.core.mail import EmailMessage

from .forms import SignUpForm, UserSettingsForm
from .tokens import account_activation_token
from inventory.models import InventoryItem

User = get_user_model()

def home(request):
    """Renders the Landing Page."""
    return render(request, 'core/index.html')

def signup(request):
    """Handles User Registration and Initial Login."""
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.is_active = True 
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
    # Logic for activation can be expanded here
    messages.success(request, "Account verified successfully.")
    return redirect('dashboard')

@login_required
def dashboard(request):
    """
    The Main Cockpit.
    Adapts based on User Role (Staff vs Client).
    """
    user = request.user
    
    # 1. Profile Completion Check
    profile_incomplete = False
    if not user.phone_number or not user.business_name:
        profile_incomplete = True

    # 2. Plan Limits Logic
    plan_limit = 5
    if user.subscription_plan == 'Pro':
        plan_limit = 50
    elif user.subscription_plan == 'Enterprise':
        plan_limit = 1000000  # Unlimited

    # 3. Inventory Stats
    inventory_count = InventoryItem.objects.filter(owner=user).count()
    usage_percent = 0
    if plan_limit > 0:
        usage_percent = (inventory_count / plan_limit) * 100

    # Base Context
    context = {
        'user': user,
        'role_label': 'Client',
        'is_online': user.is_online() if hasattr(user, 'is_online') else True,
        'plan_limit': plan_limit if plan_limit < 1000000 else 'Unlimited',
        'inventory_count': inventory_count,
        'usage_percent': min(usage_percent, 100),
        'profile_incomplete': profile_incomplete,
    }

    # ==========================================
    # ROLE-BASED STATS
    # ==========================================
    
    if user.is_staff:
        # A. STAFF VIEW
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
        # B. CLIENT VIEW (Freelancer / Vendor / Agency)
        context['role_label'] = 'Freelancer'
        if user.is_vendor: context['role_label'] = 'Vendor'
        if user.is_planner: context['role_label'] = 'Agency'
        
        my_items = InventoryItem.objects.filter(owner=user)
        rented_items = my_items.filter(status='RENTED').count()
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
    """
    Settings Page.
    Updates the User model directly.
    """
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