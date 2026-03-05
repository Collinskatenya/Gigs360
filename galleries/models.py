from django.db import models
from django.conf import settings
from django.utils.crypto import get_random_string
import uuid

# ==========================================
# GIGS360 CLIENT DELIVERY OS (STAGE 5)
# ==========================================

class Gallery(models.Model):
    """
    The master container for a client's media delivery.
    Tied directly to an Event and protected by the Escrow Ledger.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # --- RELATIONS ---
    vendor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='galleries')
    event = models.OneToOneField('events.Event', on_delete=models.CASCADE, related_name='gallery', help_text="The gig this media belongs to")
    
    # --- DETAILS ---
    name = models.CharField(max_length=200, help_text="e.g., Sam & Ruth Wedding Highlights")
    cover_image = models.ImageField(upload_to='gallery_covers/', blank=True, null=True)
    
    # --- SECURITY & ACCESS ---
    access_pin = models.CharField(max_length=6, editable=False, db_index=True)
    is_published = models.BooleanField(default=False, help_text="If false, clients cannot see the gallery link at all.")
    
    # --- STORAGE TRACKING (For SaaS Limits) ---
    total_size_bytes = models.BigIntegerField(default=0, help_text="Tracks total S3 usage for this gallery")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = "Galleries"

    def save(self, *args, **kwargs):
        # Auto-generate a secure 6-character alphanumeric PIN on creation
        if not self.access_pin:
            self.access_pin = get_random_string(6, allowed_chars='ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789')
        super().save(*args, **kwargs)

    @property
    def is_escrow_unlocked(self):
        """
        🚨 THE MASTER LOCK: Checks the financial ledger before allowing high-res downloads.
        Finds the primary invoice linked to this event and verifies if it is fully paid.
        """
        # Look for the main invoice tied to this event
        invoice = self.event.documents.filter(doc_type='INVOICE').first()
        if not invoice:
            return False # Lock down if no invoice exists
        
        # Return True ONLY if the invoice is paid and funds are in the vault (or released)
        return invoice.status == 'PAID' and invoice.escrow_status in ['LOCKED', 'RELEASED']

    def __str__(self):
        return f"{self.name} ({self.event.title})"


class Photo(models.Model):
    """
    Individual media files stored securely in AWS S3.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    gallery = models.ForeignKey(Gallery, on_delete=models.CASCADE, related_name='photos')
    
    # The original, heavy file (Locked by Escrow)
    high_res_file = models.ImageField(upload_to='galleries/high_res/')
    
    # The compressed, heavily watermarked version (Always visible to client)
    watermarked_file = models.ImageField(upload_to='galleries/watermarked/', blank=True, null=True)
    
    file_size_bytes = models.IntegerField(default=0)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['uploaded_at']

    def __str__(self):
        return f"Photo {self.id} for {self.gallery.name}"


# 🚨 NEW: THE TELEMETRY ENGINE 🚨
class GalleryActivity(models.Model):
    """
    TELEMETRY ENGINE: Tracks every interaction with a gallery for the Command Center.
    """
    ACTION_TYPES = [
        ('CREATED', 'Gallery Created'),
        ('PIN_CHANGED', 'Security PIN Changed'),
        ('VIEWED', 'Client Unlocked Gallery'),
        ('DOWNLOADED', 'High-Res Photo Downloaded'),
        ('SHARED', 'Gallery Link Shared'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    gallery = models.ForeignKey(Gallery, on_delete=models.CASCADE, related_name='activities')
    
    action_type = models.CharField(max_length=20, choices=ACTION_TYPES)
    
    # Who did it? (Could be the Vendor's name, or "Client (IP Address)")
    actor = models.CharField(max_length=100) 
    
    # Extra context (e.g., "Downloaded photo_v2.jpg" or "PIN changed to XXXXXX")
    details = models.CharField(max_length=255, blank=True, null=True)
    
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp'] # Newest activity first
        verbose_name_plural = "Gallery Activities"

    def __str__(self):
        return f"{self.actor} {self.get_action_type_display()} at {self.timestamp.strftime('%H:%M')}"