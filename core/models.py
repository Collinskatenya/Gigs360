from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone

class User(AbstractUser):
    # ==========================================
    # 1. ROLE FLAGS
    # ==========================================
    is_client = models.BooleanField(default=False, verbose_name="Is Freelancer")
    is_vendor = models.BooleanField(default=False, verbose_name="Is Vendor")
    is_planner = models.BooleanField(default=False, verbose_name="Is Agency")
    
    # ==========================================
    # 2. PERSONAL & CONTACT DETAILS
    # ==========================================
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    profile_picture = models.ImageField(upload_to='profile_pics/', blank=True, null=True)
    
    # ==========================================
    # 3. BUSINESS INFORMATION
    # ==========================================
    BUSINESS_TYPE_CHOICES = [
        ('PHOTO', 'Photography & Video'),
        ('DECOR', 'Decor & Flowers'),
        ('ENT', 'MC & DJ'),
        ('PLANNING', 'Event Planning'),
        ('SECURITY', 'Security & Bouncers'),
        ('CATERING', 'Catering'),
        ('OTHER', 'Other'),
    ]
    
    business_name = models.CharField(max_length=100, blank=True, null=True)
    business_type = models.CharField(
        max_length=50, 
        choices=BUSINESS_TYPE_CHOICES, 
        blank=True, 
        null=True, 
        help_text="Select your primary industry"
    )
    number_of_employees = models.PositiveIntegerField(default=1, blank=True, null=True)
    
    # ==========================================
    # 4. BANKING / PAYMENT INFO
    # ==========================================
    bank_name = models.CharField(max_length=100, blank=True, null=True)
    account_number = models.CharField(max_length=50, blank=True, null=True)
    mpesa_number = models.CharField(max_length=15, blank=True, null=True)
    
    # ==========================================
    # 5. DASHBOARD SETTINGS
    # ==========================================
    theme_preference = models.CharField(
        max_length=10, 
        choices=[('light', 'Light'), ('dark', 'Dark')], 
        default='light',
        blank=True
    )
    
    # ==========================================
    # 6. SUBSCRIPTION CONTROL (FIXED)
    # ==========================================
    SUBSCRIPTION_CHOICES = [
        ('Free', 'Free Starter'),
        ('Pro', 'Pro Business'),
        ('Enterprise', 'Enterprise'),
    ]
    
    subscription_plan = models.CharField(
        max_length=20, 
        choices=SUBSCRIPTION_CHOICES,  # <--- Dropdown Logic
        default='Free'
    )
    subscription_expiry = models.DateTimeField(blank=True, null=True)

    # ==========================================
    # 7. HELPER METHODS
    # ==========================================
    def is_subscription_active(self):
        """
        Checks if the user has a valid subscription.
        Free plan is always active. Paid plans check the expiry date.
        """
        if self.subscription_plan == 'Free':
            return True
        if self.is_superuser:
            return True
            
        # For paid plans, check expiry
        if self.subscription_expiry:
            return self.subscription_expiry > timezone.now()
            
        # If plan is Pro/Enterprise but no date set (e.g. manual upgrade), allow it
        return True 

    def is_online(self):
        """Checks if user was active in the last 15 minutes."""
        if self.last_login:
            return (timezone.now() - self.last_login).seconds < 900
        return False

    def __str__(self):
        if self.business_name:
            return f"{self.username} ({self.business_name})"
        return self.username