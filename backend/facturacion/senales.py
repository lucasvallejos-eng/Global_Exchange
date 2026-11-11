"""Señales que facturan las operaciones cuando quedan pagadas."""
import logging

from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

from caja.models import CompraCaja, VentaCaja
from operaciones.models import Transaccion

from . import servicio
from .models import Factura

log = logging.getLogger(__name__)


@receiver(post_save, sender=Transaccion)
def facturar_operacion_pagada(sender, instance, **kwargs):
    """Una operación de la web puede quedar pagada por varios caminos (al
    confirmarla, al pagar una pendiente, al completar el 3D Secure): todos
    guardan la ``Transaccion``, así que acá se cubren todos.

    Se factura después del ``commit``: si la operación se deshace (tarjeta
    rechazada), no queda una factura de algo que no existió. Solo se factura
    la primera vez; los reintentos son a pedido (``servicio.reintentar``).
    """
    if instance.estado != Transaccion.Estado.PAGADA:
        return
    transaction.on_commit(lambda: _facturar(Transaccion, instance.pk))


@receiver(post_save, sender=CompraCaja)
@receiver(post_save, sender=VentaCaja)
def facturar_operacion_de_caja(sender, instance, created, **kwargs):
    """Las operaciones de la caja se registran ya cobradas: se facturan al crearse."""
    if created:
        transaction.on_commit(lambda: _facturar(sender, instance.pk))


def _facturar(modelo, pk):
    try:
        campo = servicio.CAMPO_DE_ORIGEN[modelo]
        if Factura.objects.filter(**{f"{campo}_id": pk}).exists():
            return
        servicio.facturar(modelo.objects.get(pk=pk))
    except Exception:  # la factura nunca puede romper el pago
        log.exception("No se pudo facturar %s #%s", modelo.__name__, pk)
