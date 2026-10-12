from django.apps import AppConfig


class NotificacionesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "notificaciones"

    def ready(self):
        # Conecta la señal que avisa los cambios de cotización.
        from . import senales  # noqa: F401
