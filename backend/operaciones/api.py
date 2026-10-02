"""API JSON de operaciones para la maqueta (React).

Es el mismo flujo que las pantallas de Django (``operaciones/views.py``):
crear la operación pendiente, mostrar el cálculo, y pagarla o cancelarla. Las
reglas no se repiten acá: todo pasa por ``operaciones.servicios``.

Que la cotización haya cambiado al pagar **no** es un error de la API: la
operación se cancela y se devuelve con ``estado = "CANCELADA"`` y
``canceladaPorCotizacion = true``, con código 200. Es un resultado normal del
negocio, y la maqueta lo muestra como tal. Los errores (400) quedan para lo que
no se puede hacer: pagar dos veces, operar a nombre de un cliente ajeno, etc.
"""
import json
from decimal import Decimal, InvalidOperation

from django.http import HttpResponseNotAllowed, JsonResponse
from django.views.decorators.http import require_GET, require_POST

from clientes.models import Cliente
from cuentas.decorators import rol_requerido
from medios_pago.models import MedioPago
from monedas.models import Moneda

from . import servicios
from .models import Transaccion
from .servicios import OperacionInvalida
from .views import filtros_de

TODOS_LOS_ROLES = ("administrador", "analista_cambiario", "cajero", "cliente")


def _numero(valor):
    return float(valor) if valor is not None else None


def _fecha(valor):
    return valor.isoformat() if valor else None


def transaccion_a_dict(t):
    """La operación en el formato que usa la maqueta (claves en camelCase)."""
    return {
        "id": t.pk,
        "tipo": t.tipo,
        "tipoTexto": t.get_tipo_display(),
        "estado": t.estado,
        "estadoTexto": t.get_estado_display(),
        "cliente": {"id": t.cliente_id, "nombre": t.cliente.nombre},
        "moneda": t.moneda.codigo,
        "montoDivisa": _numero(t.monto_divisa),
        "tasaBase": _numero(t.tasa_base),
        "descuentoCompra": _numero(t.descuento_compra),
        "tasaAplicada": _numero(t.tasa_aplicada),
        "montoGuaranies": _numero(t.monto_guaranies),
        "porcentajeComision": _numero(t.porcentaje_comision),
        "comision": _numero(t.comision),
        "totalGuaranies": _numero(t.total_guaranies),
        "medioPago": t.medio_pago_descripcion or None,
        "motivoCancelacion": t.motivo_cancelacion or None,
        "canceladaPorCotizacion": t.cancelada_por_cotizacion,
        "tasaBaseNueva": _numero(t.tasa_base_nueva),
        "fechaCreacion": _fecha(t.fecha_creacion),
        "fechaPago": _fecha(t.fecha_pago),
        "fechaCancelacion": _fecha(t.fecha_cancelacion),
    }


def _error(mensaje, estado=400):
    return JsonResponse({"error": mensaje}, status=estado)


def _transaccion_visible(request, pk):
    """La operación si el usuario puede verla; si no, ``None`` (la vista
    responde 404, sin confirmar que exista)."""
    t = (Transaccion.objects.select_related("cliente", "moneda")
         .filter(pk=pk).first())
    if t is None or not servicios.puede_ver(request.user, t):
        return None
    return t


@rol_requerido(*TODOS_LOS_ROLES)
def operaciones(request):
    """``GET`` devuelve el historial; ``POST`` crea una operación."""
    if request.method == "GET":
        return historial(request)
    if request.method == "POST":
        return crear(request)
    return HttpResponseNotAllowed(["GET", "POST"])


def historial(request):
    """Historial de operaciones, solo consulta.

    Acepta los mismos filtros que la pantalla de Django, por la URL:
    ``estado``, ``tipo``, ``moneda`` (código), ``cliente`` (id), ``desde`` y
    ``hasta`` (``AAAA-MM-DD``). Cada uno ve lo que puede ver, igual que en la
    pantalla: el cliente las de sus clientes; administrador, analista y cajero,
    todas.
    """
    visibles = servicios.transacciones_visibles(request.user)
    resultado = servicios.filtrar_historial(visibles, **filtros_de(request.GET))
    lista = [transaccion_a_dict(t) for t in resultado]
    return JsonResponse({"operaciones": lista, "total": len(lista)})


@require_POST
@rol_requerido(*TODOS_LOS_ROLES)
def crear(request):
    """Crea una operación pendiente de pago.

    Espera ``{"clienteId", "tipo": "COMPRA"|"VENTA", "moneda": "USD",
    "monto", "medioPagoId"?}`` y devuelve la operación con el cálculo hecho.
    """
    entrada = _entrada_operacion(request)
    if isinstance(entrada, JsonResponse):
        return entrada
    datos, cliente, moneda, monto, medio_pago = entrada
    try:
        t = servicios.crear_operacion(
            request.user, cliente, datos.get("tipo"), moneda, monto, medio_pago
        )
    except OperacionInvalida as error:
        return _error(str(error))
    return JsonResponse(transaccion_a_dict(t), status=201)


