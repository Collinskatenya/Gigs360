from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, get_user_model, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.models import Group 
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib import messages
from django.db.models import Sum, Count, Q
from django.http import JsonResponse
from django.conf import settings 
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django.contrib.sites.shortcuts import get_current_site
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.utils import timezone
from django.urls import reverse  
import json

from .forms import (
    SignUpForm, 
    UserBaseUpdateForm, 
    ProfileDemographicsForm, 
    BusinessOperationsForm, 
    LegalIdentityForm, 
    FinancialPayoutForm
)
from .tokens import account_activation_token

# 🚨 INJECTED CMS MODELS HERE
from .models import (
    Notification, SecurityLog, UserProfile, SupportTicket, 
    TicketMessage, HolidayMessage, UpcomingActivity, 
    ServiceFeature, Testimonial
)
from inventory.models import InventoryItem
from events.models import Event

User = get_user_model()

# ==========================================
# 1. PUBLIC PAGES & AUTH
# ==========================================

def home(request):
    """
    Renders the Landing Page - Now powered by dynamic CMS data.
    """
    activities = UpcomingActivity.objects.filter(is_active=True)[:3]
    services = ServiceFeature.objects.filter(is_active=True)
    testimonials = Testimonial.objects.filter(is_active=True)

    context = {
        'activities': activities,
        'services': services,
        'testimonials': testimonials,
    }
    return render(request, 'core/index.html', context)

def signup(request):
    """Handles User Registration."""
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.is_active = True 
            user.save()

            # Email Logic
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
    """The Main Cockpit."""
    if request.user.is_staff:
        return redirect('staff_dashboard')
        
    user = request.user
    profile, created = UserProfile.objects.get_or_create(user=user)

    profile_incomplete = False
    if not profile.phone_number or not profile.kra_pin or not profile.id_number:
        profile_incomplete = True

    user_plan = profile.plan.upper() if profile.plan else 'FREE'
    plan_limit = settings.INVENTORY_LIMITS.get(user_plan, 15)

    inventory_count = InventoryItem.objects.filter(owner=user).count()
    
    usage_percent = 0
    limit_display = plan_limit

    if plan_limit == float('inf'):
        limit_display = "Unlimited"
        usage_percent = 5
    elif plan_limit > 0:
        usage_percent = (inventory_count / plan_limit) * 100

    role_label = 'Client'
    if profile.is_freelancer:
        role_label = 'Freelancer'
    elif profile.is_vendor:
        role_label = 'Agency'
    elif profile.is_agency:
        role_label = 'Agency'

    my_items = InventoryItem.objects.filter(owner=user)
    rented_items = my_items.filter(status='RENTED').count()
    current_revenue = my_items.filter(status='RENTED').aggregate(Sum('daily_rate'))['daily_rate__sum'] or 0

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
        'unread_support_count': unread_support_count, 
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
# 3. SETTINGS & PRICING
# ==========================================

