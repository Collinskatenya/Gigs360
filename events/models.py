from django.db import models
from django.conf import settings
from django.utils.http import urlencode
from django.utils import timezone
import uuid
import math

# ==========================================
# 1. EVENT OPERATIONS
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

    # --- CORE DETAILS ---
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='events'
    )
    title = models.CharField(max_length=200, help_text="e.g. Katenya & Faith Wedding")
    event_type = models.CharField(max_length=50, choices=EVENT_TYPES, default='OTHER')
    description = models.TextField(blank=True, help_text="Notes on logistics or venue access")
    
    # --- LOGISTICS ---
    location = models.CharField(max_length=200)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    
    # --- CLIENT & STAFF ---
    client_name = models.CharField(max_length=100, blank=True)
    client_contact = models.CharField(max_length=50, blank=True)
    client_email = models.EmailField(max_length=254, blank=True, null=True, help_text="Used for auto-filling invoices")
    staff_in_charge = models.CharField(max_length=100, blank=True, help_text="Lead Creative on site")
    
    # --- FINANCIALS (Internal Costs) ---
    transport_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    labor_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    miscellaneous_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    # --- STATUS ---
    is_completed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, null=True, blank=True, 
        related_name='event_edits'
    )

    class Meta:
        ordering = ['start_time']

    # --- SMART DURATION DISPLAY ---
    @property
    def duration_display(self):
        """Returns a formatted string like '4 Hours' or '3 Days'."""
        if not self.start_time or not self.end_time:
            return ""
        
        delta = self.end_time - self.start_time
        total_seconds = delta.total_seconds()
        hours = total_seconds / 3600
        
        if hours < 24:
            h_int = int(hours) if hours.is_integer() else round(hours, 1)
            label = "Hour" if h_int == 1 else "Hours"
            return f"{h_int} {label}"
        else:
            # Round up: 25 hours counts as 2 days rental
            days = math.ceil(hours / 24)
            label = "Day" if days == 1 else "Days"
            return f"{days} {label}"

    @property
    def total_expenses(self):
        return self.transport_cost + self.labor_cost + self.miscellaneous_cost

    def get_google_calendar_url(self):
        base_url = "https://www.google.com/calendar/render?action=TEMPLATE"
        start_str = self.start_time.strftime('%Y%m%dT%H%M%S')
        end_str = self.end_time.strftime('%Y%m%dT%H%M%S')
        params = {
            'text': self.title,
            'dates': f"{start_str}/{end_str}",
            'details': f"{self.description} - Client: {self.client_name}",
            'location': self.location,
        }
        return f"{base_url}&{urlencode(params)}"

    def __str__(self):
        return f"{self.title} ({self.start_time.date()})"


class EventItem(models.Model):
    """
    The 'Manifest' - Tracks specific inventory items for ONE event.
    """
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='manifest')
    
    # --- TASK 2: HISTORY WIPE FIX ---
    # OLD: on_delete=models.CASCADE (Bad - deletes log if camera is deleted)
    # NEW: on_delete=models.SET_NULL (Good - keeps log, sets item ID to None)
    item = models.ForeignKey(
        'inventory.InventoryItem', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True
    ) 
    
    # SNAPSHOT: We freeze the item name here. If the Item ID is deleted later, 
    # we still know this event used a "Sony A7III".
    item_name_snapshot = models.CharField(max_length=200, blank=True, help_text="Preserves item name if original item is deleted")

    # Audit Logs
    scanned_out_at = models.DateTimeField(null=True, blank=True)
    scanned_in_at = models.DateTimeField(null=True, blank=True)
    handled_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    
    CONDITION_CHOICES = [('GOOD', 'Good'), ('DAMAGED', 'Damaged'), ('LOST', 'Lost')]
    condition_return = models.CharField(max_length=20, default='GOOD', choices=CONDITION_CHOICES)

    def save(self, *args, **kwargs):
        # Auto-Freeze the name when creating the link
        if self.item and not self.item_name_snapshot:
            self.item_name_snapshot = self.item.name
        super().save(*args, **kwargs)

    def __str__(self):
        # Return snapshot name if the actual item object is deleted
        name = self.item.name if self.item else f"{self.item_name_snapshot} (Deleted)"
        return f"{name} @ {self.event.title}"


# ==========================================
# 2. SMART DOCUMENT ENGINE (Invoices & Quotes)
# ==========================================

class Document(models.Model):
    """Stores Quotes, Invoices, and Receipts."""
    DOC_TYPES = [
        ('QUOTE', 'Quotation'),
        ('INVOICE', 'Invoice'),
        ('RECEIPT', 'Payment Receipt'),
        ('CONTRACT', 'Contract / Agreement'),
    ]
    
    STATUS_CHOICES = [
        ('DRAFT', 'Draft'),
        ('SENT', 'Sent'),
        ('PAID', 'Paid'),
        ('PARTIAL', 'Partially Paid'),
        ('OVERDUE', 'Overdue'),
        ('ACCEPTED', 'Accepted'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # History Protection: Keep invoice even if event is deleted
    event = models.ForeignKey(Event, on_delete=models.SET_NULL, null=True, blank=True, related_name='documents')
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    
    doc_type = models.CharField(max_length=10, choices=DOC_TYPES, default='QUOTE')
    doc_number = models.CharField(max_length=50, unique=True, editable=False)
    
    # Client Snapshot 
    client_name = models.CharField(max_length=200)
    client_email = models.EmailField(blank=True)
    client_phone = models.CharField(max_length=50, blank=True)
    
    # Dates
    created_at = models.DateTimeField(auto_now_add=True)
    issue_date = models.DateField(default=timezone.now)
    due_date = models.DateField(null=True, blank=True)
    
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='DRAFT')
    
    # Financials
    currency = models.CharField(max_length=3, default='KES')
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    tax_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    discount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    
    # Payment Tracking
    amount_paid = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    deposit_percentage = models.IntegerField(default=50, help_text="e.g. 70 for 70% deposit required")
    
    # Smart Terms 
    notes = models.TextField(blank=True, help_text="Bank details, M-Pesa numbers, etc.")
    terms = models.TextField(blank=True, default="1. 70% Deposit required to secure booking.\n2. Balance due on delivery.")

    def save(self, *args, **kwargs):
        # Auto-Generate Number: QT-20251004-001 or INV-20251004-001
        if not self.doc_number:
            prefix = self.doc_type[:2] 
            today = timezone.now().strftime('%Y%m%d')
            count = Document.objects.filter(created_at__date=timezone.now().date()).count() + 1
            self.doc_number = f"{prefix}-{today}-{count:03d}"
        
        # Auto-Update Status
        if self.amount_paid >= self.total_amount and self.total_amount > 0:
            self.status = 'PAID'
        elif self.amount_paid > 0:
            self.status = 'PARTIAL'
            
        super().save(*args, **kwargs)

    @property
    def balance_due(self):
        return self.total_amount - self.amount_paid

    def __str__(self):
        return f"{self.get_doc_type_display()} #{self.doc_number} - {self.client_name}"


class LineItem(models.Model):
    """Represents rows in the Invoice/Quote."""
    document = models.ForeignKey(Document, related_name='items', on_delete=models.CASCADE)
    description = models.CharField(max_length=255) 
    details = models.TextField(blank=True, help_text="Bullet points of what is included")
    quantity = models.IntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    total_price = models.DecimalField(max_digits=10, decimal_places=2, editable=False)

    def save(self, *args, **kwargs):
        self.total_price = self.quantity * self.unit_price
        super().save(*args, **kwargs)