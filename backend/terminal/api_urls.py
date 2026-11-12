"""Rutas de la API JSON de la terminal de autoservicio (las consume la maqueta React)."""
from django.urls import path

from . import api

urlpatterns = [
    # GET: las reservas del usuario. POST: reservar una operación nueva.
    path("terminal/reservas/", api.reservas, name="api_terminal_reservas"),
    path("terminal/terminales/", api.terminales, name="api_terminal_terminales"),
]
