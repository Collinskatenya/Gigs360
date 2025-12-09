from django.db import models
from django.conf import settings
from inventory.models import InventoryItem

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

    # Who owns this event? (The logged-in user)
    planner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    
    # Event Details
    title = models.CharField(max_length=200, help_text="e.g. Katenya & Faith Wedding")
    event_type = models.CharField(max_length=50, choices=EVENT_TYPES)
    location = models.CharField(max_length=200)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    
    # Traceability Details
    client_name = models.CharField(max_length=100)
    client_contact = models.CharField(max_length=15)
    staff_in_charge = models.CharField(max_length=100, help_text="Who is handling the gear?")
    
    # The "Shopping Cart" of items used
    items = models.ManyToManyField(InventoryItem, blank=True, related_name='events')
    
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} ({self.start_date.date()})"