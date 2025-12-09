from django.shortcuts import render, redirect
from django.contrib.auth import login, get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum  # <--- VERIFIED: Import is present

# Email dependencies
from django.contrib.sites.shortcuts import get_current_site
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.template.loader import render_to_string
from django.core.mail import EmailMessage

from .forms import SignUpForm, UserSettingsForm
from .tokens import account_activation_token

# Import models from other apps
from inventory.models import InventoryItem

User = get_user_model()

def home(request):
    """Renders the Landing Page."""
    return render(request, 'core/index.html')

def signup(request):
    """
    Handles User Registration.
    """
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.is_active = True 
            user.save()

            # 1. Send Verification Email
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
            return redirect('dashboard')
    else:
        form = SignUpForm()
    
    return render(request, 'registration/signup.html', {'form': form})

def activate(request, uidb64, token):
    return redirect('dashboard')

@login_required
def dashboard(request):
    """
    The Main Cockpit.
    """
    user = request.user
    
    # 1. CHECK SUBSCRIPTION
    if not user.is_superuser and not user.is_subscription_active():
        messages.error(request, "Your subscription has expired. Please renew.")
        return redirect('pricing') 

    # 2. CHECK IF ROLE IS SELECTED
    if not user.is_superuser and not (user.is_vendor or user.is_planner or user.is_client):
        messages.info(request, "Welcome! Please complete your profile.")
        return redirect('settings')

    # 3. PROFILE COMPLETION CHECK (VERIFIED: Logic is present)
    profile_incomplete = False
    if not user.phone_number or not user.business_name:
        profile_incomplete = True

    # 4. LIMIT CALCULATIONS
    plan_limit = 5 
    if user.subscription_plan == 'Pro':
        plan_limit = 50
    elif user.subscription_plan == 'Enterprise':
        plan_limit = 1000000 

    # Global Inventory Stats
    inventory_count = InventoryItem.objects.filter(owner=user).count()
    usage_percent = 0
    if plan_limit > 0:
        usage_percent = (inventory_count / plan_limit) * 100

    # Base Context
    context = {
        'user': user,
        'role_label': 'User',
        'is_online': user.is_online(),
        'plan_limit': plan_limit if plan_limit < 1000000 else 'Unlimited',
        'inventory_count': inventory_count,
        'usage_percent': min(usage_percent, 100),
        'profile_incomplete': profile_incomplete, # Needed for the yellow alert
    }

    # ==========================================
    # ROLE-BASED STATS
    # ==========================================
    
    # VENDOR
    if user.is_vendor:
        context['role_label'] = 'Vendor'
        my_items = InventoryItem.objects.filter(owner=user)
        rented_items = my_items.filter(status='RENTED').count()
        issues_items = my_items.filter(status__in=['LOST', 'MAINTENANCE']).count()
        
        # Calculate Revenue (VERIFIED: Works because Sum is imported)
        current_revenue = my_items.filter(status='RENTED').aggregate(Sum('daily_rate'))['daily_rate__sum'] or 0
        
        context.update({
            'stat_1_label': 'Active Rentals', 'stat_1_value': f"{rented_items}", 'stat_1_icon': 'bi-camera-video',
            'stat_2_label': 'Current Revenue', 'stat_2_value': f"KES {current_revenue:,.0f}", 'stat_2_icon': 'bi-cash-stack',
            'stat_3_label': 'Issues', 'stat_3_value': f"{issues_items}", 'stat_3_icon': 'bi-exclamation-triangle',
        })

    # AGENCY
    elif user.is_planner:
        context['role_label'] = 'Agency'
        context.update({
            'stat_1_label': 'Active Events', 'stat_1_value': '0', 'stat_1_icon': 'bi-calendar-check',
            'stat_2_label': 'Talent Hired', 'stat_2_value': '0', 'stat_2_icon': 'bi-people',
            'stat_3_label': 'Budget Spent', 'stat_3_value': 'KES 0.00', 'stat_3_icon': 'bi-pie-chart',
        })

    # FREELANCER
    else:
        context['role_label'] = 'Freelancer'
        context.update({
            'stat_1_label': 'My Gigs', 'stat_1_value': '0', 'stat_1_icon': 'bi-briefcase',
            'stat_2_label': 'Earnings', 'stat_2_value': 'KES 0.00', 'stat_2_icon': 'bi-cash',
            'stat_3_label': 'Profile Views', 'stat_3_value': '0', 'stat_3_icon': 'bi-eye',
        })

    return render(request, 'core/dashboard_home.html', context)

@login_required
def settings_view(request):
    """
    Settings Page.
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