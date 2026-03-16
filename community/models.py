from django.db import models
from django.conf import settings
from django.utils.text import slugify
from inventory.models import InventoryItem

# ==========================================
# 1. SPACES (The Clustered Channels)
# ==========================================

class Space(models.Model):
    # 🚨 INNOVATION: The Cluster Engine (Matches Circle.so layout)
    CLUSTER_CHOICES = (
        ('1_general', 'General'),
        ('2_creatives', 'Photographers & Creators'),
        ('3_planners', 'Event Planners & Ops'),
        ('4_vendors', 'Vendors & Gear Marketplace'),
        ('5_support', 'Help, Inquiries & Complaints'),
    )
    
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True, blank=True, help_text="Auto-generated from name")
    description = models.CharField(max_length=255, blank=True)
    icon = models.CharField(max_length=50, default='bi-hash', help_text="Bootstrap icon class (e.g., bi-chat-dots)")
    
    SPACE_TYPES = (
        ('text', 'Standard Discussion'),
        ('gig_board', 'Gig & Job Board'),
        ('announcement', 'HQ Announcements'),
    )
    space_type = models.CharField(max_length=20, choices=SPACE_TYPES, default='text')
    
    # 🌟 NEW: Categorization
    cluster = models.CharField(max_length=20, choices=CLUSTER_CHOICES, default='1_general')
    
    # 🚨 SECURITY & MONETIZATION
    is_premium_only = models.BooleanField(default=False, help_text="Restrict access to Pro/Verified users only")
    admin_only_post = models.BooleanField(default=False, help_text="Only Gigs360 Staff can post here (e.g. Announcements)")
    
    order = models.IntegerField(default=0, help_text="Lower numbers appear first in the sidebar")

    class Meta:
        ordering = ['cluster', 'order', 'name'] # 🚨 Updated to group by cluster first

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.get_cluster_display()} > {self.name}"


# ==========================================
# 2. POSTS (The Feed Content)
# ==========================================

class Post(models.Model):
    space = models.ForeignKey(Space, on_delete=models.CASCADE, related_name='posts')
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='community_posts')
    
    # Core Content
    title = models.CharField(max_length=200, blank=True, null=True)
    content = models.TextField()
    
    # 💼 The Gig Board Engine
    is_gig_offer = models.BooleanField(default=False, help_text="Flags this post as a hiring opportunity")
    budget = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="In KES")
    
    # 📸 The Gear Embed System
    linked_gear = models.ForeignKey(
        InventoryItem, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='featured_posts',
        help_text="Allows vendors to showcase their available assets in the feed"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at'] # Newest posts show first

    def __str__(self):
        if self.title:
            return self.title
        return f"Post by {self.author.username} in {self.space.name}"


# ==========================================
# 3. COMMENTS (Two-Way Interaction)
# ==========================================

class Comment(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='community_comments')
    content = models.TextField()
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['created_at'] # Oldest comments at the top (chronological thread)

    def __str__(self):
        return f"Reply by {self.author.username} on Post #{self.post.id}"