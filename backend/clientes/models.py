"""Modelo de Cliente (empresa) y su relación con los usuarios del sistema."""
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
