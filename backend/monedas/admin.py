"""Registro de Moneda en el panel de administración de Django."""
from django.contrib import admin

from .models import Moneda, Denominacion


class DenominacionInline(admin.TabularInline):
    model = Denominacion
    extra = 1
    fields = ("valor", "creado_en", "actualizado_en")
    readonly_fields = ("creado_en", "actualizado_en")


@admin.register(Moneda)
class MonedaAdmin(admin.ModelAdmin):
    list_display = ("codigo", "nombre", "simbolo", "activo", "fecha_creacion")
    list_filter = ("activo",)
    search_fields = ("codigo", "nombre")
    ordering = ("codigo",)
    inlines = [DenominacionInline]


@admin.register(Denominacion)
class DenominacionAdmin(admin.ModelAdmin):
    list_display = ("moneda", "valor", "creado_en", "actualizado_en")
    list_filter = ("moneda",)
    search_fields = ("moneda__codigo", "moneda__nombre", "valor")
    ordering = ("moneda", "valor")

