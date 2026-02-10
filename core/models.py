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
# 4. COMMUNICATIONS & ALERTS
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
    title = models.CharField(max_length=100)
    send_date = models.DateField()
    message_content = models.TextField(max_length=160)
    is_sent = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.title} - {self.send_date}"


# ==========================================
# 5. USER PROFILE (Identity Layer)
# ==========================================

class UserProfile(TimeStampedModel): 
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='userprofile')
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # --- IDENTITY & KYC ---
    profile_picture = models.ImageField(upload_to='profile_pics/', default='default.jpg', blank=True)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    bio = models.TextField(blank=True, max_length=500, null=True)
    
    # LEGAL DATA
    kra_pin = models.CharField(max_length=20, blank=True, null=True, unique=True, db_index=True)
    id_number = models.CharField(max_length=20, blank=True, null=True, unique=True, db_index=True)
    dob = models.DateField(null=True, blank=True)
    
    # --- BUSINESS ---
    business_name = models.CharField(max_length=100, blank=True, null=True)
    company_logo = models.ImageField(upload_to='company_logos/', blank=True, null=True)
    invoice_color_theme = models.CharField(max_length=7, default='#003366')
    
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
    PLAN_CHOICES = [('free', 'Free Starter'), ('pro', 'Pro Business'), ('enterprise', 'Enterprise')]
    plan = models.CharField(max_length=20, choices=PLAN_CHOICES, default='free')
    subscription_end_date = models.DateTimeField(null=True, blank=True)
    auto_renew = models.BooleanField(default=False)
    
    # --- SECURITY ---
    is_verified = models.BooleanField(default=False)
    is_2fa_enabled = models.BooleanField(default=False)
    last_login_ip = models.GenericIPAddressField(null=True, blank=True)
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
        if self.plan == 'free': return True
        return self.subscription_end_date and self.subscription_end_date > timezone.now()


# ==========================================
# 6. HELPDESK SYSTEM (The Missing Piece!)
# ==========================================

class SupportTicket(TimeStampedModel):
    CATEGORY_CHOICES = [
        ('billing', 'Billing & Finance'),
        ('verification', 'Account Verification'),
        ('technical', 'Technical Issue'),
        ('general', 'General Inquiry'),
        ('internal', 'Internal Staff Issue'), 
    ]
    STATUS_CHOICES = [('open', 'Open'), ('in_progress', 'In Progress'), ('resolved', 'Resolved')]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='support_tickets')
    subject = models.CharField(max_length=200)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    description = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')
    priority = models.CharField(max_length=10, choices=[('low', 'Low'), ('medium', 'Medium'), ('high', 'High')], default='medium')

    def __str__(self):
        return f"[{self.get_status_display()}] {self.subject}"

class TicketMessage(TimeStampedModel):
    ticket = models.ForeignKey(SupportTicket, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    message = models.TextField()
    
    def __str__(self):
        return f"Msg by {self.sender.username}"


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