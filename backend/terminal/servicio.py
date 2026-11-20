"""Reglas de la terminal de autoservicio (TAUser).

El circuito:

1. **Reserva (web).** El cliente crea una compra o venta pendiente y elige
   pagarla en la terminal (``reservar``). Recibe un **código** de 8 letras y
   números. No se cobra nada todavía.
2. **Terminal.** Ingresa el código (``buscar``) y **deposita billetes**: si
   compra divisa, guaraníes por el total; si vende, la divisa. La terminal
   (``completar``):

   - verifica que lo depositado alcance y que pueda devolver el **vuelto** y
     **entregar** lo que corresponde con los billetes que tiene adentro. Si no
     puede, no pasa nada: devuelve los billetes y la operación sigue esperando
     (el cliente puede ir a otra terminal o cancelar);
   - paga la operación con ``operaciones.servicios.pagar``, que es la misma
     regla de la web: si la **cotización cambió** desde la reserva, la operación
     se **cancela** y se devuelven los billetes;
   - si quedó pagada, mueve los billetes (entra lo depositado, sale el vuelto y
     lo entregado). En una venta, el cliente puede elegir que los guaraníes se
     **acrediten** en su cuenta en vez de retirarlos.

3. **Cancelación.** El cliente puede cancelarla en la terminal
   (``cancelar``) o en la web, como cualquier pendiente.

Al quedar pagada se genera la factura, igual que en la web (``facturacion``).
"""
import secrets
from decimal import Decimal, InvalidOperation

from django.db import transaction as transaccion_bd
from django.utils import timezone

from monedas.models import Denominacion
from operaciones import servicios as operaciones
from operaciones.models import Transaccion
from operaciones.servicios import OperacionInvalida

from .models import BilleteTerminal, OperacionTerminal

# Sin letras ni números que se confundan al tipearlos (0/O, 1/I/L).
ALFABETO = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
LARGO_CODIGO = 8
GUARANI = "PYG"
DESCRIPCION_MEDIO = "Efectivo en terminal de autoservicio"


class TerminalInvalida(Exception):
    """No se puede hacer lo pedido en la terminal. El mensaje se le muestra al cliente."""


def _texto(valor):
    """Un monto sin ceros de más: 100.00 -> "100", 0.50 -> "0.5"."""
    valor = Decimal(valor).normalize()
    return f"{valor:f}"


def _legible(valor):
    """Un monto para leer en pantalla: 26000 -> "26.000", 10.5 -> "10,50"."""
    valor = Decimal(valor)
    if valor == valor.to_integral_value():
        return f"{int(valor):,}".replace(",", ".")
    return f"{valor:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")


def _codigo_nuevo():
    for _ in range(20):
        codigo = "".join(secrets.choice(ALFABETO) for _ in range(LARGO_CODIGO))
        if not OperacionTerminal.objects.filter(codigo=codigo).exists():
            return codigo
    raise TerminalInvalida("No se pudo generar un código. Probá de nuevo.")


def normalizar_codigo(codigo):
    """El código como se guarda: en mayúsculas y sin espacios ni guiones."""
    return "".join((codigo or "").split()).replace("-", "").upper()


# --- Reserva -----------------------------------------------------------------

def reservar(transaccion, usuario):
    """Deja una operación pendiente lista para completarse en la terminal.

    Se puede llamar más de una vez: devuelve la reserva que ya tenía.

    Raises:
        TerminalInvalida: si el usuario no opera a nombre del cliente, la
            operación no está pendiente o se paga con tarjeta.
    """
    if not operaciones.puede_gestionar(usuario, transaccion):
        raise TerminalInvalida("Esta operación no es de un cliente al que estés asociado.")
    existente = OperacionTerminal.objects.filter(transaccion=transaccion).first()
    if existente:
        return existente
    if transaccion.estado != Transaccion.Estado.PENDIENTE:
        raise TerminalInvalida("Solo una operación pendiente se puede pagar en la terminal.")
    if transaccion.medio_pago_id and transaccion.medio_pago.stripe_payment_method_id:
        raise TerminalInvalida("Una operación con tarjeta se paga en la web, no en la terminal.")
    with transaccion_bd.atomic():
        transaccion.medio_pago_descripcion = DESCRIPCION_MEDIO
        transaccion.save(update_fields=["medio_pago_descripcion"])
        return OperacionTerminal.objects.create(transaccion=transaccion, codigo=_codigo_nuevo())


