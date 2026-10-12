"""Notificaciones que se muestran en la campanita de la web.

Se guarda una fila por destinatario: así cada uno marca las suyas como leídas
sin afectar a los demás. Las crea el backend cuando pasa algo (una operación
pagada o fallida, un cambio de cotización), siempre a través de
``notificaciones.servicio``.
"""
from django.conf import settings
from django.db import models


class Notificacion(models.Model):
    class Tipo(models.TextChoices):
        OPERACION_EXITOSA = "OPERACION_EXITOSA", "Operación exitosa"
        OPERACION_FALLIDA = "OPERACION_FALLIDA", "Operación fallida"
        COTIZACION = "COTIZACION", "Cambio de cotización"

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notificaciones"
    )
    tipo = models.CharField(max_length=20, choices=Tipo.choices)
    titulo = models.CharField(max_length=120)
    mensaje = models.CharField(max_length=500)
    # Datos para la maqueta (id de la operación, moneda, montos...), por si
    # quiere mostrar algo más o enlazar a la operación.
    datos = models.JSONField(default=dict, blank=True)
    leida = models.BooleanField(default=False)
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-fecha", "-id"]
        indexes = [models.Index(fields=["usuario", "leida"])]
        verbose_name = "notificación"
        verbose_name_plural = "notificaciones"

    def __str__(self):
        return f"{self.usuario} · {self.titulo}"


class PreferenciaNotificaciones(models.Model):
    """Qué notificaciones quiere recibir cada usuario (suscripciones).

    Un usuario sin fila de preferencias recibe todo. Las categorías se cuentan
    desde el punto de vista de cada usuario: si en la caja la casa compra
    divisa con la tarjeta de un cliente, para ese cliente es una venta.
    """

    class Categoria(models.TextChoices):
        COMPRA = "COMPRA", "Compras"
        VENTA = "VENTA", "Ventas"
        COTIZACION = "COTIZACION", "Cambios de cotización"

    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="preferencia_notificaciones"
    )
    compras = models.BooleanField(default=True, help_text="Compras exitosas y fallidas.")
    ventas = models.BooleanField(default=True, help_text="Ventas exitosas y fallidas.")
    cotizaciones = models.BooleanField(default=True, help_text="Cambios de cotización.")
    # De qué divisas avisar los cambios de cotización. Vacío = de todas.
    monedas = models.ManyToManyField("monedas.Moneda", blank=True, related_name="+")

    class Meta:
        verbose_name = "preferencia de notificaciones"
        verbose_name_plural = "preferencias de notificaciones"

    def __str__(self):
        return f"Preferencias de {self.usuario}"

    def acepta(self, categoria, moneda=None):
        """Si este usuario quiere recibir una notificación de esa categoría."""
        if categoria == self.Categoria.COMPRA:
            return self.compras
        if categoria == self.Categoria.VENTA:
            return self.ventas
        if not self.cotizaciones:
            return False
        elegidas = {m.codigo for m in self.monedas.all()}
        return not elegidas or moneda in elegidas
