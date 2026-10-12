from django.urls import path

from . import views

urlpatterns = [
    path("", views.listar_facturas, name="listar_facturas"),
    path("<int:pk>/", views.detalle_factura, name="detalle_factura"),
    path("<int:pk>/actualizar/", views.actualizar_factura, name="actualizar_factura"),
    path("<int:pk>/reintentar/", views.reintentar_factura, name="reintentar_factura"),
]