def reservar_nueva(usuario, cliente, tipo, moneda, monto_divisa):
    """Crea la operación pendiente y la reserva en un paso (lo usa la maqueta).

    Raises:
        TerminalInvalida: ver ``reservar`` y ``operaciones.servicios.crear_operacion``.
    """
    try:
        transaccion = operaciones.crear_operacion(usuario, cliente, tipo, moneda, monto_divisa)
    except OperacionInvalida as error:
        raise TerminalInvalida(str(error)) from error
    return reservar(transaccion, usuario)


def _sincronizar(reserva):
    """Si la operación se pagó o canceló por otro lado (la web), la reserva ya no sirve."""
    transaccion = reserva.transaccion
    if reserva.estado == OperacionTerminal.Estado.ESPERANDO and transaccion.estado != Transaccion.Estado.PENDIENTE:
        reserva.estado = OperacionTerminal.Estado.CANCELADA
        reserva.detalle = f"La operación ya está {transaccion.get_estado_display().lower()} desde la web."
        reserva.fecha_fin = timezone.now()
        reserva.save()


def buscar(codigo):
    """La reserva de ese código.

    Raises:
        TerminalInvalida: si no existe.
    """
    reserva = OperacionTerminal.objects.select_related(
        "transaccion__moneda", "transaccion__cliente", "transaccion__usuario"
    ).filter(codigo=normalizar_codigo(codigo)).first()
    if reserva is None:
        raise TerminalInvalida("No hay ninguna operación con ese código. Revisalo y probá de nuevo.")
    _sincronizar(reserva)
    return reserva


# --- Qué entra y qué sale ----------------------------------------------------

def a_depositar(transaccion):
    """Lo que el cliente pone en la terminal: ``(moneda, monto)``."""
    if transaccion.tipo == Transaccion.Tipo.COMPRA:
        return GUARANI, Decimal(transaccion.total_guaranies)
    return transaccion.moneda.codigo, Decimal(transaccion.monto_divisa)


def a_entregar(transaccion):
    """Lo que la terminal le da al cliente: ``(moneda, monto)``."""
    if transaccion.tipo == Transaccion.Tipo.COMPRA:
        return transaccion.moneda.codigo, Decimal(transaccion.monto_divisa)
    return GUARANI, Decimal(transaccion.total_guaranies)


def denominaciones(codigo):
    """Los billetes de una moneda, del más grande al más chico."""
    return Denominacion.objects.filter(moneda__codigo=codigo).select_related("moneda").order_by("-valor")


