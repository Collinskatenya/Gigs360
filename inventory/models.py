from django.db import models
from django.conf import settings
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
        ('RENTED', 'Rented Out'),
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
    
    # 3. TRACEABILITY (New Fields you requested)
    serial_number = models.CharField(max_length=100, blank=True, null=True, help_text="Manufacturer S/N")
    asset_tag = models.CharField(max_length=50, blank=True, null=True, help_text="Internal ID (e.g. CAM-01)")
    color = models.CharField(max_length=50, blank=True, null=True, help_text="e.g. Matte Black")
    weight = models.CharField(max_length=50, blank=True, null=True, help_text="e.g. 2.5kg")
    condition = models.CharField(max_length=20, choices=CONDITION_CHOICES, default='GOOD')

    # 4. QUANTITY & STATE
    quantity = models.PositiveIntegerField(default=1, help_text="For Serialized, this is always 1.")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='AVAILABLE')

    # 5. FINANCIALS (Made Optional for Freelancers/Agencies)
    daily_rate = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Rental Price per Day")
    replacement_value = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    # 6. DETAILS
    description = models.TextField(blank=True, null=True, help_text="Condition notes, specs...")

    # 7. MEDIA & ASSETS
    image = models.ImageField(upload_to='inventory_photos/', blank=True, null=True)
    qr_code = models.ImageField(upload_to='qr_codes/', blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        # Auto-Generate QR Code on Save
        if not self.qr_code:
            # QR Data contains ID, Serial, and Owner for secure tracking
            qr_data = f"GIGS360|ID:{self.id}|SN:{self.serial_number}|OWNER:{self.owner.username}"
            try:
                qr_img = qrcode.make(qr_data)
                canvas = Image.new('RGB', (350, 350), 'white')
                canvas.paste(qr_img)
                
                buffer = BytesIO()
                canvas.save(buffer, 'PNG')
                
                # Create filename
                clean_name = self.name.replace(' ', '_')[:10]
                fname = f'qr_{clean_name}_{self.id}.png'
                
                self.qr_code.save(fname, File(buffer), save=False)
            except Exception as e:
                print(f"Error generating QR code: {e}")
                
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.serial_number or 'Bulk'})"