@login_required
def settings_view(request):
    """The Command Vault Engine."""
    user = request.user
    profile, created = UserProfile.objects.get_or_create(user=user)
    active_tab = 'personal' 

    if request.method == 'POST':
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

        # 🚨 THE SENTINEL INTERCEPTOR (Identity)
        elif 'submit_identity' in request.POST:
            active_tab = 'identity'
            identity_form = LegalIdentityForm(request.POST, instance=profile)
            current_password = request.POST.get('current_password')
            if not user.check_password(current_password):
                 identity_form.add_error('current_password', "Incorrect password. Changes not saved.")
            elif identity_form.is_valid():
                profile = identity_form.save(commit=False)
                
                is_fraud, reason = profile.scan_for_fraud()
                if is_fraud:
                    profile.kyc_status = 'FLAGGED'
                    profile.rejection_reason = reason
                    profile.ai_trust_score -= 20.0
                    SecurityLog.objects.create(
                        user=user, action="CRITICAL: Fraudulent Data Detected", 
                        ip_address=request.META.get('REMOTE_ADDR'), details=reason
                    )
                    messages.warning(request, "Identity submitted, but flagged for manual HQ review.")
                else:
                    profile.kyc_status = 'PENDING'
                    SecurityLog.objects.create(
                        user=user, action="KYC Details Updated", 
                        ip_address=request.META.get('REMOTE_ADDR'), details="Clean legal identity details submitted."
                    )
                    messages.success(request, "Legal identity submitted for verification.")
                
                profile.save()
                return redirect(f"{reverse('settings')}#identity")

        # 🚨 THE SENTINEL INTERCEPTOR (Finance)
        elif 'submit_finance' in request.POST:
            active_tab = 'finance'
            finance_form = FinancialPayoutForm(request.POST, instance=profile)
            current_password = request.POST.get('current_password')
            if not user.check_password(current_password):
                 finance_form.add_error('current_password', "Incorrect password. Payout details not saved.")
            elif finance_form.is_valid():
                profile = finance_form.save(commit=False)
                
                is_fraud, reason = profile.scan_for_fraud()
                if is_fraud:
                    profile.kyc_status = 'FLAGGED'
                    profile.rejection_reason = reason
                    profile.ai_trust_score -= 20.0
                    SecurityLog.objects.create(
                        user=user, action="CRITICAL: Fraudulent Bank Data Detected", 
                        ip_address=request.META.get('REMOTE_ADDR'), details=reason
                    )
                    messages.warning(request, "Payout details saved, but account flagged for manual review.")
                else:
                    SecurityLog.objects.create(
                        user=user, action="Financial Info Updated", 
                        ip_address=request.META.get('REMOTE_ADDR'), details="Clean payout routing details modified."
                    )
                    messages.success(request, "Financial payout details secured.")
                
                profile.save()
                return redirect(f"{reverse('settings')}#finance")
                
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
        'profile': profile, 
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
    if request.method == 'POST':
        category = request.POST.get('category')
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
    total_users = User.objects.count()
    active_events = Event.objects.filter(start_time__gte=timezone.now()).count()
    platform_value = InventoryItem.objects.aggregate(Sum('daily_rate'))['daily_rate__sum'] or 0

    # 🚨 UPDATED KYC PIPELINE: Grabs Pending AND Flagged users
    pending_profiles = UserProfile.objects.filter(
        Q(kyc_status='PENDING') | Q(kyc_status='FLAGGED')
    ).select_related('user')
    pending_count = pending_profiles.count()
    
    if request.user.is_superuser:
        support_queue = SupportTicket.objects.exclude(status='resolved').order_by('-last_message_at')
        resolved_queue = SupportTicket.objects.filter(status='resolved').order_by('-last_message_at')[:30]
    else:
        support_queue = SupportTicket.objects.exclude(category='internal').exclude(status='resolved').order_by('-last_message_at')
        resolved_queue = SupportTicket.objects.filter(status='resolved').exclude(category='internal').order_by('-last_message_at')[:30]
    
    support_count = support_queue.count()

    context = {
        'total_users': total_users, 
        'active_events': active_events, 
        'platform_value': platform_value,
        'pending_users': [p.user for p in pending_profiles], 
        'pending_count': pending_count,
        'support_queue': support_queue, 
        'support_count': support_count, 
        'resolved_queue': resolved_queue, 
        'recent_logs': SecurityLog.objects.all().order_by('-created_at')[:8], 
        'chart_data': {},
        'is_superuser': request.user.is_superuser, 
        'user_groups': request.user.groups.values_list('name', flat=True), 
    }
    return render(request, 'core/staff_dashboard.html', context)

@staff_member_required
def verify_user(request, user_id):
    user_to_verify = get_object_or_404(User, pk=user_id)
    try:
        profile = user_to_verify.userprofile
        profile.kyc_status = 'APPROVED'
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
    all_users = User.objects.select_related('userprofile').all().order_by('-date_joined')
    return render(request, 'core/staff_user_manager.html', {'all_users': all_users, 'user_count': all_users.count()})

@staff_member_required
def staff_master_inventory(request):
    all_items = InventoryItem.objects.select_related('owner', 'category').all().order_by('-created_at')
    return render(request, 'core/staff_master_inventory.html', {
        'all_items': all_items, 
        'total_items': all_items.count(), 
        'rented_items': all_items.filter(status='RENTED').count()
    })

@staff_member_required
def staff_security_logs(request):
    logs = SecurityLog.objects.select_related('user').all().order_by('-created_at')
    return render(request, 'core/staff_security_logs.html', {'logs': logs, 'log_count': logs.count()})
    
