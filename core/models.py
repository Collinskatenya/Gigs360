from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone

class User(AbstractUser):
    # ==========================================
    # 1. ROLE FLAGS (Who are they?)
    # ==========================================
    is_client = models.BooleanField(default=False, verbose_name="Is Freelancer")
    is_vendor = models.BooleanField(default=False, verbose_name="Is Vendor")
    is_planner = models.BooleanField(default=False, verbose_name="Is Agency")
    
    # ==========================================
    # 2. STAFF GOVERNANCE (Internal Employees)
    # ==========================================
    # Only used if is_staff=True
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

    # ==========================================
    # 3. CLIENT BUSINESS INFO
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
    business_type = models.CharField(max_length=50, choices=BUSINESS_TYPE_CHOICES, blank=True, null=True)
    number_of_employees = models.PositiveIntegerField(default=1, blank=True, null=True)
    
    # Contact & Media
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    profile_picture = models.ImageField(upload_to='profile_pics/', blank=True, null=True)
    
    # ==========================================
    # 4. SUBSCRIPTION CONTROL (The Revenue Engine)
    # ==========================================
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

    # ==========================================
    # 5. PAYMENT INFO (MPESA / BANK)
    # ==========================================
    bank_name = models.CharField(max_length=100, blank=True, null=True)
    account_number = models.CharField(max_length=50, blank=True, null=True)
    mpesa_number = models.CharField(max_length=15, blank=True, null=True)
    
    # ==========================================
    # 6. SETTINGS
    # ==========================================
    theme_preference = models.CharField(
        max_length=10, 
        choices=[('light', 'Light'), ('dark', 'Dark')], 
        default='light'
    )

    # ==========================================
    # 7. HELPER METHODS (Logic)
    # ==========================================
    def get_role_label(self):
        """Returns the dashboard badge label (Staff Role vs Plan)"""
        if self.is_superuser: return "System Owner"
        if self.is_staff and self.staff_role: return self.get_staff_role_display()
        return self.get_subscription_plan_display()

    @property
    def is_pro_member(self):
        """Checks if user is Pro or Enterprise"""
        return self.subscription_plan in ['Pro', 'Enterprise']

    def is_online(self):
        if self.last_login:
            return (timezone.now() - self.last_login).seconds < 900
        return False

    def __str__(self):
        if self.business_name:
            return f"{self.username} ({self.business_name})"
        return self.username