"""Datos de Stripe que el sistema necesita recordar.

Stripe guarda las tarjetas, no nosotros: cada usuario tiene un "Customer" en
Stripe y sus tarjetas cuelgan de él. Acá solo se guarda qué Customer le
corresponde a cada usuario, para no crear uno nuevo en cada operación.
"""
from django.conf import settings
from django.db import models


class CuentaStripe(models.Model):
    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="cuenta_stripe"
    )
    customer_id = models.CharField(max_length=255, unique=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "cuenta de Stripe"
        verbose_name_plural = "cuentas de Stripe"

    def __str__(self):
        return f"{self.usuario} → {self.customer_id}"
