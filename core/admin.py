from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Notification, HolidayMessage

class CustomUserAdmin(UserAdmin):
    model = User
    
    # 1. LIST VIEW: Updated 'subscription_plan' -> 'plan'
    list_display = (
        'username', 'email', 'phone_number', 
        'is_client', 'plan',       
        'is_staff', 'staff_role'           
    )
    
    # 2. FILTERS: Updated 'subscription_plan' -> 'plan'
    list_filter = ('staff_role', 'plan', 'is_staff', 'is_client', 'is_active')
    
    # 3. EDIT PAGE: Organized into clear sections
    fieldsets = UserAdmin.fieldsets + (
        ('Gigs360 Staff Governance', {
            'fields': ('staff_role', 'employee_id'),
            'description': 'Internal Employee controls. Only use for Staff members.'
        }),
        ('Client Role Flags', {
            'fields': ('is_client', 'is_vendor', 'is_planner')
        }),
        ('Personal Info', {
            # Added date_of_birth here
            'fields': ('phone_number', 'profile_picture', 'date_of_birth')
        }),
        ('Business Details', {
            # Added company_logo and invoice_color_theme here
            'fields': ('business_name', 'business_type', 'number_of_employees', 'company_logo', 'invoice_color_theme')
        }),
        ('Banking Info', {
            'fields': ('bank_name', 'account_number', 'mpesa_number')
        }),
        ('Subscription & Settings', {
            'fields': ('plan', 'subscription_expiry', 'theme_preference')
        }),
    )

# --- NEW: HOLIDAY MESSAGE ADMIN ---
@admin.register(HolidayMessage)
class HolidayMessageAdmin(admin.ModelAdmin):
    list_display = ['title', 'send_date', 'is_sent']
    list_filter = ['is_sent', 'send_date']
    actions = ['send_bulk_sms']

    @admin.action(description='Send SMS to all Users')
    def send_bulk_sms(self, request, queryset):
        """
        Simulates sending SMS to all users. 
        In Phase 2, we will connect this to an actual SMS Gateway (e.g. Africa's Talking).
        """
        count = 0
        for msg in queryset:
            if not msg.is_sent:
                # Logic to trigger SMS sending would go here
                msg.is_sent = True
                msg.save()
                count += 1
        
        if count > 0:
            self.message_user(request, f"Successfully sent '{count}' broadcast messages.")
        else:
            self.message_user(request, "Selected messages were already sent.", level='warning')

# Register the new User Admin
admin.site.register(User, CustomUserAdmin)
# Register Notifications (So you can see/delete alerts)
admin.site.register(Notification)