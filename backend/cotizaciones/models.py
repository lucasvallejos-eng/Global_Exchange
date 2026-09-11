"""Modelos para la gestión de Cotizaciones y Auditoría de Historial."""
from django.db import models
from monedas.models import Moneda 
from django.conf import settings
from django.core.exceptions import ValidationError



class Cotizacion(models.Model):
    """Representa la tasa de cambio activa o histórica para una moneda.

    Almacena los precios de compra y venta fijados por la entidad. Garantiza
    mediante validación interna que el precio de venta sea estrictamente mayor
    al precio de compra.

    Attributes:
        moneda (ForeignKey): Moneda extranjera a la que aplica la cotización.
        precio_compra (DecimalField): Valor al que la casa de cambio compra la divisa.
        precio_venta (DecimalField): Valor al que la casa de cambio vende la divisa.
        fecha (DateTimeField): Fecha y hora en que se registró la cotización.
        activa (BooleanField): Indica si la cotización es la tasa vigente de mercado.
    """
    moneda = models.ForeignKey(Moneda, on_delete=models.CASCADE, related_name='cotizaciones')
    precio_compra = models.DecimalField(max_digits=12, decimal_places=2)
    precio_venta = models.DecimalField(max_digits=12, decimal_places=2)
    fecha = models.DateTimeField(auto_now_add=True)
    activa = models.BooleanField(default=True)

    class Meta:
        ordering = ['-fecha']  

    def __str__(self):
        """Representación en texto legible de la cotización.

        Returns:
            str: Cadena formateada con el código de la moneda y las tasas.
        """
        return f"{self.moneda.codigo} | Compra: {self.precio_compra} - Venta: {self.precio_venta}"

    def clean(self):
        """Ejecuta las validaciones de negocio del modelo (RN10).

        Raises:
            ValidationError: Si el precio de venta es menor o igual al precio de compra.
        """
        if self.precio_venta <= self.precio_compra:
            raise ValidationError("El precio de venta debe ser mayor al precio de compra.")


class HistorialCotizacion(models.Model):
    """Registro inmutable de auditoría para cambios de cotización.

    Almacena el detalle histórico de cada modificación de tasas realizada sobre
    una moneda, incluyendo los precios anteriores, los nuevos valores y el usuario
    administrador responsable del cambio.

    Attributes:
        moneda (ForeignKey): Moneda sobre la cual se aplicó la actualización.
        administrador (ForeignKey): Usuario administrador que ejecutó la modificación.
        precio_compra_anterior (DecimalField): Tasa de compra previa al cambio.
        precio_compra_nuevo (DecimalField): Tasa de compra asignada en la actualización.
        precio_venta_anterior (DecimalField): Tasa de venta previa al cambio.
        precio_venta_nuevo (DecimalField): Tasa de venta asignada en la actualización.
        fecha_registro (DateTimeField): Timestamp exacto en que se registró el evento.
    """
    moneda = models.ForeignKey(Moneda, on_delete=models.CASCADE, related_name="historial_cotizaciones")
    administrador = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    precio_compra_anterior = models.DecimalField(max_digits=12, decimal_places=2)
    precio_compra_nuevo = models.DecimalField(max_digits=12, decimal_places=2)
    precio_venta_anterior = models.DecimalField(max_digits=12, decimal_places=2)
    precio_venta_nuevo = models.DecimalField(max_digits=12, decimal_places=2)
    fecha_registro = models.DateTimeField(auto_now_add=True)