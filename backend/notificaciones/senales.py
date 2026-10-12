"""Señales que generan notificaciones."""
from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

from cotizaciones.models import HistorialCotizacion

from . import servicio


@receiver(post_save, sender=HistorialCotizacion)
def avisar_cambio_de_cotizacion(sender, instance, created, **kwargs):
    """Cada cambio de precio queda en HistorialCotizacion (auditoría): es el
    único lugar por el que pasan todos los caminos que cambian una cotización."""
    if created:
        transaction.on_commit(lambda: servicio.cotizacion_cambiada(instance))
