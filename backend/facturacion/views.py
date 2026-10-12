"""Pantallas de Django para ver las facturas y descargarlas.

Solo muestran y llaman a ``facturacion.servicio``: la visibilidad es la misma
que la de la API (``facturacion.api.facturas_visibles``).
"""
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from cuentas.decorators import rol_requerido

from . import servicio
from .api import SOLO_ADMINISTRADOR, TODOS_LOS_ROLES, descripcion_de, facturas_visibles, puede_emitir
from .models import Factura
from .servicio import ErrorFacturaSegura, FacturaInvalida

POR_PAGINA = 20


@rol_requerido(*TODOS_LOS_ROLES)
def listar_facturas(request):
    """Las facturas que el usuario puede ver, con filtro por estado."""
    facturas = facturas_visibles(request.user)
    estado = request.GET.get("estado", "")
    if estado in Factura.Estado.values:
        facturas = facturas.filter(estado=estado)
    else:
        estado = ""
    pagina = Paginator(facturas, POR_PAGINA).get_page(request.GET.get("pagina"))
    return render(request, "facturacion/lista.html", {
        "pagina": pagina,
        "estados": Factura.Estado.choices,
        "estado": estado,
        "emite": servicio.emite(),
        "numeros_libres": len(servicio.numeros_libres()),
    })


@rol_requerido(*TODOS_LOS_ROLES)
def detalle_factura(request, pk):
    """La factura con sus ítems, su estado y los botones para descargarla."""
    factura = get_object_or_404(facturas_visibles(request.user), pk=pk)
    return render(request, "facturacion/detalle.html", {
        "f": factura,
        "operacion": descripcion_de(factura),
        "items": factura.de.get("gCamItem", []),
        "se_puede_emitir": puede_emitir(request.user) and servicio.se_puede_emitir(factura),
        "error": request.session.pop("error_factura", None),
    })


@require_POST
@rol_requerido(*TODOS_LOS_ROLES)
def actualizar_factura(request, pk):
    """Consulta el estado en el SIFEN y vuelve al detalle."""
    factura = get_object_or_404(facturas_visibles(request.user), pk=pk)
    try:
        servicio.actualizar_estado(factura)
    except ErrorFacturaSegura as error:
        request.session["error_factura"] = str(error)
    return redirect("detalle_factura", pk=pk)


@require_POST
@rol_requerido(*TODOS_LOS_ROLES)
def reintentar_factura(request, pk):
    """Vuelve a emitir una factura que falló y vuelve al detalle."""
    factura = get_object_or_404(facturas_visibles(request.user), pk=pk)
    if not puede_emitir(request.user):
        request.session["error_factura"] = SOLO_ADMINISTRADOR
        return redirect("detalle_factura", pk=pk)
    try:
        servicio.reintentar(factura)
    except FacturaInvalida as error:
        request.session["error_factura"] = str(error)
    return redirect("detalle_factura", pk=pk)
