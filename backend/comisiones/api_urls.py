"""Rutas de la API JSON de segmentos de cliente (las consume la maqueta)."""
from django.urls import path

from . import api

urlpatterns = [
    path("segmentos/", api.segmentos_lista, name="api_segmentos_lista"),
    path("segmentos/<int:pk>/", api.segmentos_detalle, name="api_segmentos_detalle"),
]
