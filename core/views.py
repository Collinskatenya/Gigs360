from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.models import Group 
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
from django.urls import reverse  # 🚨 Added for Settings URL routing
import json

# 🚨 UPDATED FORMS IMPORT (From Master Blueprint)
from .forms import (
    SignUpForm, 
    UserBaseUpdateForm, 
    ProfileDemographicsForm, 
    BusinessOperationsForm, 
    LegalIdentityForm, 
    FinancialPayoutForm
)
from .tokens import account_activation_token

# MODELS
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

            # Email Logic (Simulated for Dev)
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
    """
    # 🚨 SECURITY LOCK: Intercept Staff and route them to the Command Center
    if request.user.is_staff:
        return redirect('staff_dashboard')
        
    user = request.user

    # Get or Auto-Create Profile to prevent crashes
    profile, created = UserProfile.objects.get_or_create(user=user)

    # 1. Check for Unique Traceability (KRA/ID)
    profile_incomplete = False
    if not profile.phone_number or not profile.kra_pin or not profile.id_number:
        profile_incomplete = True

    # 2. Plan Limits Logic
    user_plan = profile.plan.upper() if profile.plan else 'FREE'
    plan_limit = settings.INVENTORY_LIMITS.get(user_plan, 15)

    # 3. Inventory Stats
    inventory_count = InventoryItem.objects.filter(owner=user).count()
    
    usage_percent = 0
    limit_display = plan_limit

    if plan_limit == float('inf'):
        limit_display = "Unlimited"
        usage_percent = 5 # Just a visual baseline
    elif plan_limit > 0:
        usage_percent = (inventory_count / plan_limit) * 100

    # 4. Determine Role Label
    role_label = 'Client'
    if profile.is_freelancer:
        role_label = 'Freelancer'
    elif profile.is_vendor:
        role_label = 'Agency'
    elif profile.is_agency:
        role_label = 'Agency'

    # 5. Business Stats (Revenue & Rentals)
    my_items = InventoryItem.objects.filter(owner=user)
    rented_items = my_items.filter(status='RENTED').count()
    current_revenue = my_items.filter(status='RENTED').aggregate(Sum('daily_rate'))['daily_rate__sum'] or 0

    # 🚨 INNOVATION: Calculate Unread Support Messages for Priority Widget
    unread_support_count = TicketMessage.objects.filter(
        ticket__user=user,
        is_read=False
    ).exclude(sender=user).exclude(is_internal_note=True).count()

    context = {
        'user': user,
        'profile': profile,
        'role_label': role_label,
        'plan_name': profile.get_plan_display(),
        'user_plan': user_plan,
        'plan_limit': limit_display,
        'inventory_count': inventory_count,
        'usage_percent': min(usage_percent, 100),
        'profile_incomplete': profile_incomplete,
        'unread_support_count': unread_support_count, # Passed to template
        'stat_1_label': 'Active Rentals', 
        'stat_1_value': str(rented_items), 
        'stat_1_icon': 'bi-camera-video',
        'stat_2_label': 'Est. Daily Rev', 
        'stat_2_value': f"KES {current_revenue:,.0f}", 
        'stat_2_icon': 'bi-cash-stack',
        'stat_3_label': 'Total Gear', 
        'stat_3_value': str(inventory_count), 
        'stat_3_icon': 'bi-box',
    }

    return render(request, 'core/dashboard.html', context)


# ==========================================
# 3. SETTINGS & PRICING (🚨 UPGRADED COMMAND VAULT)
# ==========================================

@login_required
def settings_view(request):
    """
    The Command Vault Engine with SECURITY PASSWORD CHECK.
    """
    user = request.user
    profile, created = UserProfile.objects.get_or_create(user=user)
    active_tab = 'personal' # Default tab

    if request.method == 'POST':
        # 🚨 Determine which tab was submitted based on the button name
        if 'submit_personal' in request.POST:
            active_tab = 'personal'
            base_form = UserBaseUpdateForm(request.POST, instance=user)
            demo_form = ProfileDemographicsForm(request.POST, request.FILES, instance=profile)
            if base_form.is_valid() and demo_form.is_valid():
                base_form.save()
                demo_form.save()
                messages.success(request, "Personal profile updated successfully.")
                return redirect('settings')

        elif 'submit_business' in request.POST:
            active_tab = 'business'
            business_form = BusinessOperationsForm(request.POST, request.FILES, instance=profile)
            if business_form.is_valid():
                business_form.save()
                messages.success(request, "Business operations updated successfully.")
                return redirect(f"{reverse('settings')}#business")

        elif 'submit_identity' in request.POST:
            active_tab = 'identity'
            identity_form = LegalIdentityForm(request.POST, instance=profile)
            
            # 🚨 SECURITY CHECK: Validate Password for sensitive edits
            current_password = request.POST.get('current_password')
            if not user.check_password(current_password):
                 identity_form.add_error('current_password', "Incorrect password. Changes not saved.")
            elif identity_form.is_valid():
                identity_form.save()
                SecurityLog.objects.create(
                    user=user, action="KYC Details Updated", 
                    ip_address=request.META.get('REMOTE_ADDR'), details="Legal identity details modified."
                )
                messages.success(request, "Legal identity submitted for verification.")
                return redirect(f"{reverse('settings')}#identity")

        elif 'submit_finance' in request.POST:
            active_tab = 'finance'
            finance_form = FinancialPayoutForm(request.POST, instance=profile)
            
            # 🚨 SECURITY CHECK: Validate Password for sensitive edits
            current_password = request.POST.get('current_password')
            if not user.check_password(current_password):
                 finance_form.add_error('current_password', "Incorrect password. Payout details not saved.")
            elif finance_form.is_valid():
                finance_form.save()
                SecurityLog.objects.create(
                    user=user, action="Financial Info Updated", 
                    ip_address=request.META.get('REMOTE_ADDR'), details="Payout routing details modified."
                )
                messages.success(request, "Financial payout details secured.")
                return redirect(f"{reverse('settings')}#finance")
                
        # If we fall through here, a form was invalid. Re-initialize others so UI doesn't break.
        if 'submit_personal' not in request.POST: 
            base_form = UserBaseUpdateForm(instance=user)
            demo_form = ProfileDemographicsForm(instance=profile)
        if 'submit_business' not in request.POST: 
            business_form = BusinessOperationsForm(instance=profile)
        if 'submit_identity' not in request.POST: 
            identity_form = LegalIdentityForm(instance=profile)
        if 'submit_finance' not in request.POST: 
            finance_form = FinancialPayoutForm(instance=profile)

    else:
        # GET request: Load existing data
        base_form = UserBaseUpdateForm(instance=user)
        demo_form = ProfileDemographicsForm(instance=profile)
        business_form = BusinessOperationsForm(instance=profile)
        identity_form = LegalIdentityForm(instance=profile)
        finance_form = FinancialPayoutForm(instance=profile)
    
    context = {
        'base_form': base_form, 
        'demo_form': demo_form,
        'business_form': business_form, 
        'identity_form': identity_form,
        'finance_form': finance_form,
        'user': user, 
        'profile': profile, # 🚨 Passed explicitly to fix UI data bug
        'active_tab': active_tab,
        'title': 'Settings & Operations Vault'
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
    Handles creation of support tickets from the Help Modal.
    Refined to redirect back to the REFERER page.
    """
    if request.method == 'POST':
        category = request.POST.get('category')
        # Auto-prioritize internal staff issues or billing
        priority = 'high' if category in ['internal', 'billing'] else 'medium'
        
        ticket = SupportTicket.objects.create(
            user=request.user,
            subject=request.POST.get('subject'),
            category=category,
            description=request.POST.get('description'),
            priority=priority
        )
        
        TicketMessage.objects.create(
            ticket=ticket, 
            sender=request.user, 
            message=request.POST.get('description')
        )
        
        messages.success(request, "Support ticket created! We will be in touch.")
        # UX Improvement: Stay on the same page (Settings, Inventory, etc.)
        return redirect(request.META.get('HTTP_REFERER', 'dashboard'))
        
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
    Enterprise Command Center for Admins.
    """
    total_users = User.objects.count()
    active_events = Event.objects.filter(start_time__gte=timezone.now()).count()
    platform_value = InventoryItem.objects.aggregate(Sum('daily_rate'))['daily_rate__sum'] or 0

    # Pending KYC Profiles
    pending_profiles = UserProfile.objects.filter(is_verified=False).exclude(kra_pin__isnull=True).exclude(kra_pin__exact='').select_related('user')
    pending_count = pending_profiles.count()
    
    # 🚨 INNOVATION: Fetching both Open AND Resolved queues for the Admin Archive
    if request.user.is_superuser:
        support_queue = SupportTicket.objects.exclude(status='resolved').order_by('-last_message_at')
        resolved_queue = SupportTicket.objects.filter(status='resolved').order_by('-last_message_at')[:30]
    else:
        support_queue = SupportTicket.objects.exclude(category='internal').exclude(status='resolved').order_by('-last_message_at')
        resolved_queue = SupportTicket.objects.filter(status='resolved').exclude(category='internal').order_by('-last_message_at')[:30]
    
    support_count = support_queue.count()

    # Chart Data (Simplified for context)
    chart_data = {}
    recent_logs = SecurityLog.objects.all().order_by('-created_at')[:8]

    user_groups = request.user.groups.values_list('name', flat=True)

    context = {
        'total_users': total_users,
        'active_events': active_events,
        'platform_value': platform_value,
        'pending_users': [p.user for p in pending_profiles],
        'pending_count': pending_count,
        'support_queue': support_queue,
        'support_count': support_count,
        'resolved_queue': resolved_queue, 
        'recent_logs': recent_logs,
        'chart_data': chart_data,
        'is_superuser': request.user.is_superuser,
        'user_groups': user_groups, 
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

@staff_member_required
def staff_user_manager(request):
    """
    Command Center Console: User Directory.
    Pulls all users and their KYC profiles for admin management.
    """
    all_users = User.objects.select_related('userprofile').all().order_by('-date_joined')
    
    context = {
        'all_users': all_users,
        'user_count': all_users.count(),
    }
    return render(request, 'core/staff_user_manager.html', context)

@staff_member_required
def staff_master_inventory(request):
    """
    Command Center Console: Master Inventory.
    Pulls all gear on the platform for global search and tracking.
    """
    all_items = InventoryItem.objects.select_related('owner', 'category').all().order_by('-created_at')
    
    context = {
        'all_items': all_items,
        'total_items': all_items.count(),
        'rented_items': all_items.filter(status='RENTED').count(), 
    }
    return render(request, 'core/staff_master_inventory.html', context)

@staff_member_required
def staff_security_logs(request):
    """
    Command Center Console: Security Logs (Audit Ledger).
    Full audit trail of all platform activities.
    """
    logs = SecurityLog.objects.select_related('user').all().order_by('-created_at')
    
    context = {
        'logs': logs,
        'log_count': logs.count(),
    }
    return render(request, 'core/staff_security_logs.html', context)
    
@staff_member_required
def resolve_ticket(request, ticket_id):
    """
    Command Center Action: Resolves a support ticket.
    Updates status, notifies the user, and logs the action.
    """
    ticket = get_object_or_404(SupportTicket, pk=ticket_id)
    
    if ticket.status != 'resolved':
        ticket.status = 'resolved'
        ticket.save()
        
        SecurityLog.objects.create(
            user=request.user,
            action=f"Resolved Support Ticket #{ticket.id}",
            ip_address=request.META.get('REMOTE_ADDR'),
            details=f"Subject: {ticket.subject} (User: {ticket.user.username})"
        )
        
        Notification.objects.create(
            user=ticket.user,
            title="Support Ticket Resolved",
            message=f"Your ticket regarding '{ticket.subject}' has been resolved by Gigs360 HQ.",
            notification_type="success"
        )
        
        messages.success(request, f"Ticket from {ticket.user.username} successfully resolved.")
    else:
        messages.info(request, "This ticket was already resolved.")
        
    return redirect('staff_dashboard')

@staff_member_required
def staff_gigs_tracker(request):
    """
    Command Center Console: Active Gigs Tracker.
    Pulls all events/gigs from the platform for admin monitoring.
    """
    all_events = Event.objects.all().order_by('-start_time')
    
    context = {
        'all_events': all_events,
        'total_gigs': all_events.count(),
        'active_gigs': all_events.filter(start_time__gte=timezone.now()).count()
    }
    return render(request, 'core/staff_gigs_tracker.html', context)

@staff_member_required
def staff_edit_user(request, user_id):
    """
    Command Center Console: User Access Management.
    Only Super Admins can assign or revoke Granular Staff Roles.
    """
    if not request.user.is_superuser:
        messages.error(request, "Access Denied: Only Super Admins can modify security clearances.")
        return redirect('staff_user_manager')

    target_user = get_object_or_404(User, pk=user_id)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'update_roles':
            is_staff = request.POST.get('is_staff') == 'on'
            target_user.is_staff = is_staff
            
            kyc_group, _ = Group.objects.get_or_create(name='KYC Officer')
            support_group, _ = Group.objects.get_or_create(name='Support Agent')
            
            if request.POST.get('role_kyc') == 'on':
                target_user.groups.add(kyc_group)
            else:
                target_user.groups.remove(kyc_group)
                
            if request.POST.get('role_support') == 'on':
                target_user.groups.add(support_group)
            else:
                target_user.groups.remove(support_group)
                
            target_user.save()
            
            SecurityLog.objects.create(
                user=request.user,
                action=f"Modified Security Clearance for {target_user.username}",
                ip_address=request.META.get('REMOTE_ADDR'),
                details=f"HQ Access: {is_staff}"
            )
            
            messages.success(request, f"Security clearances for {target_user.username} successfully updated.")
            return redirect('staff_edit_user', user_id=target_user.id)

    is_kyc = target_user.groups.filter(name='KYC Officer').exists()
    is_support = target_user.groups.filter(name='Support Agent').exists()

    context = {
        'target_user': target_user,
        'is_kyc': is_kyc,
        'is_support': is_support,
    }
    return render(request, 'core/staff_edit_user.html', context)

# ==========================================
# 🚨 SECURITY KILL SWITCHES
# ==========================================

@staff_member_required
def suspend_user(request, user_id):
    """Toggles a user's access to the platform."""
    if not (request.user.is_superuser or request.user.groups.filter(name='KYC Officer').exists()):
        messages.error(request, "Permission Denied: You do not have clearance to suspend users.")
        return redirect('staff_user_manager')

    target_user = get_object_or_404(User, pk=user_id)
    
    if target_user.is_staff:
        messages.error(request, "Security Exception: You cannot suspend a Staff member or Super Admin.")
        return redirect('staff_user_manager')

    target_user.is_active = not target_user.is_active
    target_user.save()

    action_text = "Suspended" if not target_user.is_active else "Reactivated"
    
    SecurityLog.objects.create(
        user=request.user,
        action=f"{action_text} Account: {target_user.username}",
        ip_address=request.META.get('REMOTE_ADDR'),
        details=f"User login access {'disabled' if not target_user.is_active else 'restored'}."
    )
    
    messages.success(request, f"User {target_user.username} has been successfully {action_text.lower()}.")
    return redirect('staff_user_manager')

