from django.contrib import admin
from .models import Event, EventItem, Document, LineItem

# ==========================================
# 1. EVENT CONFIGURATION
# ==========================================

class EventItemInline(admin.TabularInline):
    """
    The Gear Manifest: Tracks items assigned to this event.
    """
    model = EventItem
    extra = 0  # Keeps the interface clean
    
    # TRACEABILITY: Make these read-only so no one can fake the scan times manually
    readonly_fields = ('scanned_out_at', 'scanned_in_at', 'handled_by', 'condition_return')
    
    # OPTIMIZATION: Adds a search box instead of a massive dropdown.
    # Note: Ensure 'search_fields' is set in your InventoryItemAdmin.
    autocomplete_fields = ['item'] 

class DocumentInline(admin.TabularInline):
    """
    Shows linked Quotes/Invoices directly inside the Event screen.
    """
    model = Document
    extra = 0
    fields = ('doc_number', 'doc_type', 'status', 'total_amount', 'amount_paid')
    readonly_fields = ('doc_number', 'total_amount')
    show_change_link = True # Allows you to click "Edit" to go to the full Invoice screen

@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    # TRACEABILITY: 'updated_by' shows who touched it last
    list_display = (
        'title', 
        'start_time', 
        'location', 
        'user',          # The Owner/Creator
        'updated_by',    # The Last Editor
        'is_completed',
        'total_expenses_display'
    )
    
    list_filter = ('is_completed', 'start_time', 'event_type')
    search_fields = ('title', 'location', 'user__username', 'description', 'client_name')
    
    date_hierarchy = 'start_time'
    
    # Connects Gear Manifest AND Invoices to this page
    inlines = [EventItemInline, DocumentInline]
    
    # TRACEABILITY: Critical Section!
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
        ('Financials (Internal)', {
            'fields': ('transport_cost', 'labor_cost', 'miscellaneous_cost'),
            'classes': ('collapse',),
        }),
        ('Status', {
            'fields': ('user', 'is_completed')
        }),
        ('Audit Trail', {
            'fields': ('created_at', 'updated_at', 'updated_by'),
            'classes': ('collapse',),
        }),
    )

    actions = ['mark_as_completed']

    def mark_as_completed(self, request, queryset):
        queryset.update(is_completed=True)
    mark_as_completed.short_description = "Mark selected events as Completed"

    def total_expenses_display(self, obj):
        return f"KES {obj.total_expenses}"
    total_expenses_display.short_description = "Cost"

    # --- AUTO-SAVE USER LOGIC ---
    def save_model(self, request, obj, form, change):
        if not change:  # If creating a new event
            obj.user = request.user
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)


# ==========================================
# 2. SMART DOCUMENT CONFIGURATION (Invoices)
# ==========================================

class LineItemInline(admin.TabularInline):
    """
    Allows adding rows (Packages, Services) to an Invoice.
    """
    model = LineItem
    extra = 1
    fields = ('description', 'details', 'quantity', 'unit_price', 'total_price')
    readonly_fields = ('total_price',) # Calculated automatically

@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ('doc_number', 'doc_type', 'client_name', 'event', 'total_amount', 'status', 'issue_date')
    list_filter = ('doc_type', 'status', 'created_at')
    search_fields = ('doc_number', 'client_name', 'client_email')
    
    # Connects line items (rows) to the Invoice
    inlines = [LineItemInline]
    
    fieldsets = (
        ('Document Details', {
            'fields': ('doc_type', 'status', 'event', 'user')
        }),
        ('Client Info', {
            'fields': ('client_name', 'client_phone', 'client_email')
        }),
        ('Dates', {
            'fields': ('issue_date', 'due_date')
        }),
        ('Financials', {
            'fields': ('subtotal', 'tax_amount', 'discount', 'total_amount', 'amount_paid'),
            'description': "Subtotal and Total are auto-calculated from Line Items (save to update)."
        }),
        ('Terms & Notes', {
            'fields': ('terms', 'notes')
        }),
    )
    
    readonly_fields = ('doc_number', 'subtotal', 'total_amount')

    # Auto-fill user if creating from admin
    def save_model(self, request, obj, form, change):
        if not obj.user_id:
            obj.user = request.user
        
        # Recalculate totals on save
        # (Note: In a real app, signals are better, but this works for Admin)
        super().save_model(request, obj, form, change)