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

    # --- 1. Ownership & Core Details ---
    # Renaming 'user' to 'created_by' makes the code more readable for traceability, 
    # but 'user' works fine if you prefer it. I added 'updated_by' below.
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='events',
        help_text="The owner/creator of the event"
    )
    title = models.CharField(max_length=200, help_text="e.g. Katenya & Faith Wedding")
    event_type = models.CharField(max_length=50, choices=EVENT_TYPES, default='OTHER')
    description = models.TextField(blank=True, help_text="Notes on logistics or venue access")
    
    # --- 2. Time & Location ---
    location = models.CharField(max_length=200)
    # Using 'start_time' matches your snippet (better than 'start_date' for datetime fields)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    
    # --- 3. Client & Staff Traceability ---
    client_name = models.CharField(max_length=100)
    client_contact = models.CharField(max_length=15)
    staff_in_charge = models.CharField(max_length=100, help_text="Who is the Lead Creative on site?")
    
    # --- 4. System Status & Audit Trail (CRITICAL FOR ADMIN) ---
    is_completed = models.BooleanField(default=False, help_text="Mark true when gear is returned")
    
    # Creation Log
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Edit Log (The missing piece! This tracks changes)
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

    def get_google_calendar_url(self):
        """Generates a dynamic link to add this event to Google Calendar"""
        base_url = "https://www.google.com/calendar/render?action=TEMPLATE"
        params = {
            'text': self.title,
            # Formatting time specifically for Google Calendar API
            'dates': f"{self.start_time.strftime('%Y%m%dT%H%M%S')}/{self.end_time.strftime('%Y%m%dT%H%M%S')}",
            'details': f"{self.description} - Client: {self.client_name} ({self.client_contact})",
            'location': self.location,
        }
        return f"{base_url}&{urlencode(params)}"

    def __str__(self):
        return f"{self.title} ({self.start_time.date()})"


class EventItem(models.Model):
    """
    The 'Manifest' - Tracks inventory for ONE event.
    """
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='manifest')
    # Perfect usage of lazy string reference to avoid Circular Import errors
    item = models.ForeignKey('inventory.InventoryItem', on_delete=models.CASCADE)
    
    # Audit Logs
    scanned_out_at = models.DateTimeField(null=True, blank=True, help_text="Time it left the warehouse")
    scanned_in_at = models.DateTimeField(null=True, blank=True, help_text="Time it returned")
    
    # Accountability
    handled_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Return Condition Check
    CONDITION_CHOICES = [('GOOD', 'Good'), ('DAMAGED', 'Damaged'), ('LOST', 'Lost')]
    condition_return = models.CharField(max_length=20, null=True, blank=True, choices=CONDITION_CHOICES)

    def __str__(self):
        # We use 'self.item.name' assuming InventoryItem has a .name field
        return f"{self.item} @ {self.event.title}"