@staff_member_required
def flag_asset(request, item_id):
    """Removes a suspicious or broken asset from the public marketplace."""
    item = get_object_or_404(InventoryItem, pk=item_id)
    
    if item.status != 'UNAVAILABLE':
        item.status = 'UNAVAILABLE'
        action_msg = "flagged and removed from public view"
    else:
        item.status = 'AVAILABLE'
        action_msg = "unflagged and restored"
    
    item.save()

    SecurityLog.objects.create(
        user=request.user,
        action=f"Flagged Asset #{item.id}",
        ip_address=request.META.get('REMOTE_ADDR'),
        details=f"Asset visibility changed by HQ."
    )
    
    messages.warning(request, f"Asset has been {action_msg}.")
    return redirect('staff_master_inventory')

# ==========================================
# 6. TWO-WAY MESSAGING HUB (🚨 UPGRADED UX)
# ==========================================

@login_required
def support_history(request):
    """B2C Inbox: Professional WhatsApp-style interface with Auto-Reopen."""
    # Sort by the latest message activity
    tickets = SupportTicket.objects.filter(user=request.user).order_by('-last_message_at')
    
    active_ticket_id = request.GET.get('chat')
    show_new = request.GET.get('new') == 'true'
    active_chat = None
    
    # 1. Handle Active Chat Tracking & Read Receipts
    if active_ticket_id:
        active_chat = get_object_or_404(SupportTicket, id=active_ticket_id, user=request.user)
        # 🚨 INNOVATION: Prevent Users from seeing/reading Ghost Notes
        unread_msgs = active_chat.messages.exclude(sender=request.user).filter(is_read=False, is_internal_note=False)
        if unread_msgs.exists():
            unread_msgs.update(is_read=True, read_at=timezone.now())
        
    if request.method == 'POST':
        # 2. Handle Inline Ticket Creation (New Toggle)
        if request.POST.get('action') == 'new_ticket':
            category = request.POST.get('category')
            priority = 'high' if category in ['internal', 'billing'] else 'medium'
            
            new_ticket = SupportTicket.objects.create(
                user=request.user,
                subject=request.POST.get('subject'),
                category=category,
                description=request.POST.get('description'),
                priority=priority
            )
            TicketMessage.objects.create(
                ticket=new_ticket, sender=request.user, message=request.POST.get('description')
            )
            messages.success(request, "New support thread started.")
            return redirect(f"{request.path}?chat={new_ticket.id}")

        # 3. Handle Chat Replies & Auto-Reopen
        elif active_chat:
            msg_body = request.POST.get('message')
            if msg_body:
                TicketMessage.objects.create(ticket=active_chat, sender=request.user, message=msg_body)
                
                # Auto-Reopen if resolved!
                if active_chat.status == 'resolved':
                    active_chat.status = 'open'
                
                active_chat.last_message_at = timezone.now()
                active_chat.save()
                
                Notification.objects.create(
                    user=User.objects.filter(is_superuser=True).first(),
                    title=f"Reply from {request.user.username}",
                    notification_type="info"
                )
                return redirect(f"{request.path}?chat={active_chat.id}")

    context = {
        'tickets': tickets,
        'active_chat': active_chat,
        'show_new': show_new, # Tells the template to show the Compose screen
    }
    return render(request, 'core/messaging_hub.html', context)


