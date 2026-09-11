"""Modelos para la administración de Medios de Pago y sus tipos específicos."""
from django.db import models
from django.conf import settings


class TipoMedioPago(models.Model):
    """Representa la clasificación global o catálogo de tipos de medios de pago.

    Attributes:
        clave (CharField): Identificador único en texto (ej. ``TARJETA_CREDITO``).
        nombre (CharField): Descripción legible del tipo de medio de pago (ej. "Tarjeta de Crédito").
        activo (BooleanField): Estado de disponibilidad para operar en el sistema.
    """
    clave = models.CharField(max_length=30, unique=True)
    nombre = models.CharField(max_length=80)
    activo = models.BooleanField(default=True)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        """Devuelve el nombre descriptivo del tipo de medio de pago.

        Returns:
            str: Nombre legible del registro.
        """
        return self.nombre


class MedioPago(models.Model):
    """Modelo base para registrar medios de pago asociados a un usuario.

    Permite registrar datos generales tanto desde la interfaz principal de Django
    como de manera simplificada desde la maqueta/API.

    Attributes:
        usuario (ForeignKey): Usuario propietario del medio de pago.
        tipo (CharField): Clasificación del medio de pago según ``TIPO_CHOICES``.
        alias (CharField): Nombre asignado por el usuario para identificar la cuenta.
        numero_cuenta_o_tarjeta (CharField): Número, CBU o valor codificado de la cuenta/tarjeta.
        banco_o_proveedor (CharField): Entidad financiera o proveedor del servicio.
        activo (BooleanField): Estado que indica si el medio de pago está habilitado.
        fecha_creacion (DateTimeField): Fecha y hora en que se registró el medio de pago.
        fecha_actualizacion (DateTimeField): Fecha y hora del último cambio realizado.
    """
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
        """Formatea la representación legible del medio de pago.

        Returns:
            str: Cadena con el alias, el tipo de medio de pago y el username del usuario.
        """
        return f"{self.alias} ({self.get_tipo_display()}) - {self.usuario.username}"


class TarjetaCredito(MedioPago):
    """Especialización del modelo MedioPago para tarjetas de crédito.

    Attributes:
        nombre_titular (CharField): Nombre impreso en el plástico.
        alias_tarjeta (CharField): Nombre de fantasía o etiqueta asignada por el titular.
        numero_tarjeta (CharField): Token o número de tarjeta codificado/protegido.
        fecha_vencimiento (CharField): Fecha de expiración en formato MM/YY.
        codigo_seguridad (CharField): Valor CVV/CVC cifrado o protegido.
    """
    nombre_titular = models.CharField(max_length=120)
    alias_tarjeta = models.CharField(max_length=80)
    numero_tarjeta = models.CharField(max_length=255, help_text="Token o número protegido")
    fecha_vencimiento = models.CharField(max_length=5, help_text="Formato MM/YY")
    codigo_seguridad = models.CharField(max_length=255, help_text="Valor protegido")


class TransferenciaBancaria(MedioPago):
    """Especialización del modelo MedioPago para datos de transferencias bancarias.

    Attributes:
        numero_cuenta_origen (CharField): Número o CBU de la cuenta que envía los fondos.
        banco_origen (CharField): Nombre del banco de origen.
        titular_origen (CharField): Nombre completo o razón social del remitente.
        numero_cuenta_destino (CharField): Número o CBU de la cuenta receptora.
        banco_destino (CharField): Nombre del banco de destino.
        titular_destino (CharField): Nombre del destinatario de la transferencia.
    """
    numero_cuenta_origen = models.CharField(max_length=100)
    banco_origen = models.CharField(max_length=120)
    titular_origen = models.CharField(max_length=120)
    numero_cuenta_destino = models.CharField(max_length=100)
    banco_destino = models.CharField(max_length=120)
    titular_destino = models.CharField(max_length=120)


class BilleteraDigital(MedioPago):
    """Especialización del modelo MedioPago para plataformas de cobro/pago digital.

    Attributes:
        plataforma (CharField): Proveedor del servicio (ej. "MercadoPago", "PayPal").
        identificador_cuenta (CharField): Email, teléfono o usuario registrado en la plataforma.
        titular (CharField): Nombre completo o razón social del titular de la cuenta.
    """
    plataforma = models.CharField(max_length=80)
    identificador_cuenta = models.CharField(max_length=255)
    titular = models.CharField(max_length=120)