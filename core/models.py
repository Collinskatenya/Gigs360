import uuid
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

# ==========================================
# 1. CUSTOM USER MODEL
# ==========================================

class User(AbstractUser):
    """
    The Custom User Model required by settings.AUTH_USER_MODEL.
    """
    pass


# ==========================================
# 2. ENTERPRISE ABSTRACT MODELS
# ==========================================

class TimeStampedModel(models.Model):
    """Standardizes timestamping across the entire SaaS."""
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

class SoftDeleteManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)

class SoftDeleteModel(models.Model):
    is_deleted = models.BooleanField(default=False, db_index=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    objects = SoftDeleteManager() 
    all_objects = models.Manager() 

    def delete(self, using=None, keep_parents=False):
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save()

    def restore(self):
        self.is_deleted = False
        self.deleted_at = None
        self.save()

    class Meta:
        abstract = True


# ==========================================
# 3. SECURITY & LOGS
# ==========================================

class SecurityLog(TimeStampedModel):
    ACTION_CHOICES = [
        ('LOGIN', 'Login Success'),
        ('LOGIN_FAIL', 'Login Failed'),
        ('LOGOUT', 'Logout'),
        ('SUDO_MODE', 'Critical Action'),
        ('BAN_IP', 'IP Banned'),
        ('PASSWORD_CHANGE', 'Password Changed'),
        ('STAFF_ACCESS', 'Staff Accessed User Account'),
        ('KYC_VERIFY', 'KYC Verification'),
    ]
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='security_logs'
    )
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    action = models.CharField(max_length=50, choices=ACTION_CHOICES, db_index=True)
    details = models.TextField(help_text="User Agent, Device Info, or Error Message")
    is_suspicious = models.BooleanField(default=False)

    def __str__(self):
        user_str = self.user.username if self.user else "Anonymous"
        return f"[{self.created_at.strftime('%H:%M:%S')}] {user_str} - {self.get_action_display()}"


# ==========================================
# 4. SUPER ADMIN COMMAND (DEFCON KILL SWITCHES)
# ==========================================

class SystemConfiguration(TimeStampedModel):
    """
    Singleton model for Super Admin global settings and DEFCON Kill Switches.
    Only one row of this will ever exist in the database.
    """
    # 🚨 DEFCON Tiers
    defcon_3_freeze_signups = models.BooleanField(default=False, help_text="DEFCON 3: Stops new user registrations (Bot attack defense).")
    defcon_2_freeze_marketplace = models.BooleanField(default=False, help_text="DEFCON 2: Disables all checkout/booking APIs.")
    defcon_1_nuclear_shutdown = models.BooleanField(default=False, help_text="DEFCON 1: Full system maintenance mode. Logs out all non-admins.")

    # Platform Finance Globals
    platform_commission_rate = models.DecimalField(max_digits=5, decimal_places=2, default=10.00, help_text="Default % commission per transaction.")

    def save(self, *args, **kwargs):
        # OOP Singleton logic: Ensure only one config row ever exists
        if self.__class__.objects.exists() and not self.pk:
            self.pk = self.__class__.objects.first().pk
        super().save(*args, **kwargs)

    def __str__(self):
        return "Gigs360 Global Master Configuration"


# ==========================================
# 5. COMMUNICATIONS & ALERTS
# ==========================================

class Notification(TimeStampedModel):
    TYPE_CHOICES = [
        ('info', 'Information'),
        ('success', 'Success'),
        ('warning', 'Warning'),
        ('danger', 'Critical Alert'),
    ]
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=200)
    message = models.TextField()
    notification_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='info')
    link = models.CharField(max_length=200, blank=True)
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} - {self.user.username}"

class HolidayMessage(TimeStampedModel):
    # 🚨 PHASE 6: Role-Based Smart Segments (Updated for Individual Targeting)
    ROLE_TARGETS = [
        ('ALL', 'All Users (Global Broadcast)'),
        ('VENDOR', 'Vendors / Agencies Only'),
        ('FREELANCER', 'Freelance Professionals Only'),
        ('CLIENT', 'Standard Clients Only'),
        ('INDIVIDUAL', 'Specific Individuals'), # 🚨 ADDED FOR AJAX LIVE SEARCH
    ]

    title = models.CharField(max_length=255)
    send_date = models.DateField()
    message_content = models.TextField()
    
    # --- Advanced Millions-Scale Targeting ---
    target_role = models.CharField(max_length=20, choices=ROLE_TARGETS, default='ALL')
    
    # Target users who own specific gear (Links to your Inventory Categories)
    target_categories = models.ManyToManyField(
        'inventory.Category', 
        blank=True, 
        help_text="Send only to users who own gear in these categories. (Leave blank for no category filter)"
    )
    
    # Manual override for specific VIP users
    manual_recipients = models.ManyToManyField(
        settings.AUTH_USER_MODEL, 
        blank=True, 
        related_name="manual_broadcasts",
        help_text="Search and add specific users by ID/Email. Overrides role targeting."
    )
    
    # Automation Triggers
    is_birthday_automation = models.BooleanField(
        default=False, 
        help_text="If checked, this message acts as a template and sends automatically on a user's birthday."
    )
    
    is_sent = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.title} - Target: {self.get_target_role_display()}"


# ==========================================
# 6. USER PROFILE (Identity & MIS Layer)
# ==========================================

