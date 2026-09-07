"""Modelo de Cliente (empresa) y su relación con los usuarios del sistema."""
from decimal import Decimal

from django.conf import settings
from django.db import models


class Cliente(models.Model):
    """Empresa que opera en la casa de cambio."""

    class Tipo(models.TextChoices):
        JURIDICA = "Jurídica", "Jurídica"
        FISICA = "Física", "Física"

    nombre = models.CharField(max_length=255)
    tipo = models.CharField(max_length=20, choices=Tipo.choices)
    direccion = models.CharField(max_length=255)
    cuenta_acreditar = models.CharField(max_length=100)
    correo = models.EmailField()
    segmento = models.ForeignKey(
        "comisiones.SegmentoCliente",
        on_delete=models.PROTECT,
        related_name="clientes",
        null=True,
        blank=True,
        help_text="Segmento comercial del que sale el porcentaje de comisión.",
    )
    usuarios = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name="clientes_asociados",
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return self.nombre

    @property
    def porcentaje_comision(self):
        """Porcentaje de comisión que le corresponde por su segmento.

        Devuelve ``None`` si el cliente todavía no tiene segmento asignado.
        Se expone acá para que quien calcule una operación de compra o venta
        no tenga que conocer la estructura de ``comisiones``.

        Siempre devuelve ``Decimal``. Django no convierte el valor de un
        DecimalField hasta que el registro va y vuelve de la base, así que un
        segmento recién creado con una cadena la conserva tal cual. Sin esta
        conversión, ``monto * porcentaje`` repetiría la cadena en vez de
        multiplicar, y sobre un importe eso pasa desapercibido.
        """
        if self.segmento is None:
            return None
        return Decimal(self.segmento.porcentaje_comision)
