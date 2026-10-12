from django.urls import path

from . import api

urlpatterns = [
    path("pagos/configuracion/", api.configuracion, name="api_pagos_configuracion"),
]
