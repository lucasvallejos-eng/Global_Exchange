"""API JSON de facturas para la maqueta (React).

Quién ve qué: el administrador, el analista y el cajero ven todas las
facturas; el resto, las de los clientes a los que está asociado (la misma
regla del historial de operaciones). Las descargas pasan por acá: el backend
baja el archivo de Factura Segura y lo reenvía, así el token nunca llega al
navegador.
"""
from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_GET, require_POST

from cuentas.decorators import rol_requerido
from operaciones.servicios import VEN_TODAS

from . import servicio
from .models import Factura
from .servicio import ErrorFacturaSegura, FacturaInvalida

TODOS_LOS_ROLES = ("administrador", "analista_cambiario", "cajero", "cliente")
SOLO_ADMINISTRADOR = "Con la emisión prendida, solo el administrador puede emitir facturas."


def facturas_visibles(usuario):
    """Las facturas que el usuario puede ver, de la web y de la caja."""
    facturas = Factura.objects.select_related(
        "cliente", "transaccion__moneda", "compra_caja__moneda", "venta_caja__moneda"
    )
    if usuario.groups.filter(name__in=VEN_TODAS).exists():
        return facturas
    return facturas.filter(cliente__usuarios=usuario)


def puede_emitir(usuario):
    """Solo el administrador puede emitir o reintentar facturas."""
    return usuario.groups.filter(name="administrador").exists()


def descripcion_de(factura):
    """La operación facturada en una línea: ``Venta de divisa - 100 USD``."""
    operacion = servicio.operacion_de(factura.origen)
    tipo = "Venta de divisa" if operacion.casa_vende else "Compra de divisa"
    return f"{tipo} - {operacion.monto_divisa} {operacion.moneda}"


def factura_a_dict(factura, emite_el_usuario):
    """La factura en el formato que usa la maqueta (claves en camelCase).

    Args:
        emite_el_usuario (bool): ``puede_emitir`` de quien la pide.
    """
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
        # De dónde salió: una operación de la web o de la caja.
        "origen": "Web" if factura.transaccion_id else "Caja",
        "operacionId": factura.origen.pk,
        "referencia": factura.referencia,
        "operacion": descripcion_de(factura),
        "cdc": factura.cdc or None,
        # Qué botones mostrar.
        "descargable": factura.emitida,
        "sePuedeEmitir": emite_el_usuario and servicio.se_puede_emitir(factura),
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
    emite_el_usuario = puede_emitir(request.user)
    lista = [factura_a_dict(f, emite_el_usuario) for f in facturas_visibles(request.user)]
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
    return JsonResponse(factura_a_dict(factura, puede_emitir(request.user)))


@require_POST
@rol_requerido(*TODOS_LOS_ROLES)
def reintentar(request, pk):
    """Vuelve a emitir una factura que falló. El resultado (bueno o malo)
    viene en el ``estado`` y el ``detalle`` de la factura."""
    factura = _factura_visible(request, pk)
    if factura is None:
        return _error("No encontrada.", 404)
    if not puede_emitir(request.user):
        return _error(SOLO_ADMINISTRADOR, 403)
    try:
        servicio.reintentar(factura)
    except FacturaInvalida as error:
        return _error(str(error))
    return JsonResponse(factura_a_dict(factura, True))


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
