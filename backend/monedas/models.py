from django.db import models

class Moneda(models.Model):
    codigo = models.CharField(max_length=3, unique=True)  # Ej: "USD", "EUR", "PYG"
    nombre = models.CharField(max_length=50)               # Ej: "Dólar estadounidense"
    simbolo = models.CharField(max_length=5)               # Ej: "$"
    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.codigo} - {self.nombre}"