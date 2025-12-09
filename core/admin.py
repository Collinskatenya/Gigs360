from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User

class CustomUserAdmin(UserAdmin):
    model = User
    
    # 1. Display these columns in the list view
    list_display = (
        'username', 'email', 'phone_number', 
        'is_vendor', 'is_planner', 'is_client', 
        'business_name', 'subscription_plan'
    )
    
    # 2. Add filters to the right sidebar
    list_filter = ('subscription_plan', 'is_vendor', 'is_planner', 'is_active')
    
    # 3. Organize the Edit User page to show your new fields
    fieldsets = UserAdmin.fieldsets + (
        ('Role Flags', {'fields': ('is_vendor', 'is_planner', 'is_client')}),
        ('Personal Info', {'fields': ('phone_number', 'profile_picture')}),
        ('Business Details', {'fields': ('business_name', 'business_type', 'number_of_employees')}),
        ('Banking Info', {'fields': ('bank_name', 'account_number', 'mpesa_number')}),
        # FIX: Updated to 'subscription_expiry' to match your Model
        ('Subscription & Settings', {'fields': ('subscription_plan', 'subscription_expiry', 'theme_preference')}),
    )

# Register the new User Admin
admin.site.register(User, CustomUserAdmin)