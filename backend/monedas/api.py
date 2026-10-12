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

from cotizaciones.models import Cotizacion, HistorialCotizacion
from cuentas.decorators import rol_requerido

from .models import Moneda, Denominacion

# Quiénes administran monedas y denominaciones, igual que en las pantallas de Django.
GESTIONAN_MONEDAS = ("administrador", "analista_cambiario")


def _cotizacion_vigente(moneda):
    """Última cotización activa de la moneda, o None si todavía no tiene."""
    return moneda.cotizaciones.filter(activa=True).order_by("-fecha").first()


def _denominacion_a_dict(denominacion):
    """Serializa una denominación a diccionario JSON."""
    return {
        "id": denominacion.id,
        "monedaId": denominacion.moneda_id,
        "moneda_id": denominacion.moneda_id,
        "monedaCodigo": denominacion.moneda.codigo,
        "monedaNombre": denominacion.moneda.nombre,
        "simbolo": denominacion.moneda.simbolo,
        "valor": float(denominacion.valor),
        "creadoEn": denominacion.creado_en.isoformat() if denominacion.creado_en else None,
        "actualizadoEn": denominacion.actualizado_en.isoformat() if denominacion.actualizado_en else None,
        "creado_en": denominacion.creado_en.isoformat() if denominacion.creado_en else None,
        "actualizado_en": denominacion.actualizado_en.isoformat() if denominacion.actualizado_en else None,
    }


