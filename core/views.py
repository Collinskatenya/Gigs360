from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.db.models import Sum, Count
from django.http import JsonResponse
from django.conf import settings 
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django.contrib.sites.shortcuts import get_current_site
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.utils import timezone
import json

# FORMS
from .forms import SignUpForm, UserUpdateForm, UserProfileForm
from .tokens import account_activation_token

# MODELS
# Ensure you have migrated these changes if you just added SupportTicket/TicketMessage
from .models import Notification, SecurityLog, UserProfile, SupportTicket, TicketMessage
from inventory.models import InventoryItem
from events.models import Event

User = get_user_model()

# ==========================================
# 1. PUBLIC PAGES & AUTH
# ==========================================

def home(request):
    """Renders the Landing Page."""
    return render(request, 'core/index.html')

def signup(request):
    """Handles User Registration."""
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.is_active = True 
            user.save()

            # Email Logic (Simulated for Dev, configure SMTP for Prod)
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
                print(f"Email sending failed: {e}")

            login(request, user)
            messages.success(request, f"Welcome, {user.username}! Complete your profile to get started.")
            return redirect('dashboard')
    else:
        form = SignUpForm()
    
    return render(request, 'registration/signup.html', {'form': form})

def activate(request, uidb64, token):
    messages.success(request, "Account verified successfully.")
    return redirect('dashboard')


# ==========================================
# 2. DASHBOARD (The Traffic Controller)
# ==========================================

@login_required
def dashboard(request):
    """
    The Main Cockpit. 
    Users AND Staff land here by default.
    """
    user = request.user

    try:
        profile = user.userprofile
    except UserProfile.DoesNotExist:
        profile = None

    # Profile Completion Check
    profile_incomplete = False
    if profile and (not profile.phone_number or not profile.kra_pin):
        profile_incomplete = True

    # Plan Limits
    if profile:
        user_plan = profile.plan_tier.upper() # Use correct field name 'plan_tier'
    else:
        user_plan = 'FREE'
        
    plan_limit = settings.INVENTORY_LIMITS.get(user_plan, 15)

    # Stats
    inventory_count = InventoryItem.objects.filter(owner=user).count()
    usage_percent = 0
    
    if plan_limit == float('inf'):
        limit_display = "Unlimited"
        usage_percent = 5 
    else:
        limit_display = plan_limit
        if plan_limit > 0:
            usage_percent = (inventory_count / plan_limit) * 100

    context = {
        'user': user,
        'profile': profile,
        'role_label': 'Client',
        'plan_name': profile.get_plan_tier_display() if profile else "Free Starter",
        'user_plan': user_plan,
        'plan_limit': limit_display,
        'inventory_count': inventory_count,
        'usage_percent': min(usage_percent, 100),
        'profile_incomplete': profile_incomplete,
    }

    if profile:
        if profile.role == 'FREELANCER': context['role_label'] = 'Freelancer'
        if profile.role == 'VENDOR': context['role_label'] = 'Vendor'
        if profile.role == 'AGENCY': context['role_label'] = 'Agency'
    
    # Calculate Business Stats
    my_items = InventoryItem.objects.filter(owner=user)
    rented_items = my_items.filter(status='RENTED').count()
    # Assuming 'daily_rate' is a decimal field
    current_revenue = my_items.filter(status='RENTED').aggregate(Sum('daily_rate'))['daily_rate__sum'] or 0
    
    context.update({
        'stat_1_label': 'Active Rentals', 
        'stat_1_value': str(rented_items), 
        'stat_1_icon': 'bi-camera-video',
        'stat_2_label': 'Est. Daily Rev', 
        'stat_2_value': f"KES {current_revenue:,.0f}", 
        'stat_2_icon': 'bi-cash-stack',
        'stat_3_label': 'Gear Count', 
        'stat_3_value': str(inventory_count), 
        'stat_3_icon': 'bi-box',
    })

    # FIX: Renamed from dashboard_home.html to dashboard.html
    return render(request, 'core/dashboard.html', context)


# ==========================================
# 3. SETTINGS & PRICING
# ==========================================

@login_required
def settings_view(request):
    if request.method == 'POST':
        u_form = UserUpdateForm(request.POST, instance=request.user)
        profile = getattr(request.user, 'userprofile', None)
        p_form = UserProfileForm(request.POST, request.FILES, instance=profile)

        if u_form.is_valid() and p_form.is_valid():
            u_form.save()
            p_form.save()
            messages.success(request, "Business Profile Updated Successfully!")
            return redirect('dashboard') # Redirect to dashboard to see changes
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        u_form = UserUpdateForm(instance=request.user)
        profile = getattr(request.user, 'userprofile', None)
        p_form = UserProfileForm(instance=profile)
    
    context = {
        'u_form': u_form,
        'p_form': p_form,
        'user': request.user,
        'title': 'Business Settings'
    }
    return render(request, 'core/settings.html', context)

