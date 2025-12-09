from django.utils import timezone

class UpdateLastActivityMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            # Update the last_activity field we added to the model
            request.user.last_activity = timezone.now()
            # Use update_fields to optimize performance
            request.user.save(update_fields=['last_activity'])
        
        response = self.get_response(request)
        return response