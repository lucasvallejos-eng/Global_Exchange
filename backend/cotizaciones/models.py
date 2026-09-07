from django.db import models
from monedas.models import Moneda 
from django.core.exceptions import ValidationError



class Cotizacion(models.Model):
    moneda = models.ForeignKey(Moneda, on_delete=models.CASCADE, related_name='cotizaciones')
    precio_compra = models.DecimalField(max_digits=12, decimal_places=2)
    precio_venta = models.DecimalField(max_digits=12, decimal_places=2)
    fecha = models.DateTimeField(auto_now_add=True)
    activa = models.BooleanField(default=True)

    class Meta:
        ordering = ['-fecha']  # Ordena mostrando las más recientes primero

    def __str__(self):
        return f"{self.moneda.codigo} | Compra: {self.precio_compra} - Venta: {self.precio_venta}"

    def clean(self):
        if self.precio_venta <= self.precio_compra:
            raise ValidationError("El precio de venta debe ser mayor al precio de compra.")