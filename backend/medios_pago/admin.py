"""Registro de MedioPago en el panel de administración de Django."""
from django.contrib import admin

from .models import MedioPago


@admin.register(MedioPago)
class MedioPagoAdmin(admin.ModelAdmin):
    list_display = ("alias", "tipo", "usuario", "banco_o_proveedor", "activo", "fecha_creacion")
    list_filter = ("tipo", "activo")
    search_fields = ("alias", "numero_cuenta_o_tarjeta", "usuario__username")
