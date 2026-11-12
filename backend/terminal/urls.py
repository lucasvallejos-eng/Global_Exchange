from django.urls import path

from . import views

urlpatterns = [
    path("", views.elegir_terminal, name="terminal_inicio"),
    path("estado/", views.estado, name="terminal_estado"),
    path("reservar/<int:pk>/", views.reservar, name="terminal_reservar"),
    path("<int:terminal_id>/", views.ingresar_codigo, name="terminal_codigo"),
    path("<int:terminal_id>/<str:codigo>/", views.operacion, name="terminal_operacion"),
    path("<int:terminal_id>/<str:codigo>/cancelar/", views.cancelar, name="terminal_cancelar"),
]
