from django.utils import timezone
from datetime import timedelta

class ActiveUserMiddleware:
    """
    Asymmetric Presence Engine:
    Silently tracks when a user is online without overloading the database.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            try:
                profile = request.user.userprofile
                now = timezone.now()
                
                # 🚨 PERFORMANCE OPTIMIZATION: 
                # Only ping the database if their last activity was more than 1 minute ago.
                if not profile.last_active or profile.last_active < now - timedelta(minutes=1):
                    profile.last_active = now
                    profile.save(update_fields=['last_active'])
            except Exception:
                # Failsafe: If a user somehow doesn't have a profile, don't crash the page.
                pass
        
        response = self.get_response(request)
        return response