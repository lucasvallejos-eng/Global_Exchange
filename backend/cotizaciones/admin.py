"""Registro de Cotizacion en el panel de administración de Django."""
from django.contrib import admin

from .models import Cotizacion


@admin.register(Cotizacion)
class CotizacionAdmin(admin.ModelAdmin):
    list_display = ("moneda", "precio_compra", "precio_venta", "activa", "fecha")
    list_filter = ("activa", "moneda")
    search_fields = ("moneda__codigo", "moneda__nombre")
    date_hierarchy = "fecha"