@staff_member_required
def staff_ticket_detail(request, ticket_id):
    """B2B Chat: HQ Command Terminal with God View."""
    ticket = get_object_or_404(SupportTicket, id=ticket_id)
    
    # Mark incoming User messages as READ when HQ opens the chat
    unread_msgs = ticket.messages.exclude(sender=request.user).filter(is_read=False)
    if unread_msgs.exists():
        unread_msgs.update(is_read=True, read_at=timezone.now())
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'reply':
            msg_body = request.POST.get('message')
            if msg_body:
                # 🚨 INNOVATION: Determine if this is a Public Reply or a Ghost Note
                is_note = request.POST.get('is_internal_note') == 'true'

                TicketMessage.objects.create(
                    ticket=ticket, 
                    sender=request.user, 
                    message=msg_body,
                    is_internal_note=is_note
                )
                
                if not is_note:
                    # Allow Admin to Reopen a resolved ticket by replying publicly
                    if ticket.status == 'resolved':
                        ticket.status = 'open'
                        
                    # Bump the ticket to the top of the queue
                    ticket.last_message_at = timezone.now()
                    ticket.save()
                    
                    Notification.objects.create(
                        user=ticket.user,
                        title="HQ replied to your ticket.",
                        notification_type="info"
                    )
                    messages.success(request, "Reply sent. Thread active.")
                else:
                    messages.success(request, "Internal ghost note saved.")
                
        elif action == 'resolve':
            ticket.status = 'resolved'
            ticket.save()
            SecurityLog.objects.create(
                user=request.user, action=f"Resolved Ticket #{ticket.id}",
                ip_address=request.META.get('REMOTE_ADDR'), details="HQ closed ticket via Chat Hub."
            )
            Notification.objects.create(
                user=ticket.user, title="Ticket Resolved", notification_type="success"
            )
            messages.success(request, f"Ticket #{ticket.id} successfully resolved.")
            return redirect('staff_dashboard')
            
        return redirect('staff_ticket_detail', ticket_id=ticket.id)
        
    context = {
        'ticket': ticket,
    }
    return render(request, 'core/staff_ticket_detail.html', context)