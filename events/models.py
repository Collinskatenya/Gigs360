from django.db import models
from django.conf import settings
from django.utils.http import urlencode

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

    # --- 1. CORE DETAILS & OWNERSHIP ---
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='events',
        help_text="The owner/creator of the event"
    )
    title = models.CharField(max_length=200, help_text="e.g. Katenya & Faith Wedding")
    event_type = models.CharField(max_length=50, choices=EVENT_TYPES, default='OTHER')
    description = models.TextField(blank=True, help_text="Notes on logistics or venue access")
    
    # --- 2. LOGISTICS (Time & Place) ---
    location = models.CharField(max_length=200)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    
    # --- 3. CLIENT & STAFF ---
    client_name = models.CharField(max_length=100, blank=True)
    client_contact = models.CharField(max_length=50, blank=True)
    staff_in_charge = models.CharField(max_length=100, blank=True, help_text="Lead Creative on site")
    
    # --- 4. FINANCIALS (For Audit Report) ---
    transport_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, help_text="Fuel/Uber/Van")
    labor_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, help_text="Crew Payment")
    miscellaneous_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, help_text="Food/Permits")

    # --- 5. SYSTEM STATUS & TRACEABILITY ---
    is_completed = models.BooleanField(default=False, help_text="Mark true when gear is returned")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='event_edits',
        help_text="Last user to edit this event"
    )

    class Meta:
        ordering = ['start_time']

    @property
    def total_expenses(self):
        """Calculates total spend for the audit report."""
        return self.transport_cost + self.labor_cost + self.miscellaneous_cost

    def get_google_calendar_url(self):
        """Generates a dynamic link to add this event to Google Calendar."""
        base_url = "https://www.google.com/calendar/render?action=TEMPLATE"
        params = {
            'text': self.title,
            'dates': f"{self.start_time.strftime('%Y%m%dT%H%M%S')}/{self.end_time.strftime('%Y%m%dT%H%M%S')}",
            'details': f"{self.description} - Client: {self.client_name} ({self.client_contact})",
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
    # Using string reference avoids circular imports with Inventory app
    item = models.ForeignKey('inventory.InventoryItem', on_delete=models.CASCADE)
    
    # --- RAPID SCANNER AUDIT LOGS ---
    scanned_out_at = models.DateTimeField(null=True, blank=True, help_text="Time scanned out via app")
    scanned_in_at = models.DateTimeField(null=True, blank=True, help_text="Time returned via app")
    
    # Traceability
    handled_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Condition Check on Return
    CONDITION_CHOICES = [('GOOD', 'Good'), ('DAMAGED', 'Damaged'), ('LOST', 'Lost')]
    condition_return = models.CharField(max_length=20, default='GOOD', choices=CONDITION_CHOICES)

    def __str__(self):
        return f"{self.item} @ {self.event.title}"