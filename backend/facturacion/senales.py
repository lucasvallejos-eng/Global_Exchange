"""Señal que factura las operaciones cuando quedan pagadas."""
import logging

from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

from operaciones.models import Transaccion

from . import servicio
from .models import Factura

log = logging.getLogger(__name__)


@receiver(post_save, sender=Transaccion)
def facturar_operacion_pagada(sender, instance, **kwargs):
    """Una operación puede quedar pagada por varios caminos (al confirmarla,
    al pagar una pendiente, al completar el 3D Secure): todos guardan la
    ``Transaccion``, así que acá se cubren todos.

    Se factura después del ``commit``: si la operación se deshace (tarjeta
    rechazada), no queda una factura de algo que no existió. Solo se factura
    la primera vez; los reintentos son a pedido (``servicio.reintentar``).
    """
    if instance.estado != Transaccion.Estado.PAGADA:
        return
    transaction.on_commit(lambda: _facturar(instance.pk))


def _facturar(transaccion_id):
    try:
        if Factura.objects.filter(transaccion_id=transaccion_id).exists():
            return
        servicio.facturar(Transaccion.objects.get(pk=transaccion_id))
    except Exception:  # la factura nunca puede romper el pago
        log.exception("No se pudo facturar la operación #%s", transaccion_id)
