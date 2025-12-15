from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver
from django.urls import reverse
from django.contrib.auth import get_user_model
from events.models import Event, Document, EventItem
from inventory.models import InventoryItem
from .models import Notification

User = get_user_model()

# ==========================================
# 1. AUTH & PROFILE ALERTS (Security)
# ==========================================

@receiver(pre_save, sender=User)
def capture_user_changes(sender, instance, **kwargs):
    """
    Captures the old state of the user before saving (to detect sensitive changes).
    """
    if instance.pk:
        try:
            old_user = User.objects.get(pk=instance.pk)
            instance._old_username = old_user.username
            instance._old_email = old_user.email
        except User.DoesNotExist:
            pass

@receiver(post_save, sender=User)
def notify_profile_update(sender, instance, created, **kwargs):
    """
    Notify user when critical profile details change (Security Best Practice).
    """
    if not created and instance.pk:
        changes = []
        # Check if username changed
        if hasattr(instance, '_old_username') and instance.username != instance._old_username:
            changes.append("Username")
        # Check if email changed
        if hasattr(instance, '_old_email') and instance.email != instance._old_email:
            changes.append("Email")
            
        if changes:
            Notification.objects.create(
                user=instance,
                title="Security Alert",
                message=f"Your {', '.join(changes)} was updated successfully.",
                link=reverse('settings'),
                notification_type='warning'
            )

# ==========================================
# 2. INVENTORY OPERATIONS (Gear Locker)
# ==========================================

@receiver(post_save, sender=InventoryItem)
def notify_inventory_change(sender, instance, created, **kwargs):
    """
    Triggered when Gear is Added or Edited.
    """
    action = "Added" if created else "Updated"
    # Use 'inventory:item_detail' to match your urls.py namespace
    try:
        link = reverse('inventory:item_detail', args=[instance.id])
    except:
        link = "#"

    Notification.objects.create(
        user=instance.owner,
        title=f"Gear {action}",
        message=f"Item '{instance.name}' has been {action.lower()} in your locker.",
        link=link,
        notification_type='success' if created else 'info'
    )

@receiver(post_delete, sender=InventoryItem)
def notify_inventory_delete(sender, instance, **kwargs):
    """
    Triggered when Gear is Deleted.
    """
    Notification.objects.create(
        user=instance.owner,
        title="Gear Deleted",
        message=f"Item '{instance.name}' was permanently removed from inventory.",
        notification_type='error' # Red alert, no link prevents 404
    )

# ==========================================
# 3. EVENT & SCANNING OPS
# ==========================================

@receiver(post_save, sender=Event)
def notify_event_creation(sender, instance, created, **kwargs):
    """
    Triggered when a new Gig is created.
    """
    if created:
        Notification.objects.create(
            user=instance.user,
            title="New Gig Scheduled",
            message=f"Event '{instance.title}' is set for {instance.start_time.strftime('%b %d')}.",
            link=reverse('update_event', args=[instance.id]),
            notification_type='success'
        )

@receiver(post_save, sender=EventItem)
def notify_manifest_update(sender, instance, created, **kwargs):
    """
    Triggered when items are Scanned In/Out or added to a list.
    """
    # If not created, it implies an update (like scanning status change)
    if not created:
        status_msg = "updated"
        
        # Logic to guess the action based on timestamps
        if instance.scanned_out_at and not instance.scanned_in_at:
            status_msg = "scanned OUT"
        elif instance.scanned_in_at:
            status_msg = "scanned IN (Returned)"

        Notification.objects.create(
            user=instance.event.user,
            title="Manifest Update",
            message=f"Gear '{instance.item.name}' was {status_msg} for '{instance.event.title}'.",
            link=reverse('event_report', args=[instance.event.id]),
            notification_type='info'
        )

# ==========================================
# 4. INVOICING & DOCUMENTS
# ==========================================

@receiver(post_save, sender=Document)
def notify_invoice_creation(sender, instance, created, **kwargs):
    """
    Triggered when a Quote or Invoice is generated.
    """
    if created:
        doc_type = instance.get_doc_type_display()
        Notification.objects.create(
            user=instance.user,
            title=f"{doc_type} Ready",
            message=f"{doc_type} #{instance.doc_number} for {instance.client_name} is ready for download.",
            link=reverse('generate_pdf', args=[instance.id]),
            notification_type='success'
        )