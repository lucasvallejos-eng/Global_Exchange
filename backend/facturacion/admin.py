from django.contrib import admin

from .models import Factura


@admin.register(Factura)
class FacturaAdmin(admin.ModelAdmin):
    list_display = ("numero_completo", "estado", "receptor_nombre", "total", "fecha_creacion")
    list_filter = ("estado",)
    search_fields = ("cdc", "receptor_nombre", "receptor_documento")
    readonly_fields = ("transaccion", "cdc", "de", "fecha_creacion", "fecha_estado")
