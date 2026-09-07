from django.db import models
from django.conf import settings

class MedioPago(models.Model):
    TIPO_CHOICES = [
        ('TARJETA_CREDITO', 'Tarjeta de Crédito'),
        ('TARJETA_DEBITO', 'Tarjeta de Débito'),
        ('CUENTA_BANCARIA', 'Cuenta Bancaria'),
        ('BILLETERA_DIGITAL', 'Billetera Digital'),
    ]

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='medios_pago'
    )
    # El alta desde la maqueta pide solo nombre y estado, así que el tipo y el
    # número quedan opcionales: se completan desde las pantallas de Django
    # cuando hace falta el detalle de la tarjeta o la cuenta.
    tipo = models.CharField(max_length=30, choices=TIPO_CHOICES, blank=True)
    alias = models.CharField(max_length=50, help_text="Nombre del medio de pago (ej: Transferencia Bancaria)")
    numero_cuenta_o_tarjeta = models.CharField(max_length=50, blank=True, help_text="Número o alias/CBU codificado")
    banco_o_proveedor = models.CharField(max_length=100, blank=True, null=True)
    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-fecha_creacion']

    def __str__(self):
        return f"{self.alias} ({self.get_tipo_display()}) - {self.usuario.username}"