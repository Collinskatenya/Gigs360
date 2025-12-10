from django.contrib import admin
from .models import Event, EventItem

class EventItemInline(admin.TabularInline):
    """
    Allows viewing and adding gear directly inside the Event screen.
    """
    model = EventItem
    extra = 0  # Don't show extra empty rows to keep it clean
    
    # Read-only fields ensure Admins don't accidentally fake audit logs
    readonly_fields = ('scanned_out_at', 'scanned_in_at', 'handled_by')
    
    # If you have 1000s of items, this makes selecting them faster
    # (Requires search_fields to be set in InventoryAdmin)
    autocomplete_fields = ['item'] 

@admin.register(Event)
class EventAdmin(admin.ModelAdmin):  # <--- FIXED: Removed '.site'
    list_display = (
        'title', 
        'start_time', 
        'end_time', 
        'location', 
        'user', 
        'is_completed'
    )
    
    list_filter = ('is_completed', 'start_time')
    search_fields = ('title', 'location', 'user__username', 'description')
    
    # Shows the date navigation bar at the top
    date_hierarchy = 'start_time'
    
    # Connects the gear list to this page
    inlines = [EventItemInline]
    
    actions = ['mark_as_completed']

    def mark_as_completed(self, request, queryset):
        queryset.update(is_completed=True)
    mark_as_completed.short_description = "Mark selected events as Completed"