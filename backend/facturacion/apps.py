from django.apps import AppConfig


class FacturacionConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "facturacion"

    def ready(self):
        # Conecta la señal que factura las operaciones pagadas.
        from . import senales  # noqa: F401
