from django.db import models
from django.conf import settings
from django.utils import timezone
import uuid
import qrcode
from io import BytesIO
from django.core.files import File
from PIL import Image

class Category(models.Model):
    """
    Groups items: Cameras, Lighting, Audio, Furniture, Decor.
    """
    name = models.CharField(max_length=100)
    icon = models.CharField(max_length=50, default='bi-box', help_text="Bootstrap Icon class")
    
    class Meta:
        verbose_name_plural = "Categories"

    def __str__(self):
        return self.name

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
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='inventory')
    
    name = models.CharField(max_length=200, help_text="e.g. Sony A7S III Body")
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True)
    
    tracking_type = models.CharField(max_length=20, choices=TRACKING_TYPES, default='UNIQUE')
    
    # 3. TRACEABILITY (Specific Details)
    serial_number = models.CharField(max_length=100, blank=True, null=True, help_text="Manufacturer S/N")
    asset_tag = models.CharField(max_length=50, blank=True, null=True, help_text="Internal ID (e.g. CAM-01)")
    color = models.CharField(max_length=50, blank=True, null=True, help_text="e.g. Matte Black")
    weight = models.CharField(max_length=50, blank=True, null=True, help_text="e.g. 2.5kg")
    condition = models.CharField(max_length=20, choices=CONDITION_CHOICES, default='GOOD')

    # 4. QUANTITY & STATE
    quantity = models.PositiveIntegerField(default=1, help_text="For Serialized, this is always 1.")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='AVAILABLE')

    # 5. FINANCIALS
    daily_rate = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Rental Price per Day")
    replacement_value = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    # 6. DETAILS
    description = models.TextField(blank=True, null=True, help_text="Condition notes, specs...")

    # 7. MEDIA & ASSETS
    image = models.ImageField(upload_to='inventory_photos/', blank=True, null=True)
    qr_code = models.ImageField(upload_to='qr_codes/', blank=True, null=True)
    
    # 8. AUDIT TRAIL (For Event Tracking)
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

    def save(self, *args, **kwargs):
        # Auto-Generate QR Code if it doesn't exist
        if not self.qr_code:
            # QR Content: Direct link to the scan page for this item
            # Example: https://gigs360.co.ke/scan/<UUID>/
            qr_content = f"https://gigs360.co.ke/scan/{self.id}/"
            
            try:
                # Generate QR Object
                qr = qrcode.QRCode(
                    version=1,
                    error_correction=qrcode.constants.ERROR_CORRECT_H, # High error correction
                    box_size=10,
                    border=4,
                )
                qr.add_data(qr_content)
                qr.make(fit=True)

                # Create Image from QR
                img = qr.make_image(fill_color="black", back_color="white").convert('RGB')

                # Save to BytesIO Buffer
                buffer = BytesIO()
                img.save(buffer, format="PNG")
                
                # Create a clean, unique filename
                safe_name = "".join([c for c in self.name if c.isalnum()])[:15]
                filename = f"qr_{safe_name}_{str(self.id)[:8]}.png"
                
                # Save to the ImageField
                self.qr_code.save(filename, File(buffer), save=False)
            
            except Exception as e:
                print(f"Error generating QR code for {self.name}: {e}")
                # We continue saving the item even if QR fails, to prevent data loss
                
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.serial_number or 'Bulk'})"