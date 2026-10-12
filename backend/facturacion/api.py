"""API JSON de facturas para la maqueta (React).

Cada uno ve las facturas de las operaciones que puede ver (la misma regla del
historial: ``operaciones.servicios.transacciones_visibles``). Las descargas
pasan por acá: el backend baja el archivo de Factura Segura y lo reenvía, así
el token nunca llega al navegador.
"""
from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_GET, require_POST

from cuentas.decorators import rol_requerido
from operaciones import servicios as operaciones

from . import servicio
from .models import Factura
from .servicio import ErrorFacturaSegura, FacturaInvalida

TODOS_LOS_ROLES = ("administrador", "analista_cambiario", "cajero", "cliente")


def facturas_visibles(usuario):
    """Las facturas de las operaciones que el usuario puede ver."""
    return Factura.objects.select_related(
        "transaccion", "transaccion__cliente", "transaccion__moneda"
    ).filter(transaccion__in=operaciones.transacciones_visibles(usuario))


def factura_a_dict(factura):
    """La factura en el formato que usa la maqueta (claves en camelCase)."""
    transaccion = factura.transaccion
    return {
        "id": factura.pk,
        "numero": factura.numero_completo,
        "estado": factura.estado,
        "estadoTexto": factura.get_estado_display(),
        "detalle": factura.detalle or None,
        "fecha": factura.fecha_creacion.isoformat(),
        "monto": float(factura.total),
        "cliente": factura.receptor_nombre,
        "documento": factura.receptor_documento or None,
        "operacionId": transaccion.pk,
        "operacion": (
            f"{transaccion.get_tipo_display()} - "
            f"{transaccion.monto_divisa} {transaccion.moneda.codigo}"
        ),
        "cdc": factura.cdc or None,
        # Qué botones mostrar.
        "descargable": factura.emitida,
        "sePuedeEmitir": servicio.se_puede_emitir(factura),
    }


def _error(mensaje, estado=400):
    return JsonResponse({"error": mensaje}, status=estado)


def _factura_visible(request, pk):
    return facturas_visibles(request.user).filter(pk=pk).first()


@require_GET
@rol_requerido(*TODOS_LOS_ROLES)
def facturas(request):
    """Las facturas que el usuario puede ver, de la más nueva a la más vieja.

    ``emision`` le dice a la maqueta si las facturas se emiten de verdad o se
    simulan, para que lo aclare en pantalla.
    """
    lista = [factura_a_dict(f) for f in facturas_visibles(request.user)]
    return JsonResponse({
        "facturas": lista,
        "total": len(lista),
        "emision": "real" if servicio.emite() else "simulada",
    })


@require_POST
@rol_requerido(*TODOS_LOS_ROLES)
def actualizar(request, pk):
    """Consulta en Factura Segura cómo quedó la factura en el SIFEN."""
    factura = _factura_visible(request, pk)
    if factura is None:
        return _error("No encontrada.", 404)
    try:
        servicio.actualizar_estado(factura)
    except ErrorFacturaSegura as error:
        return _error(str(error), 502)
    return JsonResponse(factura_a_dict(factura))


@require_POST
@rol_requerido(*TODOS_LOS_ROLES)
def reintentar(request, pk):
    """Vuelve a emitir una factura que falló. El resultado (bueno o malo)
    viene en el ``estado`` y el ``detalle`` de la factura."""
    factura = _factura_visible(request, pk)
    if factura is None:
        return _error("No encontrada.", 404)
    try:
        servicio.reintentar(factura)
    except FacturaInvalida as error:
        return _error(str(error))
    return JsonResponse(factura_a_dict(factura))


@require_GET
@rol_requerido(*TODOS_LOS_ROLES)
def descargar(request, pk, formato):
    """El KuDE (``kude``, PDF) o el XML firmado (``xml``) de la factura."""
    factura = _factura_visible(request, pk)
    if factura is None:
        return _error("No encontrada.", 404)
    try:
        contenido, content_type, nombre = servicio.descargar(factura, formato)
    except FacturaInvalida as error:
        return _error(str(error), 409)
    except ErrorFacturaSegura as error:
        return _error(str(error), 502)
    respuesta = HttpResponse(contenido, content_type=content_type)
    respuesta["Content-Disposition"] = f'attachment; filename="{nombre}"'
    return respuesta
