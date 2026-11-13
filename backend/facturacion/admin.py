from django.contrib import admin

from .models import Factura, SecuenciaFactura


@admin.register(Factura)
class FacturaAdmin(admin.ModelAdmin):
    list_display = ("numero_completo", "estado", "receptor_nombre", "total", "fecha_creacion")
    list_filter = ("estado",)
    search_fields = ("cdc", "receptor_nombre", "receptor_documento")
    # El CDC se puede editar: es la forma de recuperar una factura sin
    # confirmar que sí se emitió (ver docs/integracion-factura-segura.md).
    readonly_fields = ("transaccion", "compra_caja", "venta_caja", "cliente", "de",
                       "fecha_creacion", "fecha_estado")


@admin.register(SecuenciaFactura)
class SecuenciaFacturaAdmin(admin.ModelAdmin):
    list_display = (
        "formato_talonario",
        "ultimo_numero",
        "proximo_numero",
        "numero_fin",
        "disponibles",
        "activo",
        "fecha_actualizacion",
    )
    list_filter = ("activo", "establecimiento", "punto_expedicion")
    readonly_fields = ("fecha_actualizacion",)

    @admin.display(description="Talonario")
    def formato_talonario(self, obj):
        return f"{obj.establecimiento}-{obj.punto_expedicion} ({obj.numero_inicio} a {obj.numero_fin})"

    @admin.display(description="Próxima Factura")
    def proximo_numero(self, obj):
        return obj.formato_factura(obj.siguiente_numero)

    @admin.display(description="Disponibles")
    def disponibles(self, obj):
        return obj.cantidad_disponible

