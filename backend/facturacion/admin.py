from django.contrib import admin

from .models import Factura


@admin.register(Factura)
class FacturaAdmin(admin.ModelAdmin):
    list_display = ("numero_completo", "estado", "receptor_nombre", "total", "fecha_creacion")
    list_filter = ("estado",)
    search_fields = ("cdc", "receptor_nombre", "receptor_documento")
    # El CDC se puede editar: es la forma de recuperar una factura sin
    # confirmar que sí se emitió (ver docs/integracion-factura-segura.md).
    readonly_fields = ("transaccion", "compra_caja", "venta_caja", "cliente", "de",
                       "fecha_creacion", "fecha_estado")
