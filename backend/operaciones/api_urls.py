"""Rutas de la API JSON de operaciones (las consume la maqueta React)."""
from django.urls import path

from . import api

urlpatterns = [
    # GET: historial. POST: crear una operación.
    path("operaciones/", api.operaciones, name="api_operaciones"),
    path("operaciones/<int:pk>/", api.detalle, name="api_operaciones_detalle"),
    path("operaciones/<int:pk>/pagar/", api.pagar, name="api_operaciones_pagar"),
    path("operaciones/<int:pk>/cancelar/", api.cancelar, name="api_operaciones_cancelar"),
]
