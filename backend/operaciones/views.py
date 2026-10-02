"""Pantallas de Django para operar: crear una compra o venta y pagarla.

Las vistas solo leen el formulario y muestran el resultado. Todas las reglas
(RN02, el cálculo, la cancelación por cambio de cotización) están en
``operaciones.servicios``, que es lo mismo que usa la API de la maqueta.
"""
from decimal import Decimal, InvalidOperation

from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from cuentas.decorators import rol_requerido
from medios_pago.models import MedioPago
from monedas.models import Moneda

from . import servicios
from .models import Transaccion
from .servicios import OperacionInvalida

TODOS_LOS_ROLES = ("administrador", "analista_cambiario", "cajero", "cliente")


def _monedas_operables():
    """Monedas activas que tienen cotización vigente, con esa cotización."""
    resultado = []
    for moneda in Moneda.objects.filter(activo=True).order_by("codigo"):
        cotizacion = servicios.cotizacion_vigente(moneda)
        if cotizacion:
            resultado.append({"moneda": moneda, "cotizacion": cotizacion})
    return resultado


def _contexto_operar(request, errores=None, enviado=None):
    return {
        "clientes": servicios.clientes_habilitados(request.user),
        "monedas": _monedas_operables(),
        "medios_pago": MedioPago.objects.filter(usuario=request.user, activo=True),
        "tipos": Transaccion.Tipo.choices,
        "errores": errores or [],
        "enviado": enviado or {},
    }


@rol_requerido(*TODOS_LOS_ROLES)
def operar(request):
    """Formulario para comprar o vender divisa.

    Al enviarlo se crea la operación **pendiente de pago** con la cotización
    de ese momento, y se pasa a la pantalla de confirmación. Todavía no se
    cobra nada: el cliente ve el detalle (tasa aplicada, comisión, total) y
    recién ahí confirma el pago.

    Si el usuario no tiene ningún cliente asociado, la pantalla se lo explica
    en vez de mostrar el formulario (RN02: sin cliente solo se consultan tasas).
    """
    if request.method != "POST":
        enviado = {"tipo": request.GET.get("tipo", ""), "moneda": request.GET.get("moneda", ""),
                   "monto": request.GET.get("monto", ""), "cliente": request.GET.get("cliente", "")}
        return render(request, "operaciones/operar.html", _contexto_operar(request, enviado=enviado))

    enviado = request.POST
    errores = []

    cliente = servicios.clientes_habilitados(request.user).filter(
        pk=request.POST.get("cliente") or None
    ).first()
    if cliente is None:
        errores.append("Elegí uno de tus clientes.")

    moneda = Moneda.objects.filter(pk=request.POST.get("moneda") or None).first()
    if moneda is None:
        errores.append("Elegí la moneda.")

    try:
        monto = Decimal(request.POST.get("monto") or "")
    except InvalidOperation:
        monto = None
        errores.append("El monto tiene que ser un número.")

    medio_pago = None
    if request.POST.get("medio_pago"):
        medio_pago = MedioPago.objects.filter(pk=request.POST["medio_pago"]).first()

    if not errores:
        try:
            transaccion = servicios.crear_operacion(
                request.user, cliente, request.POST.get("tipo"), moneda, monto, medio_pago
            )
        except OperacionInvalida as error:
            errores.append(str(error))
        else:
            return redirect("detalle_operacion", pk=transaccion.pk)

    return render(request, "operaciones/operar.html",
                  _contexto_operar(request, errores=errores, enviado=enviado))


def _transaccion_visible(request, pk):
    """La operación si este usuario puede verla; si no, 404.

    404 y no 403: a quien no tiene que verla no le confirmamos que existe.
    """
    transaccion = get_object_or_404(
        Transaccion.objects.select_related("cliente", "moneda", "usuario"), pk=pk
    )
    if not servicios.puede_ver(request.user, transaccion):
        raise Http404
    return transaccion


@rol_requerido(*TODOS_LOS_ROLES)
def detalle_operacion(request, pk):
    """El detalle de una operación, y los botones para pagarla o cancelarla
    mientras esté pendiente."""
    transaccion = _transaccion_visible(request, pk)
    return render(request, "operaciones/detalle.html", {
        "t": transaccion,
        "puede_gestionar": servicios.puede_gestionar(request.user, transaccion),
        "error": request.session.pop("error_operacion", None),
    })


@require_POST
@rol_requerido(*TODOS_LOS_ROLES)
def pagar_operacion(request, pk):
    """Confirma el pago. Si la cotización cambió desde que se creó la
    operación, el servicio la cancela y el detalle lo muestra."""
    transaccion = _transaccion_visible(request, pk)
    try:
        servicios.pagar(transaccion, request.user)
    except OperacionInvalida as error:
        request.session["error_operacion"] = str(error)
    return redirect("detalle_operacion", pk=pk)


@require_POST
@rol_requerido(*TODOS_LOS_ROLES)
def cancelar_operacion(request, pk):
    """El cliente desiste de una operación que todavía no pagó."""
    transaccion = _transaccion_visible(request, pk)
    try:
        servicios.cancelar(transaccion, request.user)
    except OperacionInvalida as error:
        request.session["error_operacion"] = str(error)
    return redirect("detalle_operacion", pk=pk)
