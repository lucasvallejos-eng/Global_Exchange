"""Rutas de la API JSON de medios de pago (las consume la maqueta)."""
from django.urls import path

from . import api

urlpatterns = [
    path("medios-pago/", api.medios_lista, name="api_medios_lista"),
    # Alta de tarjetas con Stripe: preparar (SetupIntent) y registrar.
    path("medios-pago/tarjetas/preparar/", api.tarjetas_preparar, name="api_tarjetas_preparar"),
    path("medios-pago/tarjetas/", api.tarjetas_registrar, name="api_tarjetas_registrar"),
    path("medios-pago/tipos/<str:clave>/", api.tipo_detalle, name="api_tipo_medio_detalle"),
    path("medios-pago/<int:pk>/", api.medios_detalle, name="api_medios_detalle"),
]