def _entrada_operacion(request):
    """Lee y resuelve los datos de una operación que manda la maqueta.

    Returns:
        tuple | JsonResponse: ``(datos, cliente, moneda, monto, medio_pago)``,
        o la respuesta de error si falta algo.
    """
    try:
        datos = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return _error("El cuerpo de la solicitud no es JSON válido.")

    cliente = Cliente.objects.filter(pk=datos.get("clienteId") or None).first()
    if cliente is None:
        return _error("Elegí uno de tus clientes.")
    moneda = Moneda.objects.filter(codigo=datos.get("moneda") or "").first()
    if moneda is None:
        return _error("Elegí la moneda.")
    try:
        monto = Decimal(str(datos.get("monto")))
    except (InvalidOperation, ValueError):
        return _error("El monto tiene que ser un número.")

    medio_pago = None
    if datos.get("medioPagoId"):
        medio_pago = MedioPago.objects.filter(pk=datos["medioPagoId"]).first()
    return datos, cliente, moneda, monto, medio_pago


@require_POST
@rol_requerido(*TODOS_LOS_ROLES)
def cotizar(request):
    """Calcula la operación sin guardarla (lo que muestra el modal de la maqueta).

    Recibe lo mismo que ``crear`` y devuelve el cálculo con las mismas claves
    que una operación, pero sin ``id`` ni ``estado``: todavía no existe.
    """
    entrada = _entrada_operacion(request)
    if isinstance(entrada, JsonResponse):
        return entrada
    datos, cliente, moneda, monto, medio_pago = entrada
    try:
        calculo = servicios.cotizar(
            request.user, cliente, datos.get("tipo"), moneda, monto, medio_pago
        )
    except OperacionInvalida as error:
        return _error(str(error))
    return JsonResponse({
        "tipo": datos.get("tipo"),
        "cliente": {"id": cliente.pk, "nombre": cliente.nombre},
        "moneda": moneda.codigo,
        "montoDivisa": _numero(monto),
        "tasaBase": _numero(calculo["tasa_base"]),
        "descuentoCompra": _numero(calculo["descuento_compra"]),
        "tasaAplicada": _numero(calculo["tasa_aplicada"]),
        "montoGuaranies": _numero(calculo["monto_guaranies"]),
        "porcentajeComision": _numero(calculo["porcentaje_comision"]),
        "comision": _numero(calculo["comision"]),
        "totalGuaranies": _numero(calculo["total_guaranies"]),
        "medioPago": servicios._descripcion_medio_pago(medio_pago) if medio_pago else None,
    })


@require_POST
@rol_requerido(*TODOS_LOS_ROLES)
def confirmar(request):
    """Registra la operación que el cliente confirmó en el modal.

    Recibe lo mismo que ``cotizar`` más ``tasaBase`` (la del cálculo que se le
    mostró). Devuelve la operación ya ``PAGADA``, o ``CANCELADA`` con
    ``canceladaPorCotizacion = true`` si la cotización cambió mientras tanto
    (código 201 en los dos casos: la operación quedó registrada).
    """
    entrada = _entrada_operacion(request)
    if isinstance(entrada, JsonResponse):
        return entrada
    datos, cliente, moneda, monto, medio_pago = entrada
    try:
        tasa_base = Decimal(str(datos.get("tasaBase")))
    except (InvalidOperation, ValueError):
        return _error("Falta la tasa del cálculo que se confirmó.")
    try:
        t = servicios.confirmar_operacion(
            request.user, cliente, datos.get("tipo"), moneda, monto, tasa_base, medio_pago
        )
    except OperacionInvalida as error:
        return _error(str(error))
    return JsonResponse(transaccion_a_dict(t), status=201)


@require_GET
@rol_requerido(*TODOS_LOS_ROLES)
def detalle(request, pk):
    """Una operación, si el usuario puede verla."""
    t = _transaccion_visible(request, pk)
    if t is None:
        return _error("No existe esa operación.", 404)
    return JsonResponse(transaccion_a_dict(t))


@require_POST
@rol_requerido(*TODOS_LOS_ROLES)
def pagar(request, pk):
    """Paga la operación, o la cancela si la cotización cambió (ver arriba)."""
    t = _transaccion_visible(request, pk)
    if t is None:
        return _error("No existe esa operación.", 404)
    try:
        t = servicios.pagar(t, request.user)
    except OperacionInvalida as error:
        return _error(str(error))
    return JsonResponse(transaccion_a_dict(t))


@require_POST
@rol_requerido(*TODOS_LOS_ROLES)
def cancelar(request, pk):
    """El cliente desiste de una operación que todavía no pagó."""
    t = _transaccion_visible(request, pk)
    if t is None:
        return _error("No existe esa operación.", 404)
    try:
        t = servicios.cancelar(t, request.user)
    except OperacionInvalida as error:
        return _error(str(error))
    return JsonResponse(transaccion_a_dict(t))
