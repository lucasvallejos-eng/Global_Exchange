"""Registro de Moneda en el panel de administración de Django."""
from django.contrib import admin

from .models import Moneda


@admin.register(Moneda)
class MonedaAdmin(admin.ModelAdmin):
    list_display = ("codigo", "nombre", "simbolo", "activo", "fecha_creacion")
    list_filter = ("activo",)
    search_fields = ("codigo", "nombre")
    ordering = ("codigo",)
