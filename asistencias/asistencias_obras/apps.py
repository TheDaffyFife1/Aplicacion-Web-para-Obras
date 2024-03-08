from django.apps import AppConfig


class AsistenciasObrasConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'asistencias_obras'

    def ready(self):
        import asistencias_obras.signals 
