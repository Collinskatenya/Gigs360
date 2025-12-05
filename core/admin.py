from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, VendorProfile

# Custom Display for the User Table
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'phone_number', 'is_vendor', 'is_planner', 'is_client')
    fieldsets = UserAdmin.fieldsets + (
        ('RadaGig Roles', {'fields': ('is_client', 'is_vendor', 'is_planner', 'phone_number', 'profile_picture')}),
    )

admin.site.register(User, CustomUserAdmin)
admin.site.register(VendorProfile)