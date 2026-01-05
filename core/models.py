from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
from django.urls import reverse

# ==========================================
# 1. CUSTOM USER MODEL
# ==========================================

class User(AbstractUser):
    # --- ROLE FLAGS ---
    is_client = models.BooleanField(default=False, verbose_name="Is Freelancer")
    is_vendor = models.BooleanField(default=False, verbose_name="Is Vendor")
    is_planner = models.BooleanField(default=False, verbose_name="Is Agency")
    
    # --- STAFF GOVERNANCE ---
    ROLE_CHOICES = [
        ('ADMIN', 'Super Admin'),
        ('UX_EXPERT', 'UX/UI Designer'),
        ('DEV', 'Software Engineer'),
        ('MARKETING', 'Marketing Lead'),
        ('FINANCE', 'Finance Manager'),
        ('SUPPORT', 'Customer Support'),
    ]
    staff_role = models.CharField(max_length=50, choices=ROLE_CHOICES, blank=True, null=True)
    employee_id = models.CharField(max_length=20, blank=True, null=True, help_text="e.g. GIG-EMP-001")

    # --- BUSINESS INFO ---
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
    business_type = models.CharField(max_length=50, choices=BUSINESS_TYPE_CHOICES, blank=True, null=True)
    number_of_employees = models.PositiveIntegerField(default=1, blank=True, null=True)
    
    # --- CONTACT & MEDIA ---
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    profile_picture = models.ImageField(upload_to='profile_pics/', blank=True, null=True)
    
    # --- SUBSCRIPTION ---
    SUBSCRIPTION_CHOICES = [
        ('Free', 'Free Starter'),
        ('Pro', 'Pro Business'),
        ('Enterprise', 'Enterprise'),
    ]
    subscription_plan = models.CharField(
        max_length=20, 
        choices=SUBSCRIPTION_CHOICES, 
        default='Free'
    )
    subscription_expiry = models.DateTimeField(blank=True, null=True)

    # --- PAYMENT INFO ---
    bank_name = models.CharField(max_length=100, blank=True, null=True)
    account_number = models.CharField(max_length=50, blank=True, null=True)
    mpesa_number = models.CharField(max_length=15, blank=True, null=True)
    
    # --- SETTINGS ---
    theme_preference = models.CharField(
        max_length=10, 
        choices=[('light', 'Light'), ('dark', 'Dark')], 
        default='light'
    )

    # --- HELPER METHODS ---
    def get_role_label(self):
        """Returns the dashboard badge label"""
        if self.is_superuser: return "System Owner"
        if self.is_staff and self.staff_role: return self.get_staff_role_display()
        # Fallback if get_subscription_plan_display isn't available
        for code, label in self.SUBSCRIPTION_CHOICES:
            if code == self.subscription_plan:
                return label
        return self.subscription_plan

    @property
    def is_pro_member(self):
        return self.subscription_plan in ['Pro', 'Enterprise']

    def is_online(self):
        if self.last_login:
            return (timezone.now() - self.last_login).seconds < 900
        return False

    def __str__(self):
        if self.business_name:
            return f"{self.username} ({self.business_name})"
        return self.username


# ==========================================
# 2. NOTIFICATION SYSTEM (New)
# ==========================================

class Notification(models.Model):
    """
    Stores persistent alerts for the user (Bell Icon).
    """
    TYPES = [
        ('success', 'Success'), # Green Check
        ('info', 'Info'),       # Blue Info
        ('warning', 'Warning'), # Yellow Triangle 
        ('error', 'Error'),     # Red Alert
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=255)
    message = models.TextField()
    link = models.CharField(max_length=255, blank=True, null=True, help_text="URL to redirect to when clicked")
    notification_type = models.CharField(max_length=20, choices=TYPES, default='info')
    
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} - {self.title}"