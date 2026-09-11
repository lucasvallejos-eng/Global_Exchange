"""Rutas de la API JSON de cotizaciones (las consume la maqueta)."""
from django.urls import path

from . import api

urlpatterns = [
    path("cotizaciones/", api.cotizaciones_lista, name="api_cotizaciones_lista"),
    path("cotizaciones/<int:pk>/", api.cotizaciones_detalle, name="api_cotizaciones_detalle"),
]
