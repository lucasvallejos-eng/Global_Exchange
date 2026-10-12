from django.urls import path

from . import api

urlpatterns = [
    path("notificaciones/", api.lista, name="api_notificaciones"),
    path("notificaciones/preferencias/", api.preferencias, name="api_notificaciones_preferencias"),
    path("notificaciones/marcar-leidas/", api.marcar_leidas, name="api_notificaciones_marcar_leidas"),
]
