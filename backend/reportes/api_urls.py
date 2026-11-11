"""Rutas de la API JSON de reportes (las consume la maqueta React)."""
from django.urls import path

from . import api

urlpatterns = [
    path("reportes/transacciones/", api.transacciones, name="api_reportes_transacciones"),
    path("reportes/transacciones/exportar/", api.exportar, name="api_reportes_exportar"),
    path("reportes/ganancias/", api.ganancias, name="api_reportes_ganancias"),
]
