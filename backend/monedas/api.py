"""API JSON de monedas para la maqueta (React).

Las pantallas de Django (``monedas/views.py``) siguen sirviendo el CRUD por
plantillas. Esto es lo mismo, pero en JSON, para que la maqueta muestre y edite
los datos reales de la base en vez de una lista escrita a mano.

Cada moneda viaja junto a su **cotización vigente** (la última activa), porque
la pantalla de la maqueta muestra las dos cosas en la misma fila. Guardar una
moneda con precios crea una cotización nueva en vez de editar la anterior: así
queda el histórico, que es lo que espera ``cotizaciones.Cotizacion``.
"""
import json
from decimal import Decimal, InvalidOperation

from django.core.exceptions import ValidationError
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

from cotizaciones.models import Cotizacion
from cuentas.decorators import rol_requerido

from .models import Moneda

# Quiénes administran monedas, igual que en las pantallas de Django.
GESTIONAN_MONEDAS = ("administrador", "analista_cambiario")


def _cotizacion_vigente(moneda):
    """Última cotización activa de la moneda, o None si todavía no tiene."""
    return moneda.cotizaciones.filter(activa=True).order_by("-fecha").first()


def _a_dict(moneda):
    cotizacion = _cotizacion_vigente(moneda)
    return {
        "id": moneda.id,
        "codigo": moneda.codigo,
        "nombre": moneda.nombre,
        "simbolo": moneda.simbolo,
        "activo": moneda.activo,
        "precioCompra": float(cotizacion.precio_compra) if cotizacion else None,
        "precioVenta": float(cotizacion.precio_venta) if cotizacion else None,
    }


def _cuerpo(request):
    try:
        return json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return {}


def _decimal(valor):
    """Convierte a Decimal lo que llega del navegador; None si no es un número."""
    if valor is None or valor == "":
        return None
    try:
        return Decimal(str(valor))
    except (InvalidOperation, ValueError):
        return None


def _guardar_cotizacion(moneda, compra, venta):
    """Crea una cotización nueva si vinieron ambos precios.

    Devuelve el mensaje de error si no cumple RN10 (venta > compra), o None si
    salió bien. La validación se delega a ``Cotizacion.clean()`` para no repetir
    la regla en dos lugares.
    """
    if compra is None or venta is None:
        return None

    nueva = Cotizacion(moneda=moneda, precio_compra=compra, precio_venta=venta, activa=True)
    try:
        nueva.full_clean()
    except ValidationError as e:
        return "; ".join(m for lista in e.message_dict.values() for m in lista)

    # La vigente pasa a ser la nueva: las anteriores quedan como histórico.
    moneda.cotizaciones.filter(activa=True).update(activa=False)
    nueva.save()
    return None


@require_http_methods(["GET", "POST"])
def monedas_lista(request):
    if request.method == "GET":
        monedas = Moneda.objects.all().order_by("codigo")
        return JsonResponse([_a_dict(m) for m in monedas], safe=False)
    return _crear(request)


@rol_requerido(*GESTIONAN_MONEDAS)
def _crear(request):
    datos = _cuerpo(request)
    codigo = (datos.get("codigo") or "").strip().upper()
    nombre = (datos.get("nombre") or "").strip()

    if not codigo or not nombre:
        return JsonResponse({"error": "El código y el nombre son obligatorios."}, status=400)
    if Moneda.objects.filter(codigo=codigo).exists():
        return JsonResponse({"error": f"Ya existe una moneda con el código {codigo}."}, status=400)

    moneda = Moneda.objects.create(
        codigo=codigo,
        nombre=nombre,
        simbolo=(datos.get("simbolo") or codigo).strip(),
        activo=bool(datos.get("activo", True)),
    )

    error = _guardar_cotizacion(moneda, _decimal(datos.get("precioCompra")), _decimal(datos.get("precioVenta")))
    if error:
        # Sin cotización válida la moneda no sirve: se deshace el alta.
        moneda.delete()
        return JsonResponse({"error": error}, status=400)

    return JsonResponse(_a_dict(moneda), status=201)


@require_http_methods(["GET", "PATCH", "DELETE"])
def monedas_detalle(request, pk):
    try:
        moneda = Moneda.objects.get(pk=pk)
    except Moneda.DoesNotExist:
        return JsonResponse({"error": "No existe esa moneda."}, status=404)

    if request.method == "GET":
        return JsonResponse(_a_dict(moneda))
    if request.method == "PATCH":
        return _actualizar(request, moneda)
    return _borrar(request, moneda)


@rol_requerido(*GESTIONAN_MONEDAS)
def _actualizar(request, moneda):
    datos = _cuerpo(request)

    if "nombre" in datos:
        moneda.nombre = (datos["nombre"] or "").strip()
    if "simbolo" in datos:
        moneda.simbolo = (datos["simbolo"] or "").strip()
    if "activo" in datos:
        moneda.activo = bool(datos["activo"])
    moneda.save()

    error = _guardar_cotizacion(moneda, _decimal(datos.get("precioCompra")), _decimal(datos.get("precioVenta")))
    if error:
        return JsonResponse({"error": error}, status=400)

    return JsonResponse(_a_dict(moneda))


@rol_requerido(*GESTIONAN_MONEDAS)
def _borrar(request, moneda):
    moneda.delete()
    return JsonResponse({}, status=204)