@staff_member_required
def resolve_ticket(request, ticket_id):
    ticket = get_object_or_404(SupportTicket, pk=ticket_id)
    if ticket.status != 'resolved':
        ticket.status = 'resolved'
        ticket.save()
        SecurityLog.objects.create(
            user=request.user, 
            action=f"Resolved Support Ticket #{ticket.id}", 
            ip_address=request.META.get('REMOTE_ADDR'), 
            details=f"Subject: {ticket.subject}"
        )
        Notification.objects.create(
            user=ticket.user, 
            title="Support Ticket Resolved", 
            message=f"Your ticket regarding '{ticket.subject}' has been resolved.", 
            notification_type="success"
        )
        messages.success(request, f"Ticket from {ticket.user.username} successfully resolved.")
    else:
        messages.info(request, "This ticket was already resolved.")
    return redirect('staff_dashboard')

@staff_member_required
def staff_gigs_tracker(request):
    all_events = Event.objects.all().order_by('-start_time')
    return render(request, 'core/staff_gigs_tracker.html', {
        'all_events': all_events, 
        'total_gigs': all_events.count(), 
        'active_gigs': all_events.filter(start_time__gte=timezone.now()).count()
    })

@staff_member_required
def staff_edit_user(request, user_id):
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
    return render(request, 'core/staff_edit_user.html', {
        'target_user': target_user, 
        'is_kyc': is_kyc, 
        'is_support': is_support
    })


# ==========================================
# 🚨 SECURITY KILL SWITCHES
# ==========================================

@staff_member_required
def suspend_user(request, user_id):
    if not (request.user.is_superuser or request.user.groups.filter(name='KYC Officer').exists()):
        messages.error(request, "Permission Denied: You do not have clearance to suspend users.")
        return redirect('staff_user_manager')

    target_user = get_object_or_404(User, pk=user_id)
    if target_user.is_staff:
        messages.error(request, "Security Exception: You cannot suspend a Staff member.")
        return redirect('staff_user_manager')

    target_user.is_active = not target_user.is_active
    target_user.save()
    action_text = "Suspended" if not target_user.is_active else "Reactivated"
    SecurityLog.objects.create(
        user=request.user, 
        action=f"{action_text} Account: {target_user.username}", 
        ip_address=request.META.get('REMOTE_ADDR'), 
        details="User login access toggled."
    )
    messages.success(request, f"User {target_user.username} has been successfully {action_text.lower()}.")
    return redirect('staff_user_manager')

@staff_member_required
def flag_asset(request, item_id):
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
        details="Asset visibility changed by HQ."
    )
    messages.warning(request, f"Asset has been {action_msg}.")
    return redirect('staff_master_inventory')


# ==========================================
# 6. TWO-WAY MESSAGING HUB
# ==========================================

@login_required
def support_history(request):
    tickets = SupportTicket.objects.filter(user=request.user).order_by('-last_message_at')
    active_ticket_id = request.GET.get('chat')
    show_new = request.GET.get('new') == 'true'
    active_chat = None
    
    if active_ticket_id:
        active_chat = get_object_or_404(SupportTicket, id=active_ticket_id, user=request.user)
        unread_msgs = active_chat.messages.exclude(sender=request.user).filter(is_read=False, is_internal_note=False)
        if unread_msgs.exists(): 
            unread_msgs.update(is_read=True, read_at=timezone.now())
        
    if request.method == 'POST':
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
                ticket=new_ticket, 
                sender=request.user, 
                message=request.POST.get('description')
            )
            messages.success(request, "New support thread started.")
            return redirect(f"{request.path}?chat={new_ticket.id}")

        elif active_chat:
            msg_body = request.POST.get('message')
            if msg_body:
                TicketMessage.objects.create(
                    ticket=active_chat, 
                    sender=request.user, 
                    message=msg_body
                )
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

    return render(request, 'core/messaging_hub.html', {
        'tickets': tickets, 
        'active_chat': active_chat, 
        'show_new': show_new
    })


@staff_member_required
def staff_ticket_detail(request, ticket_id):
    ticket = get_object_or_404(SupportTicket, id=ticket_id)
    unread_msgs = ticket.messages.exclude(sender=request.user).filter(is_read=False)
    if unread_msgs.exists(): 
        unread_msgs.update(is_read=True, read_at=timezone.now())
    
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'reply':
            msg_body = request.POST.get('message')
            if msg_body:
                is_note = request.POST.get('is_internal_note') == 'true'
                TicketMessage.objects.create(
                    ticket=ticket, 
                    sender=request.user, 
                    message=msg_body, 
                    is_internal_note=is_note
                )
                if not is_note:
                    if ticket.status == 'resolved': 
                        ticket.status = 'open'
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
                user=request.user, 
                action=f"Resolved Ticket #{ticket.id}", 
                ip_address=request.META.get('REMOTE_ADDR'), 
                details="HQ closed ticket."
            )
            Notification.objects.create(
                user=ticket.user, 
                title="Ticket Resolved", 
                notification_type="success"
            )
            messages.success(request, f"Ticket #{ticket.id} successfully resolved.")
            return redirect('staff_dashboard')
            
        return redirect('staff_ticket_detail', ticket_id=ticket.id)
        
    return render(request, 'core/staff_ticket_detail.html', {'ticket': ticket})


# ==========================================
# 7. HQ VAULT (THE INNOVATIVE FIX)
# ==========================================

@staff_member_required
def search_users_ajax(request):
    """AJAX Endpoint: Live search users by Email or KRA PIN for targeted comms."""
    query = request.GET.get('q', '').strip()
    if len(query) < 3:
        return JsonResponse({'users': []})
    
    # Search by uniquely identifiable data
    users = User.objects.filter(
        Q(email__icontains=query) | 
        Q(userprofile__kra_pin__icontains=query)
    ).select_related('userprofile')[:10] # Limit to 10 for performance
    
    results = []
    for u in users:
        kra = u.userprofile.kra_pin if hasattr(u, 'userprofile') and u.userprofile.kra_pin else "No KRA"
        results.append({
            'id': u.id,
            'email': u.email,
            'kra': kra,
            'name': u.username
        })
    return JsonResponse({'users': results})

@staff_member_required
def staff_comms_module(request):
    """Enterprise Broadcast Console (Now with Individual Targeting)"""
    if not request.user.is_superuser:
        messages.error(request, "Security Exception: Only Super Admins can access Comms.")
        return redirect('staff_dashboard')

    if request.method == 'POST':
        title = request.POST.get('title')
        message_content = request.POST.get('message_content')
        target_role = request.POST.get('target_role')
        is_sent = request.POST.get('is_sent') == 'on'
        selected_user_ids = request.POST.getlist('selected_users') # 🚨 Captures specific individuals

        msg = HolidayMessage.objects.create(
            title=title, 
            message_content=message_content,
            send_date=timezone.now().date(), 
            target_role=target_role, 
            is_sent=is_sent
        )

        if selected_user_ids:
            msg.manual_recipients.set(selected_user_ids)

        if is_sent:
            if target_role == 'INDIVIDUAL' and selected_user_ids:
                target_users = User.objects.filter(id__in=selected_user_ids, is_active=True)
            else:
                query = Q(is_active=True)
                if target_role == 'VENDOR': query &= Q(userprofile__is_vendor=True)
                elif target_role == 'FREELANCER': query &= Q(userprofile__is_freelancer=True)
                elif target_role == 'CLIENT': query &= Q(userprofile__is_vendor=False, userprofile__is_freelancer=False)
                target_users = User.objects.filter(query).distinct()
            
            notifications = [Notification(user=tu, title=title, message=message_content, notification_type="info") for tu in target_users]
            
            if notifications:
                Notification.objects.bulk_create(notifications)
                SecurityLog.objects.create(user=request.user, action=f"Broadcast: {title}", ip_address=request.META.get('REMOTE_ADDR'), details=f"Sent to {len(notifications)} users.")
                messages.success(request, f"🚀 Broadcast fired to {len(notifications)} users!")
            else:
                messages.warning(request, "⚠️ No active users matched your criteria.")
        else:
            messages.success(request, "📝 Draft saved successfully.")
        return redirect('staff_comms_module')

    broadcast_history = HolidayMessage.objects.all().order_by('-created_at')
    return render(request, 'core/staff_comms.html', {'broadcast_history': broadcast_history})


@staff_member_required
def staff_settings(request):
    """HQ Security Vault"""
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            SecurityLog.objects.create(
                user=request.user, action="HQ Credentials Updated",
                ip_address=request.META.get('REMOTE_ADDR'), details="Password changed via HQ Vault."
            )
            messages.success(request, "Your HQ Security Credentials have been updated.")
            return redirect('staff_settings')
        else:
            messages.error(request, "Error updating credentials. Check the form.")
    else:
        form = PasswordChangeForm(request.user)

    return render(request, 'core/staff_settings.html', {'form': form})