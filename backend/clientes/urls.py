from django.urls import path

from . import views

urlpatterns = [
    path("clientes/", views.clientes_lista, name="clientes_lista"),
    path("clientes/<int:pk>/", views.clientes_detalle, name="clientes_detalle"),
    path("usuarios/", views.usuarios_lista, name="usuarios_lista"),
]
