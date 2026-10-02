from django.apps import AppConfig


class ApiConfig(AppConfig):
    name = 'api'
    
    def ready(self):
        # Import signals to register them
        import api.signals  # noqa
