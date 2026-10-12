from django.contrib import admin

from .models import Cliente


@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ("nombre", "tipo", "ruc", "correo", "created_at")
    filter_horizontal = ("usuarios",)
    search_fields = ("nombre", "correo", "ruc")
