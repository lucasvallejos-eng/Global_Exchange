"""API JSON de cotizaciones para la maqueta.

Sirve dos pantallas distintas con los mismos datos:

* La de **cotizaciones vigentes**, que solicita solo las activas.
* La de **historial**, que solicita todas las cotizaciones de una moneda ordenadas por fecha.

Las pantallas basadas en plantillas de Django (``cotizaciones/views.py``) mantienen el CRUD
tradicional; este módulo expone la misma funcionalidad formateada en JSON.
"""
import json
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation

from django.core.exceptions import ValidationError
from django.http import HttpResponse, JsonResponse
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

        orden = (request.GET.get("orden") or "desc").lower()
        if orden in ("asc", "cronologico"):
            consulta = consulta.order_by("fecha", "id")
        else:
            consulta = consulta.order_by("-fecha", "-id")

        # ?activas=1   -> solo las vigentes: la activa más reciente de cada
        # moneda, la misma definición con la que se opera
        # (operaciones.servicios.cotizacion_vigente). Si una moneda quedó con
        # más de una activa, mostrar otra haría operar con un precio distinto
        # del que se ve.
        if request.GET.get("activas") == "1":
            vigentes = {}
            for cotizacion in consulta.filter(activa=True, moneda__activo=True):
                vigentes.setdefault(cotizacion.moneda_id, cotizacion)
            return JsonResponse([_a_dict(c) for c in vigentes.values()], safe=False)

        return JsonResponse([_a_dict(c) for c in consulta], safe=False)

    return _crear(request)


@require_http_methods(["GET"])
@rol_requerido(*CONSULTAN)
def cotizaciones_evolucion(request):
    """Endpoint para obtener la evolución histórica de tasas y su proyección semanal.

    Retorna los puntos ordenados cronológicamente desde la fecha inicial
    (ej. 1 mes atrás: 13/10/2026) hasta hoy (13/11/2026), más una proyección
    de 7 días hacia adelante (hasta 20/11/2026) según las reglas de negocio.
    """
    codigo = (request.GET.get("moneda") or "USD").upper()
    rango = (request.GET.get("rango") or "1M").upper()

    moneda = Moneda.objects.filter(codigo=codigo, activo=True).first()
    if not moneda:
        moneda = Moneda.objects.filter(activo=True, es_local=False).first()
    if not moneda:
        return JsonResponse({"error": "No hay monedas activas disponibles."}, status=404)

    cotizaciones_db = list(
        Cotizacion.objects.filter(moneda=moneda).order_by("fecha", "id")
    )
    if not cotizaciones_db:
        return JsonResponse({"error": f"No hay cotizaciones para {moneda.codigo}."}, status=404)

    ultima_vigente = (
        Cotizacion.objects.filter(moneda=moneda, activa=True).order_by("-fecha").first()
        or cotizaciones_db[-1]
    )

    hoy = timezone.localdate()

    if rango == "1M":
        fecha_inicio = hoy - timedelta(days=31)
        paso_dias = 1
    elif rango == "6M":
        fecha_inicio = hoy - timedelta(days=180)
        paso_dias = 3
    elif rango == "YTD":
        fecha_inicio = date(hoy.year, 1, 1)
        paso_dias = max(1, (hoy - fecha_inicio).days // 30)
    elif rango == "1A":
        fecha_inicio = hoy - timedelta(days=365)
        paso_dias = 7
    else:  # MAX
        fecha_inicio = cotizaciones_db[0].fecha.date() if cotizaciones_db else (hoy - timedelta(days=365))
        paso_dias = max(1, (hoy - fecha_inicio).days // 40)

    if fecha_inicio >= hoy:
        fecha_inicio = hoy - timedelta(days=31)

    puntos_historicos = []
    d = fecha_inicio
    while d <= hoy:
        cotiz = None
        for c in reversed(cotizaciones_db):
            if c.fecha.date() <= d:
                cotiz = c
                break
        if cotiz is None:
            cotiz = cotizaciones_db[0]

        puntos_historicos.append({
            "date": d.isoformat(),
            "label": d.strftime("%d/%m/%Y"),
            "dia": d.strftime("%d %b"),
            "value": float(cotiz.precio_venta),
            "compra": float(cotiz.precio_compra),
            "esProyeccion": False,
        })
        d += timedelta(days=paso_dias)

    # Aseguramos que el punto final histórico sea exactamente 'hoy'
    if not puntos_historicos or puntos_historicos[-1]["date"] != hoy.isoformat():
        puntos_historicos.append({
            "date": hoy.isoformat(),
            "label": hoy.strftime("%d/%m/%Y"),
            "dia": hoy.strftime("%d %b"),
            "value": float(ultima_vigente.precio_venta),
            "compra": float(ultima_vigente.precio_compra),
            "esProyeccion": False,
        })

    # Proyección de 1 semana (7 días hacia adelante)
    puntos_proyeccion = []
    tasa_base_venta = float(ultima_vigente.precio_venta)
    tasa_base_compra = float(ultima_vigente.precio_compra)
    for i in range(1, 8):
        dia_futuro = hoy + timedelta(days=i)
        incremento = round(tasa_base_venta * (0.0005 * i), 0)
        puntos_proyeccion.append({
            "date": dia_futuro.isoformat(),
            "label": dia_futuro.strftime("%d/%m/%Y"),
            "dia": dia_futuro.strftime("%d %b"),
            "value": tasa_base_venta + incremento,
            "compra": tasa_base_compra + incremento,
            "esProyeccion": True,
        })

    valores_hist = [p["value"] for p in puntos_historicos]
    min_val = min(valores_hist) if valores_hist else tasa_base_venta
    max_val = max(valores_hist) if valores_hist else tasa_base_venta

    return JsonResponse({
        "moneda": moneda.codigo,
        "nombre": moneda.nombre,
        "simbolo": moneda.simbolo,
        "rango": rango,
        "fechaActual": hoy.isoformat(),
        "fechaActualFormateada": hoy.strftime("%d/%m/%Y"),
        "valorActual": tasa_base_venta,
        "valorCompraActual": tasa_base_compra,
        "historico": puntos_historicos,
        "proyeccion": puntos_proyeccion,
        "rangoFechas": {
            "inicio": fecha_inicio.strftime("%d/%m/%Y"),
            "fin": hoy.strftime("%d/%m/%Y"),
            "proyeccionHasta": (hoy + timedelta(days=7)).strftime("%d/%m/%Y"),
        },
        "resumen": {
            "minimo": min_val,
            "maximo": max_val,
            "proyeccionFin": puntos_proyeccion[-1]["value"] if puntos_proyeccion else tasa_base_venta,
        },
    })


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
        return HttpResponse(status=204)

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
