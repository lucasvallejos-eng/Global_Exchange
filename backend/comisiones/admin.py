"""Registro de SegmentoCliente en el panel de administración de Django."""
from django.contrib import admin

from .models import SegmentoCliente


@admin.register(SegmentoCliente)
class SegmentoClienteAdmin(admin.ModelAdmin):
    list_display = ("nombre", "porcentaje_comision", "activo", "fecha_creacion")
    list_filter = ("activo",)
    search_fields = ("nombre", "descripcion")
