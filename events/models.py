from django.db import models
from django.conf import settings
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.db.models import Sum
import uuid
import math

# ==========================================
# 1. EVENT OPERATIONS (Master Blueprint v10.0)
# ==========================================

class Event(models.Model):
    EVENT_TYPES = [
        ('WEDDING', 'Wedding'),
        ('PRE_WEDDING', 'Pre-Wedding / Ruracio'),
        ('FUNERAL', 'Funeral'),
        ('GRADUATION', 'Graduation'),
        ('BIRTHDAY', 'Birthday Party'),
        ('ANNIVERSARY', 'Anniversary'),
        ('CONFERENCE', 'Corporate Conference'),
        ('CONCERT', 'Music Concert'),
        ('OTHER', 'Other'),
    ]

    STATUS_CHOICES = [
        ('DRAFT', 'Draft (Planning)'),
        ('REQUESTED', 'Requested (Awaiting Approval)'),
        ('APPROVED', 'Approved (Ready)'),
        ('ACTIVE', 'Active (In Progress)'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
    ]

    # TRI-ROLE ECOSYSTEM: Linking the actual users
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='vendor_events', help_text="The Vendor/Creator managing the event")
    client = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='booked_gigs', help_text="The registered Client (from Sticky Cart)")
    
    title = models.CharField(max_length=200, help_text="e.g. Katenya & Faith Wedding")
    event_type = models.CharField(max_length=50, choices=EVENT_TYPES, default='OTHER')
    description = models.TextField(blank=True)
    
    location = models.CharField(max_length=200)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='DRAFT')
    is_completed = models.BooleanField(default=False) 
    
    # Legacy Fallbacks (Preserved to avoid crashing existing data)
    client_name = models.CharField(max_length=100, blank=True)
    client_contact = models.CharField(max_length=50, blank=True)
    client_email = models.EmailField(max_length=254, blank=True, null=True)
    staff_in_charge = models.CharField(max_length=100, blank=True)
    
    transport_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    labor_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    miscellaneous_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='event_edits')

    class Meta:
        ordering = ['-start_time']

    @property
    def duration_display(self):
        if not self.start_time or not self.end_time: return ""
        delta = self.end_time - self.start_time
        hours = delta.total_seconds() / 3600
        if hours < 24:
            h_int = int(hours) if hours.is_integer() else round(hours, 1)
            return f"{h_int} Hour{'s' if h_int != 1 else ''}"
        days = math.ceil(hours / 24)
        return f"{days} Day{'s' if days != 1 else ''}"

    @property
    def total_gear_cost(self):
        """OOP Method: Calculates total cost of all gear locked to this event."""
        total = sum(item.total_cost for item in self.manifest.all())
        return total

    @property
    def grand_total_price(self):
        """OOP Method: The final mathematical source of truth for the Invoice."""
        return self.total_gear_cost + self.transport_cost + self.labor_cost + self.miscellaneous_cost

    def __str__(self):
        return f"{self.title} ({self.start_time.date()})"


class EventItem(models.Model):
    """The 'Manifest' - Tracks equipment assigned to an event."""
    
    ITEM_STATUS_CHOICES = [
        ('PENDING', 'Pending Approval'),
        ('APPROVED', 'Approved by Vendor'),
        ('REJECTED', 'Rejected / Unavailable'),
        ('DISPATCHED', 'Scanned Out (Active)'),
        ('RETURNED', 'Scanned In (Completed)'),
    ]
    
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='manifest')
    item = models.ForeignKey('inventory.InventoryItem', on_delete=models.SET_NULL, null=True, blank=True) 
    item_name_snapshot = models.CharField(max_length=200, blank=True)
    
    locked_daily_rate = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    status = models.CharField(max_length=20, choices=ITEM_STATUS_CHOICES, default='PENDING')

    scanned_out_at = models.DateTimeField(null=True, blank=True)
    scanned_in_at = models.DateTimeField(null=True, blank=True)
    handled_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    
    CONDITION_CHOICES = [('GOOD', 'Good'), ('DAMAGED', 'Damaged'), ('LOST', 'Lost')]
    condition_return = models.CharField(max_length=20, default='GOOD', choices=CONDITION_CHOICES)

    def save(self, *args, **kwargs):
        if self.item and not self.item_name_snapshot:
            self.item_name_snapshot = self.item.name
            
        if not self.pk and self.item and hasattr(self.item, 'daily_rate'):
            self.locked_daily_rate = self.item.daily_rate
            
        super().save(*args, **kwargs)

    def clean(self):
        super().clean()
        if hasattr(self, 'event') and self.event and self.item and self.status in ['APPROVED', 'DISPATCHED']:
            overlapping_bookings = EventItem.objects.filter(
                item=self.item,
                status__in=['APPROVED', 'DISPATCHED'],
                event__start_time__lt=self.event.end_time,
                event__end_time__gt=self.event.start_time
            ).exclude(pk=self.pk)

            if overlapping_bookings.exists():
                raise ValidationError(
                    _("CRITICAL OVERLAP: This gear is already booked or active for another gig during this specific time window.")
                )

    @property
    def total_cost(self):
        if self.event.start_time and self.event.end_time:
            delta = self.event.end_time - self.event.start_time
            days = max(1, math.ceil(delta.total_seconds() / 86400))
            return self.locked_daily_rate * days
        return 0

    def __str__(self):
        name = self.item.name if self.item else f"{self.item_name_snapshot} (Deleted)"
        return f"{name} @ {self.event.title}"


