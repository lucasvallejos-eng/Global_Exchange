"""Modelos de la aplicación de Monedas."""
from django.db import models

class Moneda(models.Model):
    """Representa una moneda extranjera o local aceptada para la operativa de cambio.

    Almacena los datos descriptivos, el código ISO de tres letras, el símbolo visual,
    así como el estado activo/inactivo para su uso en cotizaciones.

    Attributes:
        codigo (CharField): Código ISO de 3 letras que identifica la moneda (ej. "USD", "EUR").
        nombre (CharField): Nombre descriptivo completo de la divisa (ej. "Dólar estadounidense").
        simbolo (CharField): Símbolo tipográfico utilizado en las representaciones de precios (ej. "$").
        activo (BooleanField): Indica si la moneda está habilitada para realizar operaciones de compra/venta.
        fecha_creacion (DateTimeField): Fecha y hora en que se dio de alta el registro en el sistema.
        fecha_actualizacion (DateTimeField): Fecha y hora del último cambio realizado sobre el registro.
    """
    codigo = models.CharField(max_length=3, unique=True)  # Ej: "USD", "EUR", "PYG"
    nombre = models.CharField(max_length=50)               # Ej: "Dólar estadounidense"
    simbolo = models.CharField(max_length=5)               # Ej: "$"
    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    def __str__(self):
        """Devuelve la representación en texto legible de la moneda.

        Returns:
            str: Cadena formateada con el código y el nombre de la moneda.
        """
        return f"{self.codigo} - {self.nombre}"