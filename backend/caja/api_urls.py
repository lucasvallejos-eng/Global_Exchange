from django.urls import path

from . import api

urlpatterns = [
    path("cajero/denominaciones-por-moneda/", api.denominaciones_por_moneda, name="api_caja_denominaciones"),
    path("caja/estado-diario/", api.estado_diario, name="api_caja_estado_diario"),
    path("caja/apertura/", api.apertura, name="api_caja_apertura"),
    path("caja/compras", api.compra, name="api_caja_compras"),
    path("caja/compras/", api.compra),
    path("caja/ventas", api.venta, name="api_caja_ventas"),
    path("caja/ventas/", api.venta),
    path("caja/clientes/<int:pk>/tarjetas/", api.tarjetas_del_cliente, name="api_caja_tarjetas_cliente"),
    path("caja/historial/", api.historial, name="api_caja_historial"),
    path("caja/resumen-cierre/", api.resumen_cierre, name="api_caja_resumen_cierre"),
    path("caja/cierre/", api.cierre, name="api_caja_cierre"),
]
