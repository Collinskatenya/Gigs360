from django.apps import AppConfig

class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'

    def ready(self):
        # CRITICAL: This imports the signals when the app starts.
        # Without this, your Notification System (signals.py) will not work.
        import core.signals