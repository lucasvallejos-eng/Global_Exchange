"""API JSON de reportes para la maqueta (React).

Solo para el **administrador** y el **analista_cambiario**: son los roles que
la ERS habilita a ver las ganancias. Todos los pedidos aceptan los mismos
filtros por la URL: ``desde`` y ``hasta`` (``AAAA-MM-DD``, por fecha de pago),
``moneda`` (código), ``tipo`` (``COMPRA`` o ``VENTA``) y ``cliente`` (id). Lo
que no se entiende se ignora, igual que en el historial.
"""
import csv

from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_GET

from cuentas.decorators import rol_requerido
from operaciones.views import filtros_de

from . import servicio

VEN_GANANCIAS = ("administrador", "analista_cambiario")


def _filtros(request):
    """Los filtros de la URL. Se reusa el lector del historial, sin el estado:
    acá siempre son las pagadas."""
    filtros = filtros_de(request.GET)
    filtros.pop("estado")
    return filtros


def _numeros(datos):
    """Pasa los ``Decimal`` a número y las claves a camelCase para la maqueta."""
    return {
        "operaciones": datos["operaciones"],
        "volumen": float(datos["volumen"]),
        "comisiones": float(datos["comisiones"]),
        "margen": float(datos["margen"]),
        "ganancia": float(datos["ganancia"]),
    }


def _fila(transaccion):
    """Una operación con su ganancia, para la tabla del reporte."""
    ganancia = servicio.ganancia_de(transaccion)
    return {
        "id": transaccion.pk,
        "fecha": (transaccion.fecha_pago or transaccion.fecha_creacion).isoformat(),
        "cliente": transaccion.cliente.nombre,
        "tipo": transaccion.tipo,
        "tipoTexto": transaccion.get_tipo_display(),
        "moneda": transaccion.moneda.codigo,
        "montoDivisa": float(transaccion.monto_divisa),
        "tasaAplicada": float(transaccion.tasa_aplicada),
        "montoGuaranies": float(transaccion.monto_guaranies),
        "comision": float(ganancia["comision"]),
        "margen": float(ganancia["margen"]),
        "ganancia": float(ganancia["total"]),
        "medioPago": transaccion.medio_pago_descripcion or None,
    }


@require_GET
@rol_requerido(*VEN_GANANCIAS)
def transacciones(request):
    """Reporte de transacciones pagadas, cada una con su ganancia, y los totales."""
    operaciones = list(servicio.pagadas(**_filtros(request)))
    return JsonResponse({
        "operaciones": [_fila(t) for t in operaciones],
        "totales": _numeros(servicio.resumen(operaciones)["totales"]),
    })


@require_GET
@rol_requerido(*VEN_GANANCIAS)
def ganancias(request):
    """Los números del tablero de ganancias: totales y desgloses por tipo,
    moneda y día (ver ``servicio.resumen``)."""
    filtros = _filtros(request)
    datos = servicio.resumen(servicio.pagadas(**filtros), filtros["desde"], filtros["hasta"])
    return JsonResponse({
        "totales": _numeros(datos["totales"]),
        "porTipo": {tipo: _numeros(fila) for tipo, fila in datos["por_tipo"].items()},
        "porMoneda": [
            {"moneda": fila["codigo"], "montoDivisa": float(fila["monto_divisa"]), **_numeros(fila)}
            for fila in datos["por_moneda"]
        ],
        "porDia": [
            {"fecha": fila["fecha"].isoformat(), **_numeros(fila)} for fila in datos["por_dia"]
        ],
    })


@require_GET
@rol_requerido(*VEN_GANANCIAS)
def exportar(request):
    """El reporte de transacciones en CSV, para abrir en una planilla.

    Va con ``;`` como separador y con BOM: así Excel en castellano lo abre
    bien, con las columnas separadas y los acentos sanos.
    """
    respuesta = HttpResponse(content_type="text/csv; charset=utf-8")
    respuesta["Content-Disposition"] = 'attachment; filename="reporte-transacciones.csv"'
    respuesta.write("﻿")
    planilla = csv.writer(respuesta, delimiter=";")
    planilla.writerow([
        "Operación", "Fecha de pago", "Cliente", "Tipo", "Moneda", "Monto divisa",
        "Tasa aplicada", "Monto PYG", "Comisión PYG", "Margen de cambio PYG",
        "Ganancia PYG", "Medio de pago",
    ])
    for t in servicio.pagadas(**_filtros(request)):
        ganancia = servicio.ganancia_de(t)
        planilla.writerow([
            t.pk, (t.fecha_pago or t.fecha_creacion).strftime("%Y-%m-%d %H:%M"), t.cliente.nombre,
            t.get_tipo_display(), t.moneda.codigo, t.monto_divisa, t.tasa_aplicada,
            t.monto_guaranies, ganancia["comision"], ganancia["margen"], ganancia["total"],
            t.medio_pago_descripcion,
        ])
    return respuesta
