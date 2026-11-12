"""API JSON de la terminal de autoservicio para la maqueta (React).

La maqueta reserva la operación y muestra el código; el depósito de billetes
se hace en la pantalla de la terminal (``terminal/views.py``), que es la que
"está" en la máquina.
"""
from django.http import HttpResponseNotAllowed, JsonResponse
from django.urls import reverse
from django.views.decorators.http import require_GET

from cuentas.decorators import rol_requerido
from operaciones.api import TODOS_LOS_ROLES, _entrada_operacion, _error, transaccion_a_dict

from . import servicio
from .models import OperacionTerminal, Terminal
from .servicio import TerminalInvalida


def _numero(valor):
    return float(valor) if valor is not None else None


def reserva_a_dict(reserva, request):
    """La reserva en el formato de la maqueta (claves en camelCase)."""
    t = reserva.transaccion
    moneda_deposito, monto_deposito = servicio.a_depositar(t)
    moneda_entrega, monto_entrega = servicio.a_entregar(t)
    return {
        "codigo": reserva.codigo,
        "estado": reserva.estado,
        "estadoTexto": reserva.get_estado_display(),
        "detalle": reserva.detalle or None,
        "terminal": reserva.terminal.nombre if reserva.terminal else None,
        "entrega": reserva.entrega,
        "deposita": {"moneda": moneda_deposito, "monto": _numero(monto_deposito)},
        "recibe": {"moneda": moneda_entrega, "monto": _numero(monto_entrega)},
        "fecha": reserva.fecha_creacion.isoformat(),
        "operacion": transaccion_a_dict(t),
        "urlTerminal": request.build_absolute_uri(reverse("terminal_inicio")),
    }


@rol_requerido(*TODOS_LOS_ROLES)
def reservas(request):
    """``GET``: las reservas de los clientes del usuario. ``POST``: reservar una
    operación nueva, con ``{"clienteId", "tipo", "moneda", "monto"}``."""
    if request.method == "GET":
        lista = OperacionTerminal.objects.select_related(
            "terminal", "transaccion__moneda", "transaccion__cliente"
        ).filter(transaccion__cliente__usuarios=request.user)[:50]
        for reserva in lista:
            servicio._sincronizar(reserva)
        return JsonResponse({"reservas": [reserva_a_dict(r, request) for r in lista]})
    if request.method != "POST":
        return HttpResponseNotAllowed(["GET", "POST"])

    entrada = _entrada_operacion(request)
    if isinstance(entrada, JsonResponse):
        return entrada
    datos, cliente, moneda, monto, _ = entrada
    try:
        reserva = servicio.reservar_nueva(request.user, cliente, datos.get("tipo"), moneda, monto)
    except TerminalInvalida as error:
        return _error(str(error))
    return JsonResponse(reserva_a_dict(reserva, request), status=201)


@require_GET
@rol_requerido(*TODOS_LOS_ROLES)
def terminales(request):
    """Las terminales que atienden, para decirle al cliente dónde ir."""
    return JsonResponse({"terminales": [
        {"id": t.pk, "nombre": t.nombre, "ubicacion": t.ubicacion}
        for t in Terminal.objects.filter(activa=True)
    ]})
