"""Facturas electrónicas de las operaciones pagadas.

Cada operación pagada tiene, como mucho, una factura. La factura la genera y
la firma **Factura Segura**, que es quien habla con el SIFEN de la DNIT; acá
solo se guarda lo necesario para mostrarla, consultar su estado y descargarla
(ver ``facturacion.servicio``).
"""
from django.conf import settings
from django.db import models


class Factura(models.Model):
    """La factura electrónica de una operación.

    Los datos del receptor y el total se guardan **copiados**: si mañana cambia
    el nombre o el RUC del cliente, una factura ya emitida tiene que seguir
    mostrando a nombre de quién salió.

    ``numero`` es el número de documento dentro del rango que nos asignó la
    cátedra. Una factura simulada no tiene número: no gasta ninguno.
    """

    class Estado(models.TextChoices):
        SIMULADA = "SIMULADA", "Simulada (no emitida)"
        ERROR = "ERROR", "No se pudo emitir"
        SIN_CONFIRMAR = "SIN_CONFIRMAR", "Sin confirmar"
        ENVIADA = "ENVIADA", "Enviada, esperando al SIFEN"
        APROBADA = "APROBADA", "Aprobada"
        RECHAZADA = "RECHAZADA", "Rechazada por el SIFEN"
        CANCELADA = "CANCELADA", "Cancelada"

    transaccion = models.OneToOneField(
        "operaciones.Transaccion", on_delete=models.PROTECT, related_name="factura"
    )
    numero = models.PositiveIntegerField(
        null=True, blank=True, unique=True,
        help_text="Número de documento (dNumDoc). Vacío si no se llegó a emitir.",
    )
    cdc = models.CharField(
        max_length=44, blank=True,
        help_text="Código de control de 44 dígitos que devuelve Factura Segura.",
    )
    estado = models.CharField(max_length=15, choices=Estado.choices, default=Estado.SIMULADA)
    detalle = models.CharField(
        max_length=500, blank=True,
        help_text="Lo que respondió Factura Segura o el SIFEN (motivo de un rechazo, etc.).",
    )

    receptor_nombre = models.CharField(max_length=255)
    receptor_documento = models.CharField(max_length=20, blank=True)
    total = models.DecimalField(max_digits=16, decimal_places=0)
    # El documento electrónico tal como se armó (JSON de Factura Segura).
    de = models.JSONField(default=dict, blank=True)

    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_estado = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-fecha_creacion"]

    def __str__(self):
        return f"Factura {self.numero_completo} ({self.get_estado_display()})"

    @property
    def numero_completo(self):
        """El número como se imprime: ``001-003-0000382``."""
        if self.numero is None:
            return "Sin número"
        numeracion = settings.FACTURA_SEGURA_NUMERACION
        return f"{numeracion['establecimiento']}-{numeracion['punto_expedicion']}-{self.numero:07d}"

    @property
    def emitida(self):
        """Si existe en Factura Segura (tiene CDC): se puede consultar y descargar."""
        return bool(self.cdc)

    @property
    def se_puede_reintentar(self):
        """Falló o no se supo qué pasó: se puede volver a mandar."""
        return self.estado in (
            self.Estado.ERROR, self.Estado.RECHAZADA, self.Estado.SIN_CONFIRMAR
        )
