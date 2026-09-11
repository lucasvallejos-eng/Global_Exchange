"""Registro de Cotizacion en el panel de administración de Django."""
from datetime import timedelta

from django.contrib import admin
from django.core.exceptions import ValidationError
from django.utils import timezone

from .models import Cotizacion, HistorialCotizacion


@admin.register(Cotizacion)
class CotizacionAdmin(admin.ModelAdmin):
    list_display = ("moneda", "precio_compra", "precio_venta", "activa", "fecha")
    list_filter = ("activa", "moneda")
    search_fields = ("moneda__codigo", "moneda__nombre")
    date_hierarchy = "fecha"

    def save_model(self, request, obj, form, change):
        anterior = None
        if change:
            anterior = Cotizacion.objects.get(pk=obj.pk)
            restante = timedelta(hours=1) - (
                timezone.now() - obj.moneda.fecha_actualizacion
            )
            if (
                (obj.precio_compra != anterior.precio_compra
                 or obj.precio_venta != anterior.precio_venta)
                and restante.total_seconds() > 0
            ):
                minutos = max(1, int((restante.total_seconds() + 59) // 60))
                raise ValidationError(
                    "No se puede actualizar la cotización. Debe transcurrir "
                    f"al menos 1 hora desde el último cambio. Tiempo restante: "
                    f"{minutos} minutos."
                )

        super().save_model(request, obj, form, change)
        if anterior and (
            obj.precio_compra != anterior.precio_compra
            or obj.precio_venta != anterior.precio_venta
        ):
            HistorialCotizacion.objects.create(
                moneda=obj.moneda,
                administrador=request.user,
                precio_compra_anterior=anterior.precio_compra,
                precio_compra_nuevo=obj.precio_compra,
                precio_venta_anterior=anterior.precio_venta,
                precio_venta_nuevo=obj.precio_venta,
            )
            obj.moneda.save(update_fields=["fecha_actualizacion"])


@admin.register(HistorialCotizacion)
class HistorialCotizacionAdmin(admin.ModelAdmin):
    list_display = (
        "moneda",
        "administrador",
        "precio_compra_anterior",
        "precio_compra_nuevo",
        "precio_venta_anterior",
        "precio_venta_nuevo",
        "fecha_registro",
    )
    list_filter = ("moneda", "administrador")
    date_hierarchy = "fecha_registro"
    readonly_fields = [field.name for field in HistorialCotizacion._meta.fields]
