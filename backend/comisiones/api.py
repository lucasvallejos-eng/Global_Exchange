"""API JSON de segmentos de cliente (porcentajes de comisión) para la maqueta.

Las pantallas de Django (``comisiones/views.py``) siguen sirviendo el CRUD por
plantillas; esto es lo mismo en JSON para que la maqueta muestre los datos
reales de la base.

Nota sobre el modelo: ``SegmentoCliente`` guarda **un** porcentaje de comisión
por segmento (``porcentaje_comision``). La maqueta original dibujaba dos
columnas inventadas (venta y compra) que no existen en la base; acá se expone
el campo que realmente hay.
"""
import json
from decimal import Decimal, InvalidOperation

from django.core.exceptions import ValidationError
from django.db.models import Count
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

from cuentas.decorators import rol_requerido

from .models import SegmentoCliente


def _a_dict(segmento):
    """Serializa un objeto SegmentoCliente a un diccionario JSON.

    Args:
        segmento (SegmentoCliente): Instancia del segmento de cliente a serializar.

    Returns:
        dict: Diccionario estructurado con los datos del segmento de cliente,
            incluyendo comisiones, descuentos y el total de clientes asociados
            si fue anotado en la consulta.
    """
    return {
        "id": segmento.id,
        "nombre": segmento.nombre,
        "porcentajeComision": float(segmento.porcentaje_comision),
        "descuentoCompra": float(segmento.descuento_compra),
        "descripcion": segmento.descripcion,
        "activo": segmento.activo,
        "cantidadClientes": getattr(segmento, "cantidad_clientes", None),
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


def _mensaje(error):
    """Formatea los mensajes de una excepción de validación en una sola cadena.

    Args:
        error (ValidationError): Excepción devuelta por Django al validar modelos/formularios.

    Returns:
        str: Cadena con los mensajes de error concatenados por punto y coma.
    """
    return "; ".join(m for lista in error.message_dict.values() for m in lista)


@require_http_methods(["GET", "POST"])
@rol_requerido("administrador")
def segmentos_lista(request):
    """Endpoint para listar o registrar segmentos de clientes en formato JSON.

    Permite obtener el listado completo de segmentos anotados con la cantidad de clientes
    asociados (GET), o crear un nuevo segmento de cliente validando los datos requeridos (POST).

    Args:
        request (HttpRequest): Objeto de la solicitud HTTP.

    Returns:
        JsonResponse: 
            - Lista de segmentos serializados (200 OK en GET).
            - Segmento recién creado (201 Created en POST).
            - Objeto con la descripción del error de validación o tipo numérico (400 Bad Request).
    """
    if request.method == "GET":
        segmentos = SegmentoCliente.objects.annotate(cantidad_clientes=Count("clientes"))
        return JsonResponse([_a_dict(s) for s in segmentos], safe=False)

    datos = _cuerpo(request)
    segmento = SegmentoCliente(
        nombre=(datos.get("nombre") or "").strip(),
        descripcion=(datos.get("descripcion") or "").strip(),
        activo=bool(datos.get("activo", True)),
    )
    try:
        segmento.porcentaje_comision = Decimal(str(datos.get("porcentajeComision", "0")))
        segmento.descuento_compra = Decimal(str(datos.get("descuentoCompra", "0")))
    except (InvalidOperation, ValueError):
        return JsonResponse({"error": "El porcentaje debe ser un número."}, status=400)

    try:
        # full_clean() dispara el clean() del modelo, que evita nombres repetidos.
        segmento.full_clean()
    except ValidationError as e:
        return JsonResponse({"error": _mensaje(e)}, status=400)

    segmento.save()
    return JsonResponse(_a_dict(segmento), status=201)


@require_http_methods(["GET", "PATCH", "DELETE"])
@rol_requerido("administrador")
def segmentos_detalle(request, pk):
    """Endpoint para consultar, actualizar parcialmente o borrar un segmento de cliente específico.

    En la actualización parcial (PATCH) valida el formato numérico de las comisiones y descuentos,
    ejecuta `full_clean()` y persiste las modificaciones. En la eliminación (DELETE) verifica que el
    segmento no posea clientes asociados debido a la restricción `PROTECT`.

    Args:
        request (HttpRequest): Objeto de la solicitud HTTP.
        pk (int): Identificador primario del segmento de cliente.

    Returns:
        JsonResponse:
            - Segmento consultado o actualizado (200 OK).
            - Respuesta vacía tras una eliminación (204 No Content).
            - Error por validación de datos o por intentar borrar un segmento en uso (400 Bad Request).
            - Error por registro no encontrado (404 Not Found).
    """
    try:
        segmento = SegmentoCliente.objects.get(pk=pk)
    except SegmentoCliente.DoesNotExist:
        return JsonResponse({"error": "No existe ese segmento."}, status=404)

    if request.method == "GET":
        return JsonResponse(_a_dict(segmento))

    if request.method == "DELETE":
        # PROTECT en Cliente.segmento impide borrar uno que esté en uso.
        if segmento.clientes.exists():
            return JsonResponse(
                {"error": "No se puede borrar: hay clientes asignados a este segmento."},
                status=400,
            )
        segmento.delete()
        return JsonResponse({}, status=204)

    datos = _cuerpo(request)
    if "nombre" in datos:
        segmento.nombre = (datos["nombre"] or "").strip()
    if "descripcion" in datos:
        segmento.descripcion = (datos["descripcion"] or "").strip()
    if "activo" in datos:
        segmento.activo = bool(datos["activo"])
    if "porcentajeComision" in datos:
        try:
            segmento.porcentaje_comision = Decimal(str(datos["porcentajeComision"]))
        except (InvalidOperation, ValueError):
            return JsonResponse({"error": "El porcentaje debe ser un número."}, status=400)
    if "descuentoCompra" in datos:
        try:
            segmento.descuento_compra = Decimal(str(datos["descuentoCompra"]))
        except (InvalidOperation, ValueError):
            return JsonResponse({"error": "El descuento de compra debe ser un número."}, status=400)

    try:
        segmento.full_clean()
    except ValidationError as e:
        return JsonResponse({"error": _mensaje(e)}, status=400)

    segmento.save()
    return JsonResponse(_a_dict(segmento))