def desglosar(monto, disponibles):
    """Cómo pagar ``monto`` con los billetes que hay, empezando por los más grandes.

    Args:
        monto (Decimal): lo que hay que entregar.
        disponibles (dict): ``{valor: cantidad}``.

    Returns:
        dict | None: ``{valor: cantidad}``, o ``None`` si no se puede pagar justo.
    """
    restante = Decimal(monto)
    resultado = {}
    for valor in sorted(disponibles, reverse=True):
        if restante <= 0:
            break
        cantidad = min(int(restante // valor), disponibles[valor])
        if cantidad > 0:
            resultado[valor] = cantidad
            restante -= valor * cantidad
    return resultado if restante == 0 else None


def _stock(terminal):
    """Los billetes de la terminal, bloqueados para esta operación: ``{(moneda, valor): fila}``."""
    filas = BilleteTerminal.objects.select_for_update().filter(terminal=terminal).select_related(
        "denominacion__moneda"
    )
    return {(f.denominacion.moneda.codigo, f.denominacion.valor): f for f in filas}


def _disponibles(stock, codigo, mas=None):
    disponibles = {valor: fila.cantidad for (moneda, valor), fila in stock.items() if moneda == codigo}
    for valor, cantidad in (mas or {}).items():
        disponibles[valor] = disponibles.get(valor, 0) + cantidad
    return {valor: cantidad for valor, cantidad in disponibles.items() if cantidad > 0}


def _leer_deposito(depositado, codigo):
    """Pasa ``{id de denominación: cantidad}`` a ``{valor: cantidad}``, validando la moneda."""
    validas = {d.pk: d for d in denominaciones(codigo)}
    billetes = {}
    for clave, cantidad in depositado.items():
        try:
            pk, cantidad = int(clave), int(cantidad or 0)
        except (TypeError, ValueError, InvalidOperation) as error:
            raise TerminalInvalida("Las cantidades de billetes tienen que ser números enteros.") from error
        if cantidad < 0:
            raise TerminalInvalida("Las cantidades de billetes no pueden ser negativas.")
        if cantidad == 0:
            continue
        if pk not in validas:
            raise TerminalInvalida(f"Esa terminal solo recibe billetes de {codigo} para esta operación.")
        valor = validas[pk].valor
        billetes[valor] = billetes.get(valor, 0) + cantidad
    return billetes


def _a_texto(billetes):
    return {_texto(valor): cantidad for valor, cantidad in sorted(billetes.items(), reverse=True)}


# --- En la terminal ----------------------------------------------------------

def completar(reserva, terminal, depositado, entrega=OperacionTerminal.Entrega.EFECTIVO):
    """El cliente depositó los billetes: se paga la operación y se le entrega lo suyo.

    Args:
        reserva (OperacionTerminal): la del código ingresado.
        terminal (Terminal): dónde está el cliente.
        depositado (dict): ``{id de Denominacion: cantidad}`` de lo que puso.
        entrega (str): en una venta, ``EFECTIVO`` o ``CUENTA`` (acreditación).

    Returns:
        OperacionTerminal: ``COMPLETADA``, o ``CANCELADA`` si la cotización cambió.

    Raises:
        TerminalInvalida: si no alcanza lo depositado, no hay cambio o billetes
            para entregar, o la reserva ya no está esperando. En esos casos no
            cambia nada: la terminal devuelve los billetes.
    """
    with transaccion_bd.atomic():
        reserva = OperacionTerminal.objects.select_for_update().select_related(
            "transaccion__moneda", "transaccion__cliente", "transaccion__usuario"
        ).get(pk=reserva.pk)
        _sincronizar(reserva)
        if reserva.estado != OperacionTerminal.Estado.ESPERANDO:
            raise TerminalInvalida(f"Esta operación ya está {reserva.get_estado_display().lower()}.")
        if not terminal.activa:
            raise TerminalInvalida("Esta terminal está fuera de servicio.")
        transaccion = reserva.transaccion
        es_venta = transaccion.tipo == Transaccion.Tipo.VENTA
        if entrega not in OperacionTerminal.Entrega.values or (entrega == OperacionTerminal.Entrega.CUENTA and not es_venta):
            entrega = OperacionTerminal.Entrega.EFECTIVO
        if entrega == OperacionTerminal.Entrega.CUENTA and not transaccion.cliente.cuenta_acreditar:
            raise TerminalInvalida("El cliente no tiene una cuenta para acreditar: elegí retirar en efectivo.")

        moneda_deposito, monto_deposito = a_depositar(transaccion)
        billetes = _leer_deposito(depositado, moneda_deposito)
        total = sum((valor * cantidad for valor, cantidad in billetes.items()), Decimal("0"))
        if total < monto_deposito:
            raise TerminalInvalida(
                f"Depositaste {_legible(total)} {moneda_deposito} y la operación es de "
                f"{_legible(monto_deposito)} {moneda_deposito}. Se te devuelven los billetes."
            )

        stock = _stock(terminal)
        vuelto = {}
        if total > monto_deposito:
            vuelto = desglosar(total - monto_deposito, _disponibles(stock, moneda_deposito, billetes))
            if vuelto is None:
                raise TerminalInvalida(
                    f"La terminal no tiene cambio para devolverte {_legible(total - monto_deposito)} "
                    f"{moneda_deposito}. Depositá el monto justo. Se te devuelven los billetes."
                )

        moneda_entrega, monto_entrega = a_entregar(transaccion)
        entregar = {}
        if entrega == OperacionTerminal.Entrega.EFECTIVO:
            entregar = desglosar(monto_entrega, _disponibles(stock, moneda_entrega))
            if entregar is None:
                raise TerminalInvalida(
                    f"La terminal no tiene billetes para entregarte {_legible(monto_entrega)} "
                    f"{moneda_entrega}. Probá en otra terminal o cancelá la operación. "
                    "Se te devuelven los billetes."
                )

        try:
            transaccion = operaciones.pagar(transaccion, transaccion.usuario)
        except OperacionInvalida as error:
            raise TerminalInvalida(str(error)) from error

        reserva.terminal = terminal
        reserva.entrega = entrega
        reserva.fecha_fin = timezone.now()
        if transaccion.estado != Transaccion.Estado.PAGADA:
            # Cambió la cotización: no se cobra nada y se devuelven los billetes.
            reserva.estado = OperacionTerminal.Estado.CANCELADA
            reserva.detalle = transaccion.motivo_cancelacion[:500]
            reserva.save()
            return reserva

        _mover(terminal, stock, moneda_deposito, billetes, signo=1)
        _mover(terminal, stock, moneda_deposito, vuelto, signo=-1)
        _mover(terminal, stock, moneda_entrega, entregar, signo=-1)

        reserva.estado = OperacionTerminal.Estado.COMPLETADA
        reserva.depositado = {moneda_deposito: _a_texto(billetes)}
        reserva.entregado = {}
        if entregar:
            reserva.entregado[moneda_entrega] = _a_texto(entregar)
        if vuelto:
            reserva.entregado.setdefault(moneda_deposito, {}).update(_a_texto(vuelto))
        if entrega == OperacionTerminal.Entrega.CUENTA:
            reserva.detalle = (
                f"Se acreditaron {_legible(monto_entrega)} {moneda_entrega} en la cuenta "
                f"{transaccion.cliente.cuenta_acreditar}."
            )
        else:
            reserva.detalle = f"Se entregaron {_legible(monto_entrega)} {moneda_entrega}."
        if vuelto:
            reserva.detalle += f" Vuelto: {_legible(total - monto_deposito)} {moneda_deposito}."
        reserva.save()
        return reserva


def _mover(terminal, stock, codigo, billetes, signo):
    for valor, cantidad in billetes.items():
        fila = stock.get((codigo, valor))
        if fila is None:
            denominacion = Denominacion.objects.get(moneda__codigo=codigo, valor=valor)
            fila = BilleteTerminal.objects.create(terminal=terminal, denominacion=denominacion, cantidad=0)
            stock[(codigo, valor)] = fila
        fila.cantidad += signo * cantidad
        fila.save(update_fields=["cantidad"])


def cancelar(reserva, terminal=None):
    """El cliente cancela la operación en la terminal.

    Raises:
        TerminalInvalida: si ya no está esperando.
    """
    with transaccion_bd.atomic():
        reserva = OperacionTerminal.objects.select_for_update().select_related(
            "transaccion__usuario"
        ).get(pk=reserva.pk)
        _sincronizar(reserva)
        if reserva.estado != OperacionTerminal.Estado.ESPERANDO:
            raise TerminalInvalida(f"Esta operación ya está {reserva.get_estado_display().lower()}.")
        transaccion = reserva.transaccion
        try:
            transaccion = operaciones.cancelar(transaccion, transaccion.usuario)
        except OperacionInvalida as error:
            raise TerminalInvalida(str(error)) from error
        reserva.terminal = terminal
        reserva.fecha_fin = timezone.now()
        reserva.estado = OperacionTerminal.Estado.CANCELADA
        reserva.detalle = "Cancelada por el cliente en la terminal."
        if transaccion.estado == Transaccion.Estado.PAGADA:  # ya estaba cobrada (3D Secure)
            reserva.estado = OperacionTerminal.Estado.COMPLETADA
            reserva.detalle = "La operación ya estaba pagada."
        reserva.save()
        return reserva


def billetes_de(terminal):
    """Los billetes de la terminal por moneda, para la pantalla de estado.

    Returns:
        list[dict]: ``moneda``, ``filas`` (``valor``, ``cantidad``, ``subtotal``) y ``total``.
    """
    por_moneda = {}
    for fila in terminal.billetes.select_related("denominacion__moneda"):
        codigo = fila.denominacion.moneda.codigo
        grupo = por_moneda.setdefault(codigo, {"moneda": codigo, "filas": [], "total": Decimal("0")})
        subtotal = fila.denominacion.valor * fila.cantidad
        grupo["filas"].append({"valor": fila.denominacion.valor, "cantidad": fila.cantidad, "subtotal": subtotal})
        grupo["total"] += subtotal
    for grupo in por_moneda.values():
        grupo["filas"].sort(key=lambda f: f["valor"], reverse=True)
    return sorted(por_moneda.values(), key=lambda g: (g["moneda"] != GUARANI, g["moneda"]))
