from .models import Notification

def notifications(request):
    """
    Makes notification data available to every template (Base Layout).
    Used for the Bell Icon counter and Dropdown list.
    """
    if request.user.is_authenticated:
        # 1. Get the Badge Count (Unread only)
        count = Notification.objects.filter(user=request.user, is_read=False).count()
        
        # 2. Get the Dropdown List (Recent 10, regardless of read status)
        # We limit to 10 to keep the query fast on every page load.
        recent_notifications = Notification.objects.filter(user=request.user).order_by('-created_at')[:10]
        
        return {
            'notif_count': count,
            'notifications': recent_notifications
        }
        
    # Return empty context for anonymous users (Login page, etc.)
    return {}