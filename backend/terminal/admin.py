"""Las terminales y sus billetes se cargan desde el admin de Django."""
from django.contrib import admin

from .models import BilleteTerminal, OperacionTerminal, Terminal


class BilleteTerminalInline(admin.TabularInline):
    model = BilleteTerminal
    extra = 0


@admin.register(Terminal)
class TerminalAdmin(admin.ModelAdmin):
    list_display = ("nombre", "ubicacion", "activa")
    inlines = [BilleteTerminalInline]


@admin.register(OperacionTerminal)
class OperacionTerminalAdmin(admin.ModelAdmin):
    list_display = ("codigo", "transaccion", "estado", "terminal", "entrega", "fecha_creacion")
    list_filter = ("estado", "terminal")
    readonly_fields = ("transaccion", "codigo", "depositado", "entregado", "fecha_creacion", "fecha_fin")
