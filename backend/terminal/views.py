"""Pantallas de la terminal de autoservicio.

Las de la terminal (elegir terminal, ingresar el código, depositar) son de
**quiosco**: no piden iniciar sesión, porque la máquina la usa cualquier
cliente que llegue con su código, como un cajero automático. El código es lo
que identifica la operación: 8 caracteres al azar.

La reserva se hace con sesión, desde el detalle de la operación, y el estado de
las terminales (sus billetes) lo ven el administrador y el cajero.
"""
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from cuentas.decorators import rol_requerido
from operaciones.views import TODOS_LOS_ROLES, _transaccion_visible

from . import servicio
from .models import OperacionTerminal, Terminal
from .servicio import TerminalInvalida

VEN_TERMINALES = ("administrador", "cajero")


def _terminal_activa(terminal_id):
    return get_object_or_404(Terminal, pk=terminal_id, activa=True)


def elegir_terminal(request):
    """Primera pantalla: en qué terminal está el cliente (simula la máquina)."""
    return render(request, "terminal/elegir.html", {"terminales": Terminal.objects.filter(activa=True)})


def ingresar_codigo(request, terminal_id):
    """El cliente tipea el código de su operación."""
    terminal = _terminal_activa(terminal_id)
    error = None
    if request.method == "POST":
        try:
            reserva = servicio.buscar(request.POST.get("codigo"))
        except TerminalInvalida as problema:
            error = str(problema)
        else:
            return redirect("terminal_operacion", terminal_id=terminal.pk, codigo=reserva.codigo)
    return render(request, "terminal/codigo.html", {"terminal": terminal, "error": error})


def _contexto(terminal, reserva, error=None, cantidades=None):
    transaccion = reserva.transaccion
    moneda_deposito, monto_deposito = servicio.a_depositar(transaccion)
    moneda_entrega, monto_entrega = servicio.a_entregar(transaccion)
    cantidades = cantidades or {}
    return {
        "terminal": terminal,
        "reserva": reserva,
        "t": transaccion,
        "error": error,
        "moneda_deposito": moneda_deposito,
        "monto_deposito": monto_deposito,
        "moneda_entrega": moneda_entrega,
        "monto_entrega": monto_entrega,
        "billetes": [
            {"denominacion": d, "cantidad": cantidades.get(str(d.pk), "")}
            for d in servicio.denominaciones(moneda_deposito)
        ],
        "es_venta": transaccion.tipo == "VENTA",
        "entrega": cantidades.get("entrega", OperacionTerminal.Entrega.EFECTIVO),
    }


def operacion(request, terminal_id, codigo):
    """La operación del código: qué depositar, y el resultado al confirmar."""
    terminal = _terminal_activa(terminal_id)
    try:
        reserva = servicio.buscar(codigo)
    except TerminalInvalida as problema:
        return render(request, "terminal/codigo.html", {"terminal": terminal, "error": str(problema)})

    if request.method == "POST" and reserva.estado == OperacionTerminal.Estado.ESPERANDO:
        depositado = {
            clave[len("billete_"):]: valor
            for clave, valor in request.POST.items() if clave.startswith("billete_")
        }
        entrega = request.POST.get("entrega", OperacionTerminal.Entrega.EFECTIVO)
        try:
            reserva = servicio.completar(reserva, terminal, depositado, entrega)
        except TerminalInvalida as problema:
            cantidades = {**depositado, "entrega": entrega}
            return render(request, "terminal/operacion.html",
                          _contexto(terminal, reserva, str(problema), cantidades))

    if reserva.estado != OperacionTerminal.Estado.ESPERANDO:
        return render(request, "terminal/resultado.html", _contexto(terminal, reserva))
    return render(request, "terminal/operacion.html", _contexto(terminal, reserva))


@require_POST
def cancelar(request, terminal_id, codigo):
    """El cliente desiste en la terminal."""
    terminal = _terminal_activa(terminal_id)
    try:
        reserva = servicio.cancelar(servicio.buscar(codigo), terminal)
    except TerminalInvalida as problema:
        return render(request, "terminal/codigo.html", {"terminal": terminal, "error": str(problema)})
    return render(request, "terminal/resultado.html", _contexto(terminal, reserva))


@require_POST
@rol_requerido(*TODOS_LOS_ROLES)
def reservar(request, pk):
    """Desde el detalle de una operación pendiente: pagarla en la terminal."""
    transaccion = _transaccion_visible(request, pk)
    try:
        servicio.reservar(transaccion, request.user)
    except TerminalInvalida as error:
        request.session["error_operacion"] = str(error)
    return redirect("detalle_operacion", pk=pk)


@rol_requerido(*VEN_TERMINALES)
def estado(request):
    """Los billetes de cada terminal y sus últimas operaciones."""
    terminales = [
        {
            "terminal": terminal,
            "billetes": servicio.billetes_de(terminal),
            "operaciones": terminal.operaciones.select_related("transaccion__moneda", "transaccion__cliente")[:10],
        }
        for terminal in Terminal.objects.all()
    ]
    return render(request, "terminal/estado.html", {
        "terminales": terminales,
        "esperando": OperacionTerminal.objects.filter(estado=OperacionTerminal.Estado.ESPERANDO).count(),
    })
