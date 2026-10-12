from django.contrib import admin

from .models import Notificacion, PreferenciaNotificaciones


@admin.register(Notificacion)
class NotificacionAdmin(admin.ModelAdmin):
    list_display = ("fecha", "usuario", "tipo", "titulo", "leida")
    list_filter = ("tipo", "leida")
    search_fields = ("titulo", "mensaje", "usuario__username")


@admin.register(PreferenciaNotificaciones)
class PreferenciaNotificacionesAdmin(admin.ModelAdmin):
    list_display = ("usuario", "compras", "ventas", "cotizaciones")
