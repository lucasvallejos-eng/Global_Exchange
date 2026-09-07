"""Rutas de la API JSON de monedas (las consume la maqueta React)."""
from django.urls import path

from . import api

urlpatterns = [
    path("monedas/", api.monedas_lista, name="api_monedas_lista"),
    path("monedas/<int:pk>/", api.monedas_detalle, name="api_monedas_detalle"),
]
