from django.urls import path

from . import views

urlpatterns = [
    path("", views.historial, name="historial_operaciones"),
    path("nueva/", views.operar, name="operar"),
    path("<int:pk>/", views.detalle_operacion, name="detalle_operacion"),
    path("<int:pk>/pagar/", views.pagar_operacion, name="pagar_operacion"),
    path("<int:pk>/cancelar/", views.cancelar_operacion, name="cancelar_operacion"),
]