class UserProfile(TimeStampedModel): 
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='userprofile')
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # --- PERSONAL IDENTITY ---
    profile_picture = models.ImageField(upload_to='profile_pics/', default='default.jpg', blank=True)
    middle_name = models.CharField(max_length=50, blank=True, null=True)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    gender = models.CharField(max_length=20, choices=[('Male', 'Male'), ('Female', 'Female'), ('Other', 'Other')], blank=True, null=True)
    bio = models.TextField(blank=True, max_length=500, null=True)
    dob = models.DateField(null=True, blank=True)
    
    # --- LEGAL & ZERO-UPLOAD KYC ---
    # Note: In production, consider encrypting these fields using django-cryptography
    kra_pin = models.CharField(max_length=20, blank=True, null=True, unique=True, db_index=True)
    id_number = models.CharField(max_length=20, blank=True, null=True, unique=True, db_index=True)
    is_identity_locked = models.BooleanField(default=False, help_text="If True, user cannot edit ID/KRA without Admin Support Ticket.")
    
    # --- BUSINESS MIS & OPERATIONS ---
    business_name = models.CharField(max_length=100, blank=True, null=True)
    company_logo = models.ImageField(upload_to='company_logos/', blank=True, null=True)
    invoice_color_theme = models.CharField(max_length=7, default='#003366')
    
    county_of_residence = models.CharField(max_length=100, blank=True, null=True)
    current_city = models.CharField(max_length=100, blank=True, null=True)
    office_number = models.CharField(max_length=20, blank=True, null=True)
    
    EMPLOYEE_CHOICES = [('1-5', '1-5'), ('6-20', '6-20'), ('21-50', '21-50'), ('51+', '51+')]
    employee_count = models.CharField(max_length=20, choices=EMPLOYEE_CHOICES, blank=True, null=True)
    
    CATEGORY_CHOICES = [
        ('Photography & Video', 'Photography & Video'),
        ('Sound & DJ', 'Sound & DJ'),
        ('Decor & Flowers', 'Decor & Flowers'),
        ('Event Planning', 'Event Planning'),
        ('Transport & Logistics', 'Transport & Logistics'),
        ('Security & Bouncers', 'Security & Bouncers'),
        ('Catering', 'Catering'),
        ('Other', 'Other'),
    ]
    business_category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default='Other', null=True, blank=True)

    # --- ROLES ---
    is_freelancer = models.BooleanField(default=False)
    is_vendor = models.BooleanField(default=False)
    is_agency = models.BooleanField(default=False)
    
    # --- SUBSCRIPTION ---
    PLAN_CHOICES = [('FREE', 'Free Starter'), ('PRO', 'Pro Business'), ('ENTERPRISE', 'Enterprise')]
    plan = models.CharField(max_length=20, choices=PLAN_CHOICES, default='FREE')
    subscription_end_date = models.DateTimeField(null=True, blank=True)
    auto_renew = models.BooleanField(default=False)
    
    # --- SECURITY & PRESENCE ---
    is_verified = models.BooleanField(default=False)
    is_2fa_enabled = models.BooleanField(default=False)
    last_login_ip = models.GenericIPAddressField(null=True, blank=True)
    last_active = models.DateTimeField(default=timezone.now, db_index=True) # Asymmetric Presence Tracker

    terms_accepted = models.BooleanField(default=False)
    terms_version = models.CharField(max_length=50, blank=True, null=True)
    terms_accepted_at = models.DateTimeField(null=True, blank=True)

    # --- PAYMENT ---
    bank_name = models.CharField(max_length=100, blank=True, null=True)
    account_number = models.CharField(max_length=50, blank=True, null=True)
    mpesa_number = models.CharField(max_length=15, blank=True, null=True)

    def __str__(self):
        return f"{self.user.username}'s Profile"

    @property
    def is_subscription_active(self):
        if self.plan == 'FREE': return True
        return self.subscription_end_date and self.subscription_end_date > timezone.now()
        
    @property
    def is_online(self):
        """Returns True if the user was active in the last 3 minutes."""
        now = timezone.now()
        return self.last_active >= now - timezone.timedelta(minutes=3)


# ==========================================
# 7. UNIFIED MESSAGING & HELPDESK HUB
# ==========================================

class SupportTicket(TimeStampedModel):
    CATEGORY_CHOICES = [
        ('billing', 'Billing & Finance'),
        ('verification', 'Account Verification'),
        ('technical', 'Technical Issue / Bug'),
        ('general', 'General Inquiry'),
        ('internal', 'Internal Staff Issue'), 
    ]
    STATUS_CHOICES = [
        ('open', 'Open'), 
        ('in_progress', 'Processing'), 
        ('resolved', 'Resolved')
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='support_tickets')
    subject = models.CharField(max_length=200)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    description = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')
    priority = models.CharField(max_length=10, choices=[('low', 'Low'), ('medium', 'Medium'), ('high', 'High')], default='medium')
    last_message_at = models.DateTimeField(default=timezone.now)

    def save(self, *args, **kwargs):
        if self.category in ['billing', 'internal']:
            self.priority = 'high'
        super().save(*args, **kwargs)

    def __str__(self):
        return f"[{self.status.upper()}] {self.subject} - {self.user.username}"


class TicketMessage(TimeStampedModel):
    ticket = models.ForeignKey(SupportTicket, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    message = models.TextField()
    
    # Read Receipts
    is_read = models.BooleanField(default=False, db_index=True)
    read_at = models.DateTimeField(null=True, blank=True)
    
    # 🚨 Ghost Notes (Invisible to the client)
    is_internal_note = models.BooleanField(default=False)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        note_flag = " [NOTE]" if self.is_internal_note else ""
        return f"Msg{note_flag} from {self.sender.username} in Ticket #{self.ticket.id}"


# --- SIGNALS ---
@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)

@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def save_user_profile(sender, instance, **kwargs):
    try:
        instance.userprofile.save()
    except UserProfile.DoesNotExist:
        UserProfile.objects.create(user=instance)