"""Facturas electrónicas de las operaciones pagadas.

Cada operación pagada tiene, como mucho, una factura: las de la web
(``operaciones.Transaccion``) y las de la caja (``caja.CompraCaja`` y
``caja.VentaCaja``). La factura la genera y la firma **Factura Segura**, que
es quien habla con el SIFEN de la DNIT; acá solo se guarda lo necesario para
mostrarla, consultar su estado y descargarla (ver ``facturacion.servicio``).
"""
from django.conf import settings
from django.db import models


class Factura(models.Model):
    """La factura electrónica de una operación.

    La operación facturada es **una sola** de estas tres: ``transaccion`` (la
    web), ``compra_caja`` o ``venta_caja`` (la ventanilla). Las otras dos
    quedan vacías.

    El cliente, los datos del receptor y el total se guardan **copiados**: si
    mañana cambia el nombre o el RUC del cliente, una factura ya emitida tiene
    que seguir mostrando a nombre de quién salió.

    ``numero`` es el número de documento dentro del rango que nos asignó la
    cátedra. Una factura simulada no tiene número: no gasta ninguno.
    """

    class Estado(models.TextChoices):
        SIMULADA = "SIMULADA", "Simulada (no emitida)"
        ERROR = "ERROR", "No se pudo emitir"
        SIN_CONFIRMAR = "SIN_CONFIRMAR", "Sin confirmar"
        ENVIADA = "ENVIADA", "Enviada, esperando al SIFEN"
        APROBADA = "APROBADA", "Aprobada"
        RECHAZADA = "RECHAZADA", "Rechazada por el SIFEN"
        CANCELADA = "CANCELADA", "Cancelada"

    transaccion = models.OneToOneField(
        "operaciones.Transaccion", on_delete=models.PROTECT, related_name="factura",
        null=True, blank=True,
    )
    compra_caja = models.OneToOneField(
        "caja.CompraCaja", on_delete=models.PROTECT, related_name="factura",
        null=True, blank=True,
    )
    venta_caja = models.OneToOneField(
        "caja.VentaCaja", on_delete=models.PROTECT, related_name="factura",
        null=True, blank=True,
    )
    # De quién es: decide quién puede verla, venga de la web o de la caja.
    cliente = models.ForeignKey(
        "clientes.Cliente", on_delete=models.PROTECT, related_name="facturas"
    )
    numero = models.PositiveIntegerField(
        null=True, blank=True, unique=True,
        help_text="Número de documento (dNumDoc). Vacío si no se llegó a emitir.",
    )
    cdc = models.CharField(
        max_length=44, blank=True,
        help_text="Código de control de 44 dígitos que devuelve Factura Segura.",
    )
    estado = models.CharField(max_length=15, choices=Estado.choices, default=Estado.SIMULADA)
    detalle = models.CharField(
        max_length=500, blank=True,
        help_text="Lo que respondió Factura Segura o el SIFEN (motivo de un rechazo, etc.).",
    )

    receptor_nombre = models.CharField(max_length=255)
    receptor_documento = models.CharField(max_length=20, blank=True)
    total = models.DecimalField(max_digits=16, decimal_places=0)
    # El documento electrónico tal como se armó (JSON de Factura Segura).
    de = models.JSONField(default=dict, blank=True)

    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_estado = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-fecha_creacion"]

    def __str__(self):
        return f"Factura {self.numero_completo} ({self.get_estado_display()})"

    @property
    def origen(self):
        """La operación facturada: la transacción web o la operación de caja."""
        return self.transaccion or self.compra_caja or self.venta_caja

    @property
    def referencia(self):
        """De qué operación es: ``Web #5``, ``Caja, compra #2`` o ``Caja, venta #2``.

        Las compras y las ventas de la caja se numeran por separado, así que
        el número solo no alcanza para distinguirlas. Como en el resto de la
        caja, "compra" y "venta" van desde el lado de la casa.
        """
        if self.transaccion_id:
            return f"Web #{self.transaccion_id}"
        if self.compra_caja_id:
            return f"Caja, compra #{self.compra_caja_id}"
        return f"Caja, venta #{self.venta_caja_id}"

    @property
    def numero_completo(self):
        """El número como se imprime: ``001-003-0000382``."""
        if self.numero is None:
            return "Sin número"
        numeracion = settings.FACTURA_SEGURA_NUMERACION
        return f"{numeracion['establecimiento']}-{numeracion['punto_expedicion']}-{self.numero:07d}"

    @property
    def emitida(self):
        """Si existe en Factura Segura (tiene CDC): se puede consultar y descargar."""
        return bool(self.cdc)

    @property
    def se_puede_reintentar(self):
        """Falló o no se supo qué pasó: se puede volver a mandar."""
        return self.estado in (
            self.Estado.ERROR, self.Estado.RECHAZADA, self.Estado.SIN_CONFIRMAR
        )


class SecuenciaFactura(models.Model):
    """Control persistente y seguro de la numeración secuencial de facturas electrónicas.

    Permite registrar y consultar el último número utilizado para un
    establecimiento y punto de expedición, controlando el límite máximo
    autorizado por el timbrado de la DNIT / SIFEN (Factura Segura).
    """

    establecimiento = models.CharField(
        max_length=3,
        default="001",
        help_text="Código de establecimiento de 3 dígitos (dEst), ej: 001.",
    )
    punto_expedicion = models.CharField(
        max_length=3,
        default="003",
        help_text="Punto de expedición de 3 dígitos (dPunExp), ej: 003.",
    )
    ultimo_numero = models.PositiveIntegerField(
        default=387,
        help_text="Último número de factura utilizado (ej. 387 para 001-003-0000387).",
    )
    numero_inicio = models.PositiveIntegerField(
        default=382,
        help_text="Número inicial del rango autorizado (ej. 382).",
    )
    numero_fin = models.PositiveIntegerField(
        default=393,
        help_text="Límite máximo autorizado del talonario (ej. 393).",
    )
    timbrado = models.CharField(
        max_length=8,
        blank=True,
        default="",
        help_text="Número de timbrado asociado al talonario.",
    )
    activo = models.BooleanField(
        default=True,
        help_text="Indica si este talonario es el que está en uso actualmente.",
    )
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Secuencia de Factura"
        verbose_name_plural = "Secuencias de Facturas"
        unique_together = ("establecimiento", "punto_expedicion")

    def __str__(self):
        return (
            f"Talonario {self.establecimiento}-{self.punto_expedicion} "
            f"[{self.numero_inicio} - {self.numero_fin}] - Último: {self.ultimo_numero}"
        )

    @property
    def siguiente_numero(self) -> int:
        """Siguiente número correlativo que se debe emitir."""
        return self.ultimo_numero + 1

    @property
    def cantidad_disponible(self) -> int:
        """Cantidad de facturas disponibles antes de llegar al límite máximo."""
        return max(0, self.numero_fin - self.ultimo_numero)

    @property
    def esta_agotado(self) -> bool:
        """Indica si el talonario ya no tiene números disponibles para emitir."""
        return self.ultimo_numero >= self.numero_fin

    def formato_factura(self, numero: int | None = None) -> str:
        """Retorna el número formateado con el estándar EEE-PPP-NNNNNNN."""
        num = self.ultimo_numero if numero is None else numero
        return f"{self.establecimiento:0>3}-{self.punto_expedicion:0>3}-{num:07d}"

