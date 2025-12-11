from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User

class CustomUserAdmin(UserAdmin):
    model = User
    
    # 1. LIST VIEW: Added 'staff_role' so you can spot employees quickly
    list_display = (
        'username', 'email', 'phone_number', 
        'is_client', 'subscription_plan',  # Client info
        'is_staff', 'staff_role'           # Employee info
    )
    
    # 2. FILTERS: Added 'staff_role' to filter employees by department
    list_filter = ('staff_role', 'subscription_plan', 'is_staff', 'is_client', 'is_active')
    
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
            'fields': ('phone_number', 'profile_picture')
        }),
        ('Business Details', {
            'fields': ('business_name', 'business_type', 'number_of_employees')
        }),
        ('Banking Info', {
            'fields': ('bank_name', 'account_number', 'mpesa_number')
        }),
        ('Subscription & Settings', {
            'fields': ('subscription_plan', 'subscription_expiry', 'theme_preference')
        }),
    )

# Register the new User Admin
admin.site.register(User, CustomUserAdmin)