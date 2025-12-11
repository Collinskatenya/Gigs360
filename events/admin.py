from django.contrib import admin
from .models import Event, EventItem

class EventItemInline(admin.TabularInline):
    """
    Allows viewing and adding gear directly inside the Event screen.
    """
    model = EventItem
    extra = 0  # Keeps the interface clean
    
    # TRACEABILITY: Make these read-only so no one can fake the scan times
    readonly_fields = ('scanned_out_at', 'scanned_in_at', 'handled_by', 'condition_return')
    
    # OPTIMIZATION: If you have many inventory items, this adds a search box 
    # instead of a massive dropdown. 
    # (Requires 'search_fields' to be set in your InventoryAdmin)
    autocomplete_fields = ['item'] 

@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    # TRACEABILITY: Added 'updated_by' so you see who touched it last
    list_display = (
        'title', 
        'start_time', 
        'location', 
        'user',          # The Owner/Creator
        'updated_by',    # The Last Editor
        'is_completed'
    )
    
    list_filter = ('is_completed', 'start_time', 'event_type')
    search_fields = ('title', 'location', 'user__username', 'description')
    
    date_hierarchy = 'start_time'
    
    # Connects the gear manifest to this page
    inlines = [EventItemInline]
    
    # TRACEABILITY: Critical Section!
    # These fields are shown but cannot be edited by anyone, even Super Admins.
    readonly_fields = ('created_at', 'updated_at', 'updated_by')

    # Organized Layout
    fieldsets = (
        ('Event Details', {
            'fields': ('title', 'event_type', 'description', 'location')
        }),
        ('Schedule', {
            'fields': ('start_time', 'end_time')
        }),
        ('Client & Staff', {
            'fields': ('client_name', 'client_contact', 'staff_in_charge')
        }),
        ('Status', {
            'fields': ('user', 'is_completed')
        }),
        ('Audit Trail (System Data)', {
            'fields': ('created_at', 'updated_at', 'updated_by'),
            'classes': ('collapse',), # Collapsed to save space
        }),
    )

    actions = ['mark_as_completed']

    def mark_as_completed(self, request, queryset):
        # Update the boolean and set the updater to the admin performing the action
        queryset.update(is_completed=True)
        # Note: queryset.update() doesn't trigger save() signals, 
        # so updated_by won't auto-update here unless you loop through them.
        # For bulk actions, this is usually acceptable.
    mark_as_completed.short_description = "Mark selected events as Completed"