# ==========================================
# 2. SMART DOCUMENT & ESCROW ENGINE
# ==========================================

class Document(models.Model):
    DOC_TYPES = [('QUOTE', 'Quotation'), ('INVOICE', 'Invoice'), ('RECEIPT', 'Receipt')]
    STATUS_CHOICES = [('DRAFT', 'Draft'), ('SENT', 'Sent'), ('PAID', 'Paid'), ('PARTIAL', 'Partial')]
    
    # 🚨 STAGE 4: Escrow Tracking Ledger
    ESCROW_STATUS_CHOICES = [
        ('NONE', 'Not in Escrow'),
        ('PENDING', 'Awaiting M-Pesa Auth'),
        ('LOCKED', 'Locked in Vault'),
        ('RELEASED', 'Paid to Vendor'),
        ('DISPUTED', 'In Dispute')
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event = models.ForeignKey(Event, on_delete=models.SET_NULL, null=True, blank=True, related_name='documents')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, help_text="Vendor issuing the doc")
    
    doc_type = models.CharField(max_length=10, choices=DOC_TYPES, default='QUOTE')
    doc_number = models.CharField(max_length=50, unique=True, editable=False)
    
    client_name = models.CharField(max_length=200)
    client_email = models.EmailField(blank=True)
    client_phone = models.CharField(max_length=50, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    issue_date = models.DateField(default=timezone.now)
    due_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='DRAFT')
    
    # Financials
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    amount_paid = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    
    # Stage 4: Fintech Tracking
    escrow_status = models.CharField(max_length=20, choices=ESCROW_STATUS_CHOICES, default='NONE')
    daraja_receipt_number = models.CharField(max_length=50, blank=True, help_text="M-Pesa transaction ID")
    
    notes = models.TextField(blank=True)
    terms = models.TextField(blank=True, default="1. 70% Deposit required.\n2. Balance due on delivery. Protected by Gigs360 Escrow.")

    def save(self, *args, **kwargs):
        if not self.doc_number:
            prefix = self.doc_type[:3].upper() 
            date_str = timezone.now().strftime('%Y%m%d')
            daily_count = Document.objects.filter(user=self.user, created_at__date=timezone.now().date()).count() + 1
            self.doc_number = f"{prefix}-{date_str}-{daily_count:03d}"
        
        if self.amount_paid >= self.total_amount and self.total_amount > 0:
            self.status = 'PAID'
        elif self.amount_paid > 0:
            self.status = 'PARTIAL'
            
        super().save(*args, **kwargs)

    @property
    def balance_due(self):
        return self.total_amount - self.amount_paid

    def __str__(self):
        return f"{self.doc_number} - {self.client_name}"


class LineItem(models.Model):
    document = models.ForeignKey(Document, related_name='items', on_delete=models.CASCADE)
    description = models.CharField(max_length=255) 
    details = models.TextField(blank=True)
    quantity = models.IntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    total_price = models.DecimalField(max_digits=10, decimal_places=2, editable=False)

    class Meta:
        ordering = ['id']

    def save(self, *args, **kwargs):
        self.total_price = self.quantity * self.unit_price
        super().save(*args, **kwargs)