from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth import get_user_model
# FIX: Added SupportTicket and TicketMessage to imports
from .models import UserProfile, SecurityLog, Notification, HolidayMessage, SupportTicket, TicketMessage

User = get_user_model()

# ==========================================
# 1. INLINE PROFILE (Connects Profile to User)
# ==========================================
class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'Business Identity & KYC'
    fk_name = 'user'
    
    fieldsets = (
        ('Identity & KYC', {
            'fields': ('profile_picture', 'phone_number', 'kra_pin', 'id_number', 'dob')
        }),
        ('Business Info', {
            'fields': ('business_name', 'business_category', 'bio', 'company_logo', 'invoice_color_theme')
        }),
        ('Finance', {
            'fields': ('bank_name', 'account_number', 'mpesa_number')
        }),
        ('Status', {
            'fields': ('plan', 'subscription_end_date', 'is_verified')
        }),
    )

# ==========================================
# 2. CUSTOM USER ADMIN
# ==========================================
class UserAdmin(BaseUserAdmin):
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

# ==========================================
# 3. SECURITY LOG
# ==========================================
@admin.register(SecurityLog)
class SecurityLogAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'user', 'action', 'ip_address', 'is_suspicious')
    list_filter = ('action', 'is_suspicious', 'created_at')
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False

# ==========================================
# 4. HOLIDAY MESSAGES
# ==========================================
@admin.register(HolidayMessage)
class HolidayMessageAdmin(admin.ModelAdmin):
    list_display = ['title', 'send_date', 'is_sent']
    list_filter = ['is_sent', 'send_date']
    actions = ['send_bulk_sms']

    @admin.action(description='Send SMS to all Users')
    def send_bulk_sms(self, request, queryset):
        count = 0
        for msg in queryset:
            if not msg.is_sent:
                msg.is_sent = True
                msg.save()
                count += 1
        self.message_user(request, f"Queued {count} messages for sending.")

# ==========================================
# 5. HELPDESK ADMIN (New)
# ==========================================

class TicketMessageInline(admin.TabularInline):
    model = TicketMessage
    extra = 0
    readonly_fields = ('sender', 'created_at')
    can_delete = False

@admin.register(SupportTicket)
class SupportTicketAdmin(admin.ModelAdmin):
    list_display = ('subject', 'user', 'category', 'priority', 'status', 'created_at')
    list_filter = ('status', 'priority', 'category')
    search_fields = ('subject', 'description', 'user__username', 'user__email')
    inlines = [TicketMessageInline] # View chat history inside the ticket
    readonly_fields = ('created_at',)

# ==========================================
# 6. REGISTER EVERYTHING
# ==========================================

# Unregister User if it was registered by default (safety check)
try:
    admin.site.unregister(User)
except admin.sites.NotRegistered:
    pass

admin.site.register(User, UserAdmin)
admin.site.register(Notification)