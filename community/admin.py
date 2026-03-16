from django.contrib import admin
from .models import Space, Post, Comment

@admin.register(Space)
class SpaceAdmin(admin.ModelAdmin):
    # 🚨 FIXED: Replaced 'space_type' with 'cluster', and added 'admin_only_post'
    list_display = ('name', 'cluster', 'order', 'is_premium_only', 'admin_only_post')
    
    # 🎨 INNOVATION: Allows you to toggle premium/admin locks directly from the main list view!
    list_editable = ('cluster', 'order', 'is_premium_only', 'admin_only_post')
    
    prepopulated_fields = {'slug': ('name',)}
    list_filter = ('cluster', 'is_premium_only', 'admin_only_post')
    search_fields = ('name', 'description')

@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    # Added budget and removed the basic list display to show deeper MIS data
    list_display = ('title', 'author', 'space', 'is_gig_offer', 'budget', 'created_at')
    list_filter = ('space', 'is_gig_offer', 'created_at')
    search_fields = ('title', 'content', 'author__username', 'author__userprofile__business_name')
    readonly_fields = ('created_at', 'updated_at')
    
    # 📊 MIS ARCHITECTURE: Groups the data logically when you click into a specific post
    fieldsets = (
        ('Post Details', {
            'fields': ('author', 'space', 'title', 'content')
        }),
        ('Market Insights & Monetization', {
            'fields': ('linked_gear', 'is_gig_offer', 'budget')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )

@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    # Upgraded from basic admin.site.register(Comment) to a full moderation panel
    list_display = ('author', 'post', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('content', 'author__username', 'post__title')
    readonly_fields = ('created_at', 'updated_at')