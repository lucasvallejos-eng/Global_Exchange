"""Rutas de la API JSON de facturas (las consume la maqueta React)."""
from django.urls import path, re_path

from . import api

urlpatterns = [
    path("facturas/", api.facturas, name="api_facturas"),
    path("facturas/<int:pk>/actualizar/", api.actualizar, name="api_facturas_actualizar"),
    path("facturas/<int:pk>/reintentar/", api.reintentar, name="api_facturas_reintentar"),
    # Descarga del KuDE (PDF) o del XML firmado.
    re_path(
        r"^facturas/(?P<pk>\d+)/(?P<formato>kude|xml)/$",
        api.descargar, name="api_facturas_descargar",
    ),
]