def _a_dict(moneda):
    cotizacion = _cotizacion_vigente(moneda)
    denominaciones = list(moneda.denominaciones.all().order_by("valor"))
    return {
        "id": moneda.id,
        "codigo": moneda.codigo,
        "nombre": moneda.nombre,
        "simbolo": moneda.simbolo,
        "activo": moneda.activo,
        "precioCompra": float(cotizacion.precio_compra) if cotizacion else None,
        "precioVenta": float(cotizacion.precio_venta) if cotizacion else None,
        "ultimaActualizacion": (
            moneda.fecha_actualizacion.isoformat() if cotizacion else None
        ),
        "denominaciones": [_denominacion_a_dict(d) for d in denominaciones],
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


def _guardar_cotizacion(moneda, compra, venta, administrador=None):
    """Crea una cotización nueva si vinieron ambos precios.

    Devuelve el mensaje de error si no cumple RN10 (venta > compra), o None si
    salió bien. La validación se delega a ``Cotizacion.clean()`` para no repetir
    la regla en dos lugares.
    """
    if compra is None or venta is None:
        return None
    vigente = moneda.cotizaciones.filter(activa=True).order_by("-fecha").first()
    # Si los precios no cambian (p. ej. solo se editó el nombre o el estado)
    # no hay cotización nueva que registrar.
    if vigente and vigente.precio_compra == compra and vigente.precio_venta == venta:
        return None

    nueva = Cotizacion(moneda=moneda, precio_compra=compra, precio_venta=venta, activa=True)
    try:
        nueva.full_clean()
    except ValidationError as e:
        return "; ".join(m for lista in e.message_dict.values() for m in lista)

    # La vigente pasa a ser la nueva: las anteriores quedan como histórico.
    moneda.cotizaciones.filter(activa=True).update(activa=False)
    nueva.save()
    if vigente and administrador:
        HistorialCotizacion.objects.create(
            moneda=moneda,
            administrador=administrador,
            precio_compra_anterior=vigente.precio_compra,
            precio_compra_nuevo=nueva.precio_compra,
            precio_venta_anterior=vigente.precio_venta,
            precio_venta_nuevo=nueva.precio_venta,
        )
    moneda.save(update_fields=["fecha_actualizacion"])
    return None


@require_http_methods(["GET", "POST"])
def monedas_lista(request):
    if request.method == "GET":
        monedas = Moneda.objects.all().prefetch_related("denominaciones").order_by("codigo")
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

    error = _guardar_cotizacion(
        moneda,
        _decimal(datos.get("precioCompra")),
        _decimal(datos.get("precioVenta")),
        request.user,
    )
    if error:
        # Sin cotización válida la moneda no sirve: se deshace el alta.
        moneda.delete()
        return JsonResponse({"error": error}, status=400)

    return JsonResponse(_a_dict(moneda), status=201)


@require_http_methods(["GET", "PATCH", "DELETE"])
def monedas_detalle(request, pk):
    try:
        moneda = Moneda.objects.prefetch_related("denominaciones").get(pk=pk)
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

    error = _guardar_cotizacion(
        moneda,
        _decimal(datos.get("precioCompra")),
        _decimal(datos.get("precioVenta")),
        request.user,
    )
    if error:
        return JsonResponse({"error": error}, status=400)

    return JsonResponse(_a_dict(moneda))


@rol_requerido(*GESTIONAN_MONEDAS)
def _borrar(request, moneda):
    moneda.delete()
    return JsonResponse({}, status=204)


# ==========================================
# Endpoints de Denominaciones
# ==========================================

@require_http_methods(["GET", "POST"])
def denominaciones_lista(request):
    """Listado o creación de denominaciones."""
    if request.method == "GET":
        qs = Denominacion.objects.select_related("moneda").all()
        moneda_id = request.GET.get("moneda_id") or request.GET.get("monedaId")
        if moneda_id:
            qs = qs.filter(moneda_id=moneda_id)
        qs = qs.order_by("moneda__codigo", "valor")
        return JsonResponse([_denominacion_a_dict(d) for d in qs], safe=False)
    return _crear_denominacion(request)


@rol_requerido(*GESTIONAN_MONEDAS)
def _crear_denominacion(request):
    datos = _cuerpo(request)
    moneda_id = datos.get("moneda_id") or datos.get("monedaId") or datos.get("moneda")
    raw_valor = datos.get("valor")

    if moneda_id is None or str(moneda_id).strip() == "":
        return JsonResponse({"error": "Debe seleccionar una moneda válida."}, status=400)

    try:
        moneda = Moneda.objects.get(pk=moneda_id)
    except (Moneda.DoesNotExist, ValueError, TypeError):
        return JsonResponse({"error": "La moneda especificada no existe."}, status=404)

    valor = _decimal(raw_valor)
    if valor is None:
        return JsonResponse({"error": "El valor nominal es obligatorio y debe ser un número."}, status=400)
    if valor <= 0:
        return JsonResponse({"error": "El valor nominal debe ser mayor a 0."}, status=400)

    if Denominacion.objects.filter(moneda=moneda, valor=valor).exists():
        return JsonResponse(
            {"error": f"Ya existe la denominación {valor} para la moneda {moneda.codigo}."},
            status=400,
        )

    denominacion = Denominacion(moneda=moneda, valor=valor)
    try:
        denominacion.full_clean()
    except ValidationError as e:
        return JsonResponse({"error": "; ".join(m for lista in e.message_dict.values() for m in lista)}, status=400)

    denominacion.save()
    return JsonResponse(_denominacion_a_dict(denominacion), status=201)


@require_http_methods(["GET", "PUT", "PATCH", "DELETE"])
def denominaciones_detalle(request, pk):
    """Consulta, actualización o eliminación de una denominación."""
    try:
        denominacion = Denominacion.objects.select_related("moneda").get(pk=pk)
    except Denominacion.DoesNotExist:
        return JsonResponse({"error": "No existe esa denominación."}, status=404)

    if request.method == "GET":
        return JsonResponse(_denominacion_a_dict(denominacion))
    if request.method in ("PUT", "PATCH"):
        return _actualizar_denominacion(request, denominacion)
    return _borrar_denominacion(request, denominacion)


@rol_requerido(*GESTIONAN_MONEDAS)
def _actualizar_denominacion(request, denominacion):
    datos = _cuerpo(request)

    if "moneda_id" in datos or "monedaId" in datos:
        moneda_id = datos.get("moneda_id") or datos.get("monedaId")
        try:
            denominacion.moneda = Moneda.objects.get(pk=moneda_id)
        except (Moneda.DoesNotExist, ValueError, TypeError):
            return JsonResponse({"error": "La moneda especificada no existe."}, status=404)

    if "valor" in datos:
        valor = _decimal(datos.get("valor"))
        if valor is None:
            return JsonResponse({"error": "El valor nominal debe ser un número válido."}, status=400)
        if valor <= 0:
            return JsonResponse({"error": "El valor nominal debe ser mayor a 0."}, status=400)

        if Denominacion.objects.filter(moneda=denominacion.moneda, valor=valor).exclude(pk=denominacion.pk).exists():
            return JsonResponse(
                {"error": f"Ya existe la denominación {valor} para la moneda {denominacion.moneda.codigo}."},
                status=400,
            )
        denominacion.valor = valor

    try:
        denominacion.full_clean()
    except ValidationError as e:
        return JsonResponse({"error": "; ".join(m for lista in e.message_dict.values() for m in lista)}, status=400)

    denominacion.save()
    return JsonResponse(_denominacion_a_dict(denominacion))


@rol_requerido(*GESTIONAN_MONEDAS)
def _borrar_denominacion(request, denominacion):
    denominacion.delete()
    return JsonResponse({}, status=204)

