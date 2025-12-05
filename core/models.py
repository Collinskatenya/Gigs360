from django.db import models
from django.contrib.auth.models import AbstractUser

# 1. CUSTOM USER MODEL
class User(AbstractUser):
    # Role Flags
    is_client = models.BooleanField(default=False)
    is_vendor = models.BooleanField(default=False)
    is_planner = models.BooleanField(default=False)
    
    # Contact Info
    phone_number = models.CharField(max_length=15, blank=True, null=True)

    def __str__(self):
        return self.username

# 2. VENDOR PROFILE (For Photographers, Decorators, etc.)
class VendorProfile(models.Model):
    CATEGORY_CHOICES = [
        ('PHOTO', 'Photography & Video'),
        ('DECOR', 'Decor & Flowers'),
        ('ENT', 'MC & DJ'),
        ('PLANNING', 'Event Planning'),
    ]
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='vendor_profile')
    business_name = models.CharField(max_length=100)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    
    def __str__(self):
        return self.business_name