from django.conf import settings
from django.db import models


class AperturaCaja(models.Model):
    class Estado(models.TextChoices):
        ACTIVA = "activa", "Activa"
        CERRADA = "cerrada", "Cerrada"

    cajero_id = models.CharField(max_length=255)
    # Para mostrar quién abrió la caja en el historial (cajero_id es el "sub"
    # de Keycloak). Vacío en las aperturas anteriores a este campo.
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="aperturas_caja",
    )
    fecha_hora_apertura = models.DateTimeField(auto_now_add=True)
    totales_consolidado = models.JSONField(default=dict)
    estado = models.CharField(max_length=10, choices=Estado.choices, default=Estado.ACTIVA)

    class Meta:
        db_table = "aperturas_caja"


class DetalleAperturaDenominacion(models.Model):
    apertura = models.ForeignKey(
        AperturaCaja, on_delete=models.CASCADE, related_name="detalles"
    )
    denominacion = models.ForeignKey("monedas.Denominacion", on_delete=models.PROTECT)
    cantidad_unidades = models.PositiveIntegerField()
    subtotal = models.DecimalField(max_digits=18, decimal_places=2)

    class Meta:
        db_table = "detalles_apertura_denominaciones"


class CompraCaja(models.Model):
    apertura = models.ForeignKey(AperturaCaja, on_delete=models.PROTECT, related_name="compras")
    cajero_id = models.CharField(max_length=255)
    cliente = models.ForeignKey("clientes.Cliente", on_delete=models.PROTECT)
    moneda = models.ForeignKey("monedas.Moneda", on_delete=models.PROTECT)
    monto_divisa = models.DecimalField(max_digits=18, decimal_places=2)
    cotizacion_aplicada = models.DecimalField(max_digits=18, decimal_places=4)
    monto_local_total = models.DecimalField(max_digits=18, decimal_places=0)
    medio_pago = models.ForeignKey(
        "medios_pago.MedioPago", on_delete=models.PROTECT, null=True, blank=True
    )
    cotizacion_base = models.DecimalField(max_digits=18, decimal_places=4, null=True, blank=True)
    tasa_preferencial_aplicada = models.DecimalField(max_digits=8, decimal_places=4, default=0)
    cotizacion_final = models.DecimalField(max_digits=18, decimal_places=4, null=True, blank=True)
    # Cobro con tarjeta en Stripe (pi_...). Vacío si se pagó en efectivo.
    # Único: el mismo cobro no puede registrar dos operaciones.
    stripe_payment_intent_id = models.CharField(max_length=255, null=True, blank=True, unique=True)
    # Cómo pagó el cliente: EFECTIVO, TARJETA_STRIPE o la clave del tipo de
    # medio de pago (transferencia, etc.). Decide qué entra al cajón en el arqueo.
    forma_pago = models.CharField(max_length=30, blank=True)
    fecha_hora = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "compras_caja"


class VentaCaja(models.Model):
    apertura = models.ForeignKey(AperturaCaja, on_delete=models.PROTECT, related_name="ventas")
    cajero_id = models.CharField(max_length=255)
    cliente = models.ForeignKey("clientes.Cliente", on_delete=models.PROTECT)
    moneda = models.ForeignKey("monedas.Moneda", on_delete=models.PROTECT)
    monto_divisa = models.DecimalField(max_digits=18, decimal_places=2)
    cotizacion_aplicada = models.DecimalField(max_digits=18, decimal_places=4)
    monto_local_total = models.DecimalField(max_digits=18, decimal_places=0)
    medio_pago = models.ForeignKey(
        "medios_pago.MedioPago", on_delete=models.PROTECT, null=True, blank=True
    )
    cotizacion_base = models.DecimalField(max_digits=18, decimal_places=4, null=True, blank=True)
    tasa_preferencial_aplicada = models.DecimalField(max_digits=8, decimal_places=4, default=0)
    cotizacion_final = models.DecimalField(max_digits=18, decimal_places=4, null=True, blank=True)
    # Cobro con tarjeta en Stripe (pi_...). Vacío si se pagó en efectivo.
    # Único: el mismo cobro no puede registrar dos operaciones.
    stripe_payment_intent_id = models.CharField(max_length=255, null=True, blank=True, unique=True)
    # Cómo pagó el cliente: EFECTIVO, TARJETA_STRIPE o la clave del tipo de
    # medio de pago (transferencia, etc.). Decide qué entra al cajón en el arqueo.
    forma_pago = models.CharField(max_length=30, blank=True)
    fecha_hora = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "ventas_caja"


class CierreCaja(models.Model):
    apertura = models.OneToOneField(
        AperturaCaja, on_delete=models.CASCADE, related_name="cierre"
    )
    cajero_id = models.CharField(max_length=255)
    fecha_hora_cierre = models.DateTimeField(auto_now_add=True)
    totales_esperados = models.JSONField(default=dict)
    totales_reales = models.JSONField(default=dict)
    diferencia = models.JSONField(default=dict)

    class Meta:
        db_table = "cierres_caja"
