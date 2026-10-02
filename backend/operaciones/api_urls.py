"""Rutas de la API JSON de operaciones (las consume la maqueta React)."""
from django.urls import path

from . import api

urlpatterns = [
    # GET: historial. POST: crear una operación.
    path("operaciones/", api.operaciones, name="api_operaciones"),
    # Flujo de la maqueta: calcular sin guardar, y registrar al confirmar.
    path("operaciones/cotizar/", api.cotizar, name="api_operaciones_cotizar"),
    path("operaciones/confirmar/", api.confirmar, name="api_operaciones_confirmar"),
    path("operaciones/<int:pk>/", api.detalle, name="api_operaciones_detalle"),
    path("operaciones/<int:pk>/pagar/", api.pagar, name="api_operaciones_pagar"),
    path("operaciones/<int:pk>/cancelar/", api.cancelar, name="api_operaciones_cancelar"),
]
