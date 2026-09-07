"""API JSON de cotizaciones para la maqueta.

Sirve dos pantallas distintas con los mismos datos:

* la de **cotizaciones vigentes**, que pide solo las activas;
* la de **historial**, que pide todas las de una moneda ordenadas por fecha.

Las pantallas de Django (``cotizaciones/views.py``) siguen sirviendo el CRUD
por plantillas; esto es lo mismo en JSON.
"""
import json
from decimal import Decimal, InvalidOperation

from django.core.exceptions import ValidationError
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

from cuentas.decorators import rol_requerido
from monedas.models import Moneda

from .models import Cotizacion

# Mismos roles que las pantallas de Django (ver cotizaciones/views.py).
GESTIONAN_TASAS = ("administrador", "analista_cambiario")
# Consultar cotizaciones lo puede hacer cualquiera que haya entrado.
CONSULTAN = ("administrador", "analista_cambiario", "cajero", "cliente")


def _a_dict(cotizacion):
    return {
        "id": cotizacion.id,
        "monedaId": cotizacion.moneda_id,
        "codigo": cotizacion.moneda.codigo,
        "nombre": cotizacion.moneda.nombre,
        "simbolo": cotizacion.moneda.simbolo,
        "precioCompra": float(cotizacion.precio_compra),
        "precioVenta": float(cotizacion.precio_venta),
        "activa": cotizacion.activa,
        "fecha": cotizacion.fecha.isoformat(),
    }


def _cuerpo(request):
    try:
        return json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return {}


def _decimal(valor):
    try:
        return Decimal(str(valor))
    except (InvalidOperation, ValueError, TypeError):
        return None


@require_http_methods(["GET", "POST"])
@rol_requerido(*CONSULTAN)
def cotizaciones_lista(request):
    if request.method == "GET":
        consulta = Cotizacion.objects.select_related("moneda")

        # ?moneda=USD  -> historial de una sola moneda
        codigo = request.GET.get("moneda")
        if codigo:
            consulta = consulta.filter(moneda__codigo=codigo.upper())

        # ?activas=1   -> solo las vigentes
        if request.GET.get("activas") == "1":
            consulta = consulta.filter(activa=True, moneda__activo=True)

        return JsonResponse([_a_dict(c) for c in consulta.order_by("-fecha")], safe=False)

    return _crear(request)


@rol_requerido(*GESTIONAN_TASAS)
def _crear(request):
    datos = _cuerpo(request)

    try:
        moneda = Moneda.objects.get(pk=datos.get("monedaId"))
    except (Moneda.DoesNotExist, ValueError, TypeError):
        return JsonResponse({"error": "Elegí una moneda válida."}, status=400)

    compra = _decimal(datos.get("precioCompra"))
    venta = _decimal(datos.get("precioVenta"))
    if compra is None or venta is None:
        return JsonResponse({"error": "Los precios de compra y venta son obligatorios."}, status=400)

    cotizacion = Cotizacion(moneda=moneda, precio_compra=compra, precio_venta=venta, activa=True)
    try:
        # full_clean() dispara clean(), donde vive RN10 (venta > compra).
        cotizacion.full_clean()
    except ValidationError as e:
        return JsonResponse(
            {"error": "; ".join(m for lista in e.message_dict.values() for m in lista)},
            status=400,
        )

    # La nueva pasa a ser la vigente; las anteriores quedan como histórico.
    moneda.cotizaciones.filter(activa=True).update(activa=False)
    cotizacion.save()
    return JsonResponse(_a_dict(cotizacion), status=201)


@require_http_methods(["GET", "PATCH", "DELETE"])
@rol_requerido(*GESTIONAN_TASAS)
def cotizaciones_detalle(request, pk):
    try:
        cotizacion = Cotizacion.objects.select_related("moneda").get(pk=pk)
    except Cotizacion.DoesNotExist:
        return JsonResponse({"error": "No existe esa cotización."}, status=404)

    if request.method == "GET":
        return JsonResponse(_a_dict(cotizacion))

    if request.method == "DELETE":
        cotizacion.delete()
        return JsonResponse({}, status=204)

    datos = _cuerpo(request)
    if "precioCompra" in datos:
        valor = _decimal(datos["precioCompra"])
        if valor is None:
            return JsonResponse({"error": "El precio de compra debe ser un número."}, status=400)
        cotizacion.precio_compra = valor
    if "precioVenta" in datos:
        valor = _decimal(datos["precioVenta"])
        if valor is None:
            return JsonResponse({"error": "El precio de venta debe ser un número."}, status=400)
        cotizacion.precio_venta = valor
    if "activa" in datos:
        cotizacion.activa = bool(datos["activa"])

    try:
        cotizacion.full_clean()
    except ValidationError as e:
        return JsonResponse(
            {"error": "; ".join(m for lista in e.message_dict.values() for m in lista)},
            status=400,
        )

    cotizacion.save()
    return JsonResponse(_a_dict(cotizacion))
