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

    # 1. Ownership & Core Details
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='events')
    title = models.CharField(max_length=200, help_text="e.g. Katenya & Faith Wedding")
    event_type = models.CharField(max_length=50, choices=EVENT_TYPES, default='OTHER')
    description = models.TextField(blank=True, help_text="Notes on logistics or venue access")
    
    # 2. Time & Location
    location = models.CharField(max_length=200)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    
    # 3. Client & Staff Traceability
    client_name = models.CharField(max_length=100)
    client_contact = models.CharField(max_length=15)
    staff_in_charge = models.CharField(max_length=100, help_text="Who is the Lead Creative on site?")
    
    # 4. System Status
    is_completed = models.BooleanField(default=False, help_text="Mark true when gear is returned and job is done")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['start_time']

    def get_google_calendar_url(self):
        """Generates a dynamic link to add this event to Google Calendar"""
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
    The 'Manifest' - Tracks the specific lifecycle of an item for ONE event.
    This replaces the simple ManyToManyField to allow for Audit Trails.
    """
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='manifest')
    # Using string reference to avoid circular imports with Inventory app
    item = models.ForeignKey('inventory.InventoryItem', on_delete=models.CASCADE)
    
    # Audit Logs (The 'Black Box' Data)
    scanned_out_at = models.DateTimeField(null=True, blank=True, help_text="Time it left the warehouse")
    scanned_in_at = models.DateTimeField(null=True, blank=True, help_text="Time it returned")
    
    # Accountability
    handled_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Return Condition Check
    CONDITION_CHOICES = [('GOOD', 'Good'), ('DAMAGED', 'Damaged'), ('LOST', 'Lost')]
    condition_return = models.CharField(max_length=20, null=True, blank=True, choices=CONDITION_CHOICES)

    def __str__(self):
        return f"{self.item.name} @ {self.event.title}"