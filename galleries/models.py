import uuid
from django.db import models
from django.conf import settings
from django.utils.text import slugify
from django.utils.crypto import get_random_string

# ==========================================
# GIGS360 HYBRID CLIENT DELIVERY OS 
# ==========================================

class Gallery(models.Model):
    """
    The master container for media delivery.
    Can operate standalone (Pixieset mode) OR be tied to an Event (Escrow mode).
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # --- RELATIONS ---
    photographer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='galleries')
    # OPTIONAL: Link to an event to trigger Escrow Locks
    event = models.ForeignKey('events.Event', on_delete=models.SET_NULL, null=True, blank=True, related_name='galleries', help_text="Optional: Link to an event for Invoice/Escrow locking")
    
    # --- DETAILS ---
    title = models.CharField(max_length=200, help_text="e.g., The Smith Wedding")
    slug = models.SlugField(unique=True, blank=True, max_length=250)
    event_date = models.DateField(blank=True, null=True)
    cover_image = models.ImageField(upload_to='gallery_covers/', blank=True, null=True)
    
    # --- SECURITY & ACCESS ---
    client_email = models.EmailField(blank=True, null=True)
    access_pin = models.CharField(max_length=6, blank=True, null=True, help_text="Optional 6-digit PIN")
    is_published = models.BooleanField(default=False, help_text="If false, clients cannot see the gallery link at all.")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = "Galleries"

    def save(self, *args, **kwargs):
        # 1. Generate unguessable URL slug
        if not self.slug:
            base_slug = slugify(self.title)
            uuid_segment = str(self.id).split('-')[0]
            self.slug = f"{base_slug}-{uuid_segment}"
            
        # 2. Auto-generate PIN if left blank
        if not self.access_pin:
            self.access_pin = get_random_string(6, allowed_chars='ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789')
            
        super().save(*args, **kwargs)

    @property
    def is_escrow_unlocked(self):
        """
        🚨 THE MASTER LOCK: If linked to an event, checks if the invoice is paid.
        If NO event is linked, it defaults to True (Pixieset mode).
        """
        if not self.event:
            return True # Standalone mode: Always unlocked
            
        invoice = self.event.documents.filter(doc_type='INVOICE').first()
        if not invoice:
            return False 
            
        return invoice.status == 'PAID' and invoice.escrow_status in ['LOCKED', 'RELEASED']

    def __str__(self):
        return f"{self.title} by {self.photographer.username}"


class Photo(models.Model):
    """
    Individual media files stored securely in AWS S3.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    gallery = models.ForeignKey(Gallery, on_delete=models.CASCADE, related_name='photos')
    
    # The original, heavy file (Routed to AWS S3)
    image = models.ImageField(upload_to='galleries/high_res/')
    
    # The compressed, watermarked version
    watermarked_file = models.ImageField(upload_to='galleries/watermarked/', blank=True, null=True)
    
    # Metadata for the 3GB SaaS Tracker
    original_filename = models.CharField(max_length=255, blank=True)
    file_size = models.IntegerField(default=0)
    
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['uploaded_at']

    def __str__(self):
        return self.original_filename or f"Photo {self.id}"


# 🚨 RESTORED: THE TELEMETRY ENGINE 🚨
class GalleryActivity(models.Model):
    """
    Tracks every interaction with a gallery for the Command Center.
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
    actor = models.CharField(max_length=100) # e.g., "Client (IP Address)"
    details = models.CharField(max_length=255, blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']
        verbose_name_plural = "Gallery Activities"

    def __str__(self):
        return f"{self.actor} {self.get_action_type_display()}"