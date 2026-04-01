from django.db import models
from django.conf import settings
from django.utils import timezone
from django.utils.text import slugify
from django.core.files.base import ContentFile
import uuid
import qrcode
from io import BytesIO
from PIL import Image

# ==========================================
# 1. GEAR CATEGORIES
# ==========================================

class Category(models.Model):
    """
    Groups items: Cameras, Lighting, Audio, Furniture, Decor.
    """
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=120, unique=True, blank=True) # 🚨 Added for SEO URLs
    icon = models.CharField(max_length=50, default='bi-box', help_text="Bootstrap Icon class")
    
    class Meta:
        verbose_name_plural = "Categories"
        ordering = ['name']

    def save(self, *args, **kwargs):
        # 🚨 FIX: Prevent database crash on duplicate category names
        if not self.slug:
            base_slug = slugify(self.name)
            short_uid = str(uuid.uuid4())[:6]
            self.slug = f"{base_slug}-{short_uid}"
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

# ==========================================
# 2. THE MASTER INVENTORY ENGINE
# ==========================================

class InventoryItem(models.Model):
    # 1. TRACKING LOGIC
    TRACKING_TYPES = [
        ('UNIQUE', 'Unique (Serialized)'), 
        ('BULK', 'Bulk (Non-Serialized)'),
        ('CONSUMABLE', 'Sale Item (Gaffer Tape, Batteries)'),
    ]
    
    STATUS_CHOICES = [
        ('AVAILABLE', 'Available'),
        ('RENTED', 'On Job / Rented'),
        ('MAINTENANCE', 'In Repair'),
        ('LOST', 'Lost/Stolen'),
        ('SOLD', 'Sold/Consumed'),
    ]

    CONDITION_CHOICES = [
        ('GOOD', 'Good Condition'),
        ('FAIR', 'Fair / Scratched'),
        ('DAMAGED', 'Damaged / Needs Repair'),
        ('LOST', 'Lost / Stolen'),
    ]

    # 2. IDENTIFICATION
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # 🚨 SEO SLUG: For beautiful public marketplace links
    slug = models.SlugField(max_length=255, unique=True, blank=True)
    
    # SECURE QR ID: For public verification links (separates DB ID from public access)
    qr_code_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='inventory')
    name = models.CharField(max_length=200, help_text="e.g. Sony A7S III Body")
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True)
    tracking_type = models.CharField(max_length=20, choices=TRACKING_TYPES, default='UNIQUE')
    
    # 3. PUBLIC MARKETPLACE (Phase 3 Discovery Hub)
    is_published = models.BooleanField(default=True, help_text="Show on the public Discovery Hub?")
    search_location = models.CharField(max_length=100, blank=True, null=True, help_text="City for Global Search Engine")

    # 4. TRACEABILITY
    serial_number = models.CharField(max_length=100, blank=True, null=True, help_text="Manufacturer S/N")
    asset_tag = models.CharField(max_length=50, blank=True, null=True, help_text="Internal ID (e.g. CAM-01)")
    color = models.CharField(max_length=50, blank=True, null=True)
    weight = models.CharField(max_length=50, blank=True, null=True)
    condition = models.CharField(max_length=20, choices=CONDITION_CHOICES, default='GOOD')

    # 5. QUANTITY & STATE
    quantity = models.PositiveIntegerField(default=1, help_text="For UNIQUE items, this should be 1.")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='AVAILABLE')

    # 6. FINANCIALS
    daily_rate = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Rental Price per Day")
    replacement_value = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    # 7. DETAILS
    description = models.TextField(blank=True, null=True)

    # 8. MEDIA & ASSETS (Primary cover image)
    image = models.ImageField(upload_to='inventory_photos/', blank=True, null=True)
    qr_code = models.ImageField(upload_to='qr_codes/', blank=True, null=True)
    
    # 9. AUDIT TRAIL
    last_scanned_at = models.DateTimeField(null=True, blank=True)
    last_scanned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='scanned_items'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        # 🚨 Auto-Generate SEO Slug
        if not self.slug:
            base_slug = slugify(self.name)
            uid_str = str(self.id).split('-')[0]
            self.slug = f"{base_slug}-{uid_str}"

        # Auto-Generate QR Code if it doesn't exist
        if not self.qr_code:
            base_url = getattr(settings, 'SITE_URL', 'http://127.0.0.1:8000')
            qr_content = f"{base_url}/inventory/verify/{self.qr_code_id}/"
            
            try:
                qr = qrcode.QRCode(
                    version=1,
                    error_correction=qrcode.constants.ERROR_CORRECT_H,
                    box_size=10,
                    border=4,
                )
                qr.add_data(qr_content)
                qr.make(fit=True)

                img = qr.make_image(fill_color="black", back_color="white").convert('RGB')
                buffer = BytesIO()
                img.save(buffer, format="PNG")
                
                safe_name = "".join([c for c in self.name if c.isalnum()])[:15]
                filename = f"qr_{safe_name}_{str(self.id)[:8]}.png"
                
                self.qr_code.save(filename, ContentFile(buffer.getvalue()), save=False)
            
            except Exception as e:
                print(f"Error generating QR code for {self.name}: {e}")
                
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.serial_number or 'Bulk'})"


# ==========================================
# 3. DYNAMIC ASSET SHOWROOMS (Phase 3)
# ==========================================

class ItemImage(models.Model):
    """
    Allows vendors to upload multiple angles/photos for a single piece of gear,
    creating a premium marketplace showroom experience.
    """
    item = models.ForeignKey(InventoryItem, on_delete=models.CASCADE, related_name='gallery_images')
    image = models.ImageField(upload_to='inventory_gallery/')
    is_primary = models.BooleanField(default=False, help_text="Use as the main thumbnail?")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-is_primary', '-created_at']

    def __str__(self):
        return f"Gallery Image for {self.item.name}"