@login_required
def pricing_view(request):
    return render(request, 'core/pricing.html')


# ==========================================
# 4. NOTIFICATIONS & HELPDESK
# ==========================================

@login_required
def create_ticket(request):
    """
    Handles creation of support tickets from the user dashboard.
    """
    if request.method == 'POST':
        category = request.POST.get('category')
        priority = 'high' if category == 'internal' else 'medium'
        
        ticket = SupportTicket.objects.create(
            user=request.user,
            subject=request.POST.get('subject'),
            category=category,
            description=request.POST.get('description'),
            priority=priority
        )
        
        # Create initial message
        TicketMessage.objects.create(
            ticket=ticket, 
            sender=request.user, 
            message=request.POST.get('description')
        )
        
        messages.success(request, "Support ticket created successfully!")
        return redirect('dashboard')
        
    return redirect('dashboard')

@login_required
def mark_notification_read(request, pk):
    notification = get_object_or_404(Notification, pk=pk, user=request.user)
    notification.is_read = True
    notification.save()
    return JsonResponse({'status': 'success'})

@login_required
def mark_all_notifications_read(request):
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    return redirect(request.META.get('HTTP_REFERER', 'dashboard'))


# ==========================================
# 5. STAFF COMMAND CENTER (Enterprise)
# ==========================================

@staff_member_required
def staff_dashboard(request):
    """
    Enterprise Command Center.
    """
    # 1. KPIs
    total_users = User.objects.count()
    
    # FIX: Changed 'end_date' to 'start_time' to match Event model
    active_events = Event.objects.filter(start_time__gte=timezone.now()).count()
    
    platform_value = InventoryItem.objects.aggregate(Sum('daily_rate'))['daily_rate__sum'] or 0

    # 2. QUEUES
    # Verification Queue
    pending_profiles = UserProfile.objects.filter(is_verified=False).exclude(kra_pin__isnull=True).select_related('user')
    pending_count = pending_profiles.count()
    
    # Support Ticket Queue
    if request.user.is_superuser:
        support_queue = SupportTicket.objects.exclude(status='resolved').order_by('-created_at')
    else:
        # Staff only see user tickets, not internal super-admin issues
        support_queue = SupportTicket.objects.exclude(category='internal').exclude(status='resolved')
    
    support_count = support_queue.count()

    # 3. CHART DATA (Superuser Only)
    chart_data = {}
    if request.user.is_superuser:
        cat_data = InventoryItem.objects.values('category').annotate(count=Count('id'))
        chart_data['inventory_pie'] = json.dumps({
            'labels': [c['category'].replace('_', ' ').title() for c in cat_data],
            'data': [c['count'] for c in cat_data]
        })
        chart_data['growth'] = json.dumps({
            'labels': ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'],
            'data': [10, 25, 45, 80, 120, total_users]
        })

    # 4. RECENT LOGS
    recent_logs = SecurityLog.objects.all().order_by('-created_at')[:8]

    context = {
        'total_users': total_users,
        'active_events': active_events,
        'platform_value': platform_value,
        'pending_users': [p.user for p in pending_profiles],
        'pending_count': pending_count,
        'support_queue': support_queue,
        'support_count': support_count,
        'recent_logs': recent_logs,
        'chart_data': chart_data,
        'is_superuser': request.user.is_superuser,
    }
    return render(request, 'core/staff_dashboard.html', context)

@staff_member_required
def verify_user(request, user_id):
    """Approves a user's KYC details."""
    user_to_verify = get_object_or_404(User, pk=user_id)
    
    try:
        profile = user_to_verify.userprofile
        profile.is_verified = True
        profile.save()
        
        SecurityLog.objects.create(
            user=request.user,
            action=f"Verified User: {user_to_verify.username}",
            ip_address=request.META.get('REMOTE_ADDR'),
            details="KYC Approved via Dashboard"
        )
        
        Notification.objects.create(
            user=user_to_verify,
            title="Account Verified!",
            message="Your KYC documents have been approved. You can now generate invoices.",
            notification_type="success"
        )
        messages.success(request, f"{user_to_verify.username} has been verified.")
        
    except UserProfile.DoesNotExist:
        messages.error(request, "User has no profile to verify.")
        
    return redirect('staff_dashboard')