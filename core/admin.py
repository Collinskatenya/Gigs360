from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.utils.html import format_html # 🚨 ADDED FOR STATUS BADGES

# 🚨 PHASE 6 & LANDING PAGE CMS IMPORTS
from .models import (
    UserProfile, SecurityLog, Notification, HolidayMessage, 
    SupportTicket, TicketMessage, SystemConfiguration,
    UpcomingActivity, ServiceFeature, Testimonial  
)
from inventory.models import InventoryItem  # Needed for safe category querying

User = get_user_model()

# ==========================================
# 1. INLINE PROFILE (Connects Profile to User)
# ==========================================
class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'Business Identity & KYC'
    fk_name = 'user'
    
    # 🚨 ZERO-KNOWLEDGE PROTOCOL: Seal the Inline Backdoor
    readonly_fields = ('get_masked_kra', 'get_masked_id', 'get_masked_account', 'ai_trust_score')
    exclude = ('kra_pin', 'id_number', 'account_number')
    
    fieldsets = (
        ('Identity & KYC', {
            'fields': ('profile_picture', 'phone_number', 'get_masked_kra', 'get_masked_id', 'dob')
        }),
        ('Business Info', {
            'fields': ('business_name', 'business_category', 'bio', 'company_logo', 'invoice_color_theme')
        }),
        ('Finance', {
            'fields': ('bank_name', 'get_masked_account', 'mpesa_number')
        }),
        ('Security & AI Status', {
            'fields': ('plan', 'subscription_end_date', 'kyc_status', 'rejection_reason', 'ai_trust_score', 'is_verified')
        }),
    )

    def get_masked_kra(self, obj):
        if obj.kra_pin and len(obj.kra_pin) > 4: return f"********{obj.kra_pin[-4:]}"
        return "Not Provided"
    get_masked_kra.short_description = 'KRA PIN'

    def get_masked_id(self, obj):
        if obj.id_number and len(obj.id_number) > 3: return f"******{obj.id_number[-3:]}"
        return "Not Provided"
    get_masked_id.short_description = 'National ID'

    def get_masked_account(self, obj):
        if obj.account_number and len(obj.account_number) > 4: return f"********{obj.account_number[-4:]}"
        return "Not Provided"
    get_masked_account.short_description = 'Bank Account'

# ==========================================
# 2. CUSTOM USER ADMIN
# ==========================================
class CustomUserAdmin(BaseUserAdmin):
    inlines = (UserProfileInline,)
    list_display = ('username', 'email', 'get_role', 'get_plan', 'is_active', 'date_joined')
    list_select_related = ('userprofile',)

    def get_role(self, instance):
        if hasattr(instance, 'userprofile'):
            if instance.userprofile.is_vendor: return "VENDOR"
            if instance.userprofile.is_agency: return "AGENCY"
            if instance.userprofile.is_freelancer: return "FREELANCER"
        return "USER"
    get_role.short_description = 'Role'

    def get_plan(self, instance):
        return instance.userprofile.plan if hasattr(instance, 'userprofile') else "N/A"
    get_plan.short_description = 'Plan'

    # 🚨 NOTIFICATION LOOP: Catch KYC changes if edited via User page
    def save_formset(self, request, form, formset, change):
        if formset.model == UserProfile:
            instances = formset.save(commit=False)
            for instance in instances:
                if change and instance.pk:
                    old_obj = UserProfile.objects.get(pk=instance.pk)
                    if instance.kyc_status == 'REJECTED' and old_obj.kyc_status != 'REJECTED':
                        Notification.objects.create(user=instance.user, title="Verification Failed ❌", message=f"Your KYC verification was rejected. Reason: {instance.rejection_reason}", notification_type="error")
                    elif instance.kyc_status == 'APPROVED' and old_obj.kyc_status != 'APPROVED':
                        Notification.objects.create(user=instance.user, title="Account Verified! ✅", message="Your legal identity has been approved. You can now use Escrow.", notification_type="success")
                instance.save()
            formset.save_m2m()
        else:
            super().save_formset(request, form, formset, change)


