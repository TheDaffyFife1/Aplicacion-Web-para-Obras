from django.apps import AppConfig


class AsistenciasObrasConfig(AppConfig):
    name = 'asistencias_obras'

    def ready(self):
        import asistencias_obras.signals 
