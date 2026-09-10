from django.db import models
from django.conf import settings


class TipoMedioPago(models.Model):
    clave = models.CharField(max_length=30, unique=True)
    nombre = models.CharField(max_length=80)
    activo = models.BooleanField(default=True)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return self.nombre


class MedioPago(models.Model):
    TIPO_CHOICES = [
        ('TARJETA_CREDITO', 'Tarjeta de Crédito'),
        ('TARJETA_DEBITO', 'Tarjeta de Débito'),
        ('CUENTA_BANCARIA', 'Cuenta Bancaria'),
        ('TRANSFERENCIA', 'Transferencia Bancaria'),
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
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-fecha_creacion']

    def __str__(self):
        return f"{self.alias} ({self.get_tipo_display()}) - {self.usuario.username}"


class TarjetaCredito(MedioPago):
    nombre_titular = models.CharField(max_length=120)
    alias_tarjeta = models.CharField(max_length=80)
    numero_tarjeta = models.CharField(max_length=255, help_text="Token o número protegido")
    fecha_vencimiento = models.CharField(max_length=5, help_text="Formato MM/YY")
    codigo_seguridad = models.CharField(max_length=255, help_text="Valor protegido")


class TransferenciaBancaria(MedioPago):
    numero_cuenta_origen = models.CharField(max_length=100)
    banco_origen = models.CharField(max_length=120)
    titular_origen = models.CharField(max_length=120)
    numero_cuenta_destino = models.CharField(max_length=100)
    banco_destino = models.CharField(max_length=120)
    titular_destino = models.CharField(max_length=120)


class BilleteraDigital(MedioPago):
    plataforma = models.CharField(max_length=80)
    identificador_cuenta = models.CharField(max_length=255)
    titular = models.CharField(max_length=120)