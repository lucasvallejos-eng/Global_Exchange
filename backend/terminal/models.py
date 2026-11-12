"""Terminal de autoservicio (TAUser): el cliente completa con efectivo una
operación que reservó en la web.

- ``Terminal``: una máquina, con los billetes que tiene adentro
  (``BilleteTerminal``) para entregar divisa, guaraníes y vuelto.
- ``OperacionTerminal``: la reserva de una ``Transaccion`` pendiente, con el
  código que el cliente ingresa en la terminal y lo que pasó ahí (qué depositó,
  qué se le entregó).

Las reglas están en ``terminal.servicio``.
"""
from django.db import models


class TerminalManager(models.Manager):
    def get_by_natural_key(self, nombre):
        return self.get(nombre=nombre)


class Terminal(models.Model):
    """Una terminal de autoservicio.

    Attributes:
        nombre (str): cómo se la reconoce, por ejemplo "Terminal Centro". Único.
        ubicacion (str): dónde está.
        activa (bool): una terminal inactiva no atiende a nadie.
    """

    nombre = models.CharField(max_length=80, unique=True)
    ubicacion = models.CharField(max_length=150, blank=True)
    activa = models.BooleanField(default=True)

    objects = TerminalManager()

    class Meta:
        ordering = ["nombre"]
        verbose_name = "terminal de autoservicio"
        verbose_name_plural = "terminales de autoservicio"

    def natural_key(self):
        return (self.nombre,)

    def __str__(self):
        return self.nombre


class BilleteTerminalManager(models.Manager):
    def get_by_natural_key(self, terminal, codigo, valor):
        return self.get(terminal__nombre=terminal, denominacion__moneda__codigo=codigo,
                        denominacion__valor=valor)


class BilleteTerminal(models.Model):
    """Cuántos billetes de una denominación tiene una terminal.

    Sube con lo que depositan los clientes y baja con lo que entrega.
    """

    terminal = models.ForeignKey(Terminal, on_delete=models.CASCADE, related_name="billetes")
    denominacion = models.ForeignKey("monedas.Denominacion", on_delete=models.PROTECT)
    cantidad = models.PositiveIntegerField(default=0)

    objects = BilleteTerminalManager()

    class Meta:
        unique_together = ("terminal", "denominacion")
        ordering = ["terminal", "denominacion__moneda__codigo", "-denominacion__valor"]
        verbose_name = "billetes de la terminal"
        verbose_name_plural = "billetes de las terminales"

    def natural_key(self):
        return (self.terminal.nombre, *self.denominacion.natural_key())

    natural_key.dependencies = ["terminal.terminal", "monedas.denominacion"]

    def __str__(self):
        return f"{self.terminal}: {self.cantidad} x {self.denominacion}"


class OperacionTerminal(models.Model):
    """Una operación web que se completa (o se cancela) en una terminal.

    Attributes:
        codigo: lo que el cliente ingresa en la terminal. Único y al azar.
        estado: ``ESPERANDO`` hasta que el cliente va a la terminal.
        entrega: en una venta, si los guaraníes se retiran en efectivo o se
            acreditan en la cuenta del cliente.
        depositado, entregado: billetes por moneda, ``{"USD": {"100": 2}}``.
            En ``entregado`` va también el vuelto.
    """

    class Estado(models.TextChoices):
        ESPERANDO = "ESPERANDO", "Esperando en la terminal"
        COMPLETADA = "COMPLETADA", "Completada"
        CANCELADA = "CANCELADA", "Cancelada"

    class Entrega(models.TextChoices):
        EFECTIVO = "EFECTIVO", "Retiro en efectivo"
        CUENTA = "CUENTA", "Acreditación en cuenta"

    transaccion = models.OneToOneField(
        "operaciones.Transaccion", on_delete=models.PROTECT, related_name="reserva_terminal"
    )
    codigo = models.CharField(max_length=8, unique=True)
    estado = models.CharField(max_length=10, choices=Estado.choices, default=Estado.ESPERANDO)
    terminal = models.ForeignKey(Terminal, on_delete=models.PROTECT, null=True, blank=True,
                                 related_name="operaciones")
    entrega = models.CharField(max_length=10, choices=Entrega.choices, default=Entrega.EFECTIVO)
    depositado = models.JSONField(default=dict, blank=True)
    entregado = models.JSONField(default=dict, blank=True)
    detalle = models.CharField(max_length=500, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_fin = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-fecha_creacion"]
        verbose_name = "operación en terminal"
        verbose_name_plural = "operaciones en terminal"

    def __str__(self):
        return f"{self.codigo} (operación #{self.transaccion_id})"
