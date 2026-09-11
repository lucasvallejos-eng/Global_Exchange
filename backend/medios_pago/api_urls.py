"""Rutas de la API JSON de medios de pago (las consume la maqueta)."""
from django.urls import path

from . import api

urlpatterns = [
    path("medios-pago/", api.medios_lista, name="api_medios_lista"),
    path("medios-pago/tipos/<str:clave>/", api.tipo_detalle, name="api_tipo_medio_detalle"),
    path("medios-pago/<int:pk>/", api.medios_detalle, name="api_medios_detalle"),
]
