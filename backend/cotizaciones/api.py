"""API JSON de cotizaciones para la maqueta.

Sirve dos pantallas distintas con los mismos datos:

* La de **cotizaciones vigentes**, que solicita solo las activas.
* La de **historial**, que solicita todas las cotizaciones de una moneda ordenadas por fecha.

Las pantallas basadas en plantillas de Django (``cotizaciones/views.py``) mantienen el CRUD
tradicional; este módulo expone la misma funcionalidad formateada en JSON.
"""
import json
from datetime import timedelta
from decimal import Decimal, InvalidOperation

from django.core.exceptions import ValidationError
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from cuentas.decorators import rol_requerido
from monedas.models import Moneda

from .models import Cotizacion, HistorialCotizacion

# Mismos roles que las pantallas de Django (ver cotizaciones/views.py).
GESTIONAN_TASAS = ("administrador", "analista_cambiario")
# Consultar cotizaciones lo puede hacer cualquiera que haya entrado.
CONSULTAN = ("administrador", "analista_cambiario", "cajero", "cliente")


def _a_dict(cotizacion):
    """Serializa un objeto Cotizacion a un diccionario JSON compatible con la maqueta.

    Args:
        cotizacion (Cotizacion): Instancia de cotización a serializar.

    Returns:
        dict: Diccionario estructurado con los atributos de la cotización, datos de la
            moneda relacionada y marcas de tiempo formateadas en ISO 8601.
    """
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
        "ultimaActualizacion": cotizacion.moneda.fecha_actualizacion.isoformat(),
    }


def _cuerpo(request):
    """Decodifica el cuerpo en formato JSON de la solicitud HTTP entrante.

    Args:
        request (HttpRequest): Objeto de solicitud de Django.

    Returns:
        dict: Diccionario decodificado o un diccionario vacío ante un fallo de parseo.
    """
    try:
        return json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return {}


def _decimal(valor):
    """Convierte un valor numérico o cadena a un objeto Decimal de Python.

    Args:
        valor (int | float | str | None): Valor recibido a convertir.

    Returns:
        Decimal | None: Objeto Decimal o None si el argumento no representa un número válido.
    """
    try:
        return Decimal(str(valor))
    except (InvalidOperation, ValueError, TypeError):
        return None


def _bloqueo_por_tiempo(moneda):
    """Calcula si aplica la restricción de bloqueo por tiempo en la actualización de cotizaciones.

    Verifica si ha transcurrido menos de 1 hora desde la última modificación realizada
    sobre la tasa de la moneda especificada.

    Args:
        moneda (Moneda): Instancia de la moneda a evaluar.

    Returns:
        str | None: Mensaje descriptivo con el tiempo restante de bloqueo o None si la
        actualización ya está habilitada.
    """
    transcurrido = timezone.now() - moneda.fecha_actualizacion
    restante = timedelta(hours=1) - transcurrido
    if restante.total_seconds() <= 0:
        return None
    minutos = max(1, int((restante.total_seconds() + 59) // 60))
    return (
        "No se puede actualizar la cotización. Debe transcurrir al menos "
        f"1 hora desde el último cambio. Tiempo restante: {minutos} minutos."
    )


@require_http_methods(["GET", "POST"])
@rol_requerido(*CONSULTAN)
def cotizaciones_lista(request):
    """Endpoint para listar o registrar cotizaciones en formato JSON.

    Permite consultar cotizaciones vigentes u históricas mediante filtros por parámetro GET
    (``moneda`` y ``activas``), o registrar una nueva cotización enviando una petición POST.

    Args:
        request (HttpRequest): Objeto de la solicitud HTTP.

    Returns:
        JsonResponse: 
            - Lista de cotizaciones serializadas (200 OK en GET).
            - Cotización recién creada (201 Created en POST).
            - Objeto con descripción del error de validación o bloqueo (400 Bad Request).
    """
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
    """Función auxiliar que ejecuta la lógica de alta de una cotización.

    Valida la existencia de la moneda, los precios de compra/venta, la regla de negocio
    RN10 (venta > compra) mediante ``full_clean()``, el bloqueo de 1 hora y genera
    automáticamente una entrada en ``HistorialCotizacion``.

    Args:
        request (HttpRequest): Objeto de solicitud HTTP con payload JSON.

    Returns:
        JsonResponse: Cotización serializada (201 Created) o error estructurado (400 Bad Request).
    """
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

    if moneda.cotizaciones.filter(activa=True).exists():
        bloqueo = _bloqueo_por_tiempo(moneda)
        if bloqueo:
            return JsonResponse({"error": bloqueo}, status=400)

    # La nueva pasa a ser la vigente; las anteriores quedan como histórico.
    vigente = moneda.cotizaciones.filter(activa=True).order_by("-fecha").first()
    moneda.cotizaciones.filter(activa=True).update(activa=False)
    cotizacion.save()
    if vigente:
        HistorialCotizacion.objects.create(
            moneda=moneda,
            administrador=request.user,
            precio_compra_anterior=vigente.precio_compra,
            precio_compra_nuevo=cotizacion.precio_compra,
            precio_venta_anterior=vigente.precio_venta,
            precio_venta_nuevo=cotizacion.precio_venta,
        )
    moneda.save(update_fields=["fecha_actualizacion"])
    return JsonResponse(_a_dict(cotizacion), status=201)


@require_http_methods(["GET", "PATCH", "DELETE"])
@rol_requerido(*GESTIONAN_TASAS)
def cotizaciones_detalle(request, pk):
    """Endpoint para consultar, actualizar parcialmente o eliminar una cotización específica.

    La actualización parcial (PATCH) aplica las validaciones del bloqueo temporal de 1 hora
    si involucra cambios de precios, ejecuta ``full_clean()`` y registra el evento en
    el historial de auditoría.

    Args:
        request (HttpRequest): Objeto de la solicitud HTTP.
        pk (int): Identificador primario de la cotización.

    Returns:
        JsonResponse:
            - Cotización consultada o actualizada (200 OK).
            - Respuesta vacía tras una eliminación (204 No Content).
            - Error por validación de datos o restricción de tiempo (400 Bad Request).
            - Error por registro no encontrado (404 Not Found).
    """
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
    cambia_precio = "precioCompra" in datos or "precioVenta" in datos
    if cambia_precio:
        bloqueo = _bloqueo_por_tiempo(cotizacion.moneda)
        if bloqueo:
            return JsonResponse({"error": bloqueo}, status=400)
        precio_compra_anterior = cotizacion.precio_compra
        precio_venta_anterior = cotizacion.precio_venta
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
    if cambia_precio:
        HistorialCotizacion.objects.create(
            moneda=cotizacion.moneda,
            administrador=request.user,
            precio_compra_anterior=precio_compra_anterior,
            precio_compra_nuevo=cotizacion.precio_compra,
            precio_venta_anterior=precio_venta_anterior,
            precio_venta_nuevo=cotizacion.precio_venta,
        )
        cotizacion.moneda.save(update_fields=["fecha_actualizacion"])
    return JsonResponse(_a_dict(cotizacion))
