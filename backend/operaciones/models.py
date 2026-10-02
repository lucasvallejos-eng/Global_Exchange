"""Transacciones de compra y venta de divisas.

Cubre el alcance del Sprint 3: la operación de compra/venta con su cálculo de
comisión y tasa aplicada, y la cancelación por cambio de cotización antes del
pago. El cálculo y las reglas viven en ``operaciones.servicios``; este módulo
solo define qué se guarda de cada operación.
"""
from django.conf import settings
from django.db import models


class Transaccion(models.Model):
    """Una operación de compra o venta de divisa contra guaraníes.

    La otra moneda es siempre el guaraní (PYG): la casa de cambios opera
    divisas extranjeras contra la moneda local, así que alcanza con guardar
    cuál es la divisa.

    Los valores del cálculo (tasa, descuento, comisión, totales) se guardan
    **copiados** al momento de crear la operación, y no se recalculan desde la
    cotización o el segmento del cliente. Es a propósito: si mañana cambia la
    cotización o el segmento, una operación ya hecha tiene que seguir
    mostrando lo que se le cobró al cliente en su momento. Por la misma razón
    se guarda ``tasa_base``: es el precio contra el que se compara al pagar
    para detectar que la cotización cambió.

    Los estados son los de RN04: Pendiente pasa a Pagada o Cancelada, y una
    Pagada puede pasar a Anulada.
    """

    class Tipo(models.TextChoices):
        COMPRA = "COMPRA", "Compra de divisa"
        VENTA = "VENTA", "Venta de divisa"

    class Estado(models.TextChoices):
        PENDIENTE = "PENDIENTE", "Pendiente de pago"
        PAGADA = "PAGADA", "Pagada"
        CANCELADA = "CANCELADA", "Cancelada"
        ANULADA = "ANULADA", "Anulada"

    # RN02: se opera a nombre de un cliente (empresa o persona), no de un
    # usuario suelto. El usuario es quién la ejecutó.
    cliente = models.ForeignKey(
        "clientes.Cliente", on_delete=models.PROTECT, related_name="transacciones"
    )
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="transacciones"
    )
    tipo = models.CharField(max_length=10, choices=Tipo.choices)
    moneda = models.ForeignKey(
        "monedas.Moneda", on_delete=models.PROTECT, related_name="transacciones"
    )
    monto_divisa = models.DecimalField(
        max_digits=14, decimal_places=2,
        help_text="Cantidad de divisa que el cliente compra o vende.",
    )

    # Copia del cálculo al momento de crear la operación.
    cotizacion = models.ForeignKey(
        "cotizaciones.Cotizacion", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="transacciones",
        help_text="Cotización vigente al crear la operación. Solo como referencia.",
    )
    tasa_base = models.DecimalField(
        max_digits=12, decimal_places=2,
        help_text="Precio de venta (si el cliente compra) o de compra (si vende).",
    )
    descuento_compra = models.DecimalField(
        max_digits=4, decimal_places=2, default=0,
        help_text="Descuento del segmento del cliente, entre 0 y 1. Solo en compras.",
    )
    tasa_aplicada = models.DecimalField(
        max_digits=14, decimal_places=4,
        help_text="Tasa base con el descuento del segmento ya aplicado.",
    )
    monto_guaranies = models.DecimalField(
        max_digits=16, decimal_places=0,
        help_text="Monto de divisa por la tasa aplicada, antes de la comisión.",
    )
    porcentaje_comision = models.DecimalField(
        max_digits=5, decimal_places=2, default=0,
        help_text="Porcentaje de comisión del segmento, entre 0 y 100.",
    )
    comision = models.DecimalField(max_digits=16, decimal_places=0, default=0)
    total_guaranies = models.DecimalField(
        max_digits=16, decimal_places=0,
        help_text="Lo que paga el cliente (compra) o lo que recibe (venta).",
    )

    # El medio de pago es opcional. Se guarda además su descripción en texto
    # porque la maqueta borra medios de pago de verdad: sin la copia, el
    # historial perdería con qué se pagó.
    medio_pago = models.ForeignKey(
        "medios_pago.MedioPago", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="transacciones",
    )
    medio_pago_descripcion = models.CharField(max_length=150, blank=True)

    estado = models.CharField(
        max_length=10, choices=Estado.choices, default=Estado.PENDIENTE
    )
    motivo_cancelacion = models.CharField(max_length=200, blank=True)
    # Separa la cancelación automática (la cotización cambió antes del pago)
    # de la que hace el propio cliente: la pantalla muestra una alerta distinta.
    cancelada_por_cotizacion = models.BooleanField(default=False)
    tasa_base_nueva = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True,
        help_text="Precio vigente que se encontró al intentar pagar. Vacío si ya no había cotización.",
    )

    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_pago = models.DateTimeField(null=True, blank=True)
    fecha_cancelacion = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-fecha_creacion"]
        verbose_name = "transacción"
        verbose_name_plural = "transacciones"

    def __str__(self):
        return (
            f"#{self.pk} {self.get_tipo_display()} {self.monto_divisa} "
            f"{self.moneda.codigo} ({self.get_estado_display()})"
        )