# ==========================================
# 2B. DEDICATED KYC DASHBOARD (SENTINEL)
# ==========================================
@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    """Standalone Admin for KYC Officers to review flagged accounts safely."""
    list_display = ('user', 'business_name', 'status_badge', 'ai_trust_score', 'get_masked_kra')
    list_filter = ('kyc_status', 'plan')
    search_fields = ('user__email', 'business_name', 'kra_pin')
    
    readonly_fields = ('get_masked_kra', 'get_masked_id', 'get_masked_account', 'ai_trust_score')
    exclude = ('kra_pin', 'id_number', 'account_number')

    def get_masked_kra(self, obj):
        if obj.kra_pin and len(obj.kra_pin) > 4: return f"********{obj.kra_pin[-4:]}"
        return "Not Provided"
    get_masked_kra.short_description = 'KRA PIN'

    def get_masked_id(self, obj):
        if obj.id_number and len(obj.id_number) > 3: return f"******{obj.id_number[-3:]}"
        return "Not Provided"
    get_masked_id.short_description = 'National ID'
    
    def get_masked_account(self, obj):
        if obj.account_number and len(obj.account_number) > 4: return f"********{obj.account_number[-4:]}"
        return "Not Provided"
    get_masked_account.short_description = 'Bank Account'

    def status_badge(self, obj):
        colors = {'APPROVED': 'green', 'PENDING': 'orange', 'FLAGGED': 'red', 'REJECTED': 'black', 'UNVERIFIED': 'gray'}
        color = colors.get(obj.kyc_status, 'gray')
        return format_html('<span style="color: white; background-color: {}; padding: 3px 8px; border-radius: 10px; font-weight: bold;">{}</span>', color, obj.kyc_status)
    status_badge.short_description = 'KYC Status'

    def save_model(self, request, obj, form, change):
        if change:
            old_obj = UserProfile.objects.get(pk=obj.pk)
            if obj.kyc_status == 'REJECTED' and old_obj.kyc_status != 'REJECTED':
                Notification.objects.create(user=obj.user, title="Verification Failed ❌", message=f"Reason: {obj.rejection_reason}", notification_type="error")
            elif obj.kyc_status == 'APPROVED' and old_obj.kyc_status != 'APPROVED':
                Notification.objects.create(user=obj.user, title="Account Verified! ✅", message="Your identity has been approved.", notification_type="success")
        super().save_model(request, obj, form, change)


# ==========================================
# 3. SECURITY & SYSTEM CONFIGURATION
# ==========================================
@admin.register(SecurityLog)
class SecurityLogAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'user', 'action', 'ip_address', 'is_suspicious')
    list_filter = ('action', 'is_suspicious', 'created_at')
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False

@admin.register(SystemConfiguration)
class SystemConfigurationAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'platform_commission_rate', 'defcon_3_freeze_signups', 'defcon_2_freeze_marketplace')


# ==========================================
# 4. HELPDESK ADMIN
# ==========================================
class TicketMessageInline(admin.TabularInline):
    model = TicketMessage
    extra = 0
    readonly_fields = ('sender', 'created_at', 'is_internal_note')
    can_delete = False

@admin.register(SupportTicket)
class SupportTicketAdmin(admin.ModelAdmin):
    list_display = ('subject', 'user', 'category', 'priority', 'status', 'created_at')
    list_filter = ('status', 'priority', 'category')
    search_fields = ('subject', 'description', 'user__username', 'user__email')
    inlines = [TicketMessageInline] 
    readonly_fields = ('created_at',)


# ==========================================
# 5. MILLION-USER COMMS ENGINE (PHASE 6)
# ==========================================
@admin.register(HolidayMessage)
class HolidayMessageAdmin(admin.ModelAdmin):
    list_display = ('title', 'send_date', 'target_role', 'is_sent', 'is_birthday_automation')
    list_filter = ('is_sent', 'target_role', 'is_birthday_automation')
    search_fields = ('title', 'message_content')
    
    # 🚨 MILLION-USER UI OPTIMIZATION
    filter_horizontal = ('target_categories',)
    raw_id_fields = ('manual_recipients',)
    
    fieldsets = (
        ('Broadcast Content', {
            'fields': ('title', 'message_content', 'send_date', 'is_sent')
        }),
        ('Smart Targeting (The Algorithm)', {
            'fields': ('target_role', 'target_categories'),
            'description': 'Select your audience. E.g., Target "Freelancers" who own "Drones".'
        }),
        ('Manual Overrides & Automations', {
            'fields': ('manual_recipients', 'is_birthday_automation'),
            'classes': ('collapse',),
            'description': 'Use this for single-user VIP messages or setting up the Birthday bot.'
        }),
    )

    # 🚨 THE INTERCEPT ENGINE (Generates Notifications on Save)
    def save_model(self, request, obj, form, change):
        # Save the object first so ManyToMany fields (categories) are locked in.
        super().save_model(request, obj, form, change)
        
        # If the admin manually checks "Is Sent", trigger the broadcast algorithm!
        if obj.is_sent and 'is_sent' in form.changed_data:
            target_users = obj.manual_recipients.all()
            
            # Rule-Based Segmenting (If no manual users specified)
            if not target_users.exists():
                query = Q(is_active=True)
                
                # Filter by Role
                if obj.target_role == 'VENDOR':
                    query &= Q(userprofile__is_vendor=True)
                elif obj.target_role == 'FREELANCER':
                    query &= Q(userprofile__is_freelancer=True)
                elif obj.target_role == 'CLIENT':
                    query &= Q(userprofile__is_vendor=False, userprofile__is_freelancer=False)
                    
                # Filter by Gear Category (Safe Query Method)
                if obj.target_categories.exists():
                    # Find owners of gear in these specific categories
                    owner_ids = InventoryItem.objects.filter(
                        category__in=obj.target_categories.all()
                    ).values_list('owner_id', flat=True).distinct()
                    
                    query &= Q(id__in=owner_ids)
                
                # Execute query
                target_users = User.objects.filter(query).distinct()

            # Bulk Generate the Notifications
            notifications = []
            for target_user in target_users:
                notifications.append(
                    Notification(
                        user=target_user,
                        title=obj.title,
                        message=obj.message_content,
                        notification_type="info"
                    )
                )
            
            if notifications:
                Notification.objects.bulk_create(notifications)
                self.message_user(request, f"🚀 Broadcast Successfully Sent to {len(notifications)} users!")
            else:
                self.message_user(request, "⚠️ No active users matched your targeting criteria.", level='WARNING')


# ==========================================
# 6. REGISTER EVERYTHING
# ==========================================

# Unregister User if it was registered by default (safety check)
try:
    admin.site.unregister(User)
except admin.sites.NotRegistered:
    pass

admin.site.register(User, CustomUserAdmin)
admin.site.register(Notification)

# ==========================================
# 7. LANDING PAGE CMS (Dynamic Content)
# ==========================================

@admin.register(UpcomingActivity)
class UpcomingActivityAdmin(admin.ModelAdmin):
    list_display = ('title', 'event_date', 'is_active')
    list_filter = ('is_active',)

@admin.register(ServiceFeature)
class ServiceFeatureAdmin(admin.ModelAdmin):
    list_display = ('title', 'order', 'is_active')
    list_editable = ('order', 'is_active')

@admin.register(Testimonial)
class TestimonialAdmin(admin.ModelAdmin):
    list_display = ('client_name', 'role', 'rating', 'is_active')
    list_filter = ('is_active', 'rating')