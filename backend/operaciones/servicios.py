"""Reglas de negocio de las operaciones de compra y venta.

Las vistas de Django y la API de la maqueta llaman a estas funciones en vez de
calcular por su cuenta: así la tasa, la comisión y la cancelación se deciden
en un solo lugar y las dos pantallas no pueden dar resultados distintos.

Cómo se calcula una operación (es la regla que ya usaba la maqueta, más la
comisión que configura ``comisiones``):

- **El cliente compra divisa.** La casa se la vende, así que la tasa base es
  el precio de **venta**. Sobre esa tasa se aplica el ``descuento_compra`` del
  segmento del cliente.
- **El cliente vende divisa.** La casa se la compra, así que la tasa base es
  el precio de **compra**, sin descuento.
- **La comisión** es el ``porcentaje_comision`` del segmento sobre el monto
  en guaraníes. En una compra se suma a lo que paga el cliente; en una venta
  se resta de lo que recibe.

Los guaraníes se redondean a enteros: no hay centavos de guaraní en
circulación, y cobrar fracciones que nadie puede pagar no tiene sentido.
"""
from decimal import ROUND_HALF_UP, Decimal

from django.db import transaction as transaccion_bd
from django.utils import timezone

from clientes.models import Cliente
from cotizaciones.models import Cotizacion
from medios_pago.models import MedioPago

from .models import Transaccion

GUARANI = Decimal("1")
CUATRO_DECIMALES = Decimal("0.0001")

# Pueden mirar cualquier operación (no pagarla ni cancelarla): el
# analista_cambiario por la ERS ("ver ganancias"), el administrador y el
# cajero porque atienden a los clientes.
VEN_TODAS = ("administrador", "analista_cambiario", "cajero")


class OperacionInvalida(Exception):
    """La operación no se puede hacer. El mensaje se le muestra al usuario."""


def cotizacion_vigente(moneda):
    """La cotización activa más reciente de la moneda, o ``None`` si no tiene.

    Es la misma definición que usan la pantalla de tasas y el simulador:
    ``Cotizacion`` ya viene ordenada por fecha descendente.
    """
    return Cotizacion.objects.filter(moneda=moneda, activa=True).first()


def tasa_base_de(cotizacion, tipo):
    """El precio de la cotización que corresponde según quién compra.

    Si el cliente compra divisa, la casa se la vende: precio de venta. Si el
    cliente vende, la casa se la compra: precio de compra.
    """
    if tipo == Transaccion.Tipo.COMPRA:
        return cotizacion.precio_venta
    return cotizacion.precio_compra


def calcular(tipo, monto_divisa, cotizacion, segmento):
    """Calcula tasa aplicada, comisión y total de una operación, sin guardarla.

    Args:
        tipo: ``Transaccion.Tipo.COMPRA`` o ``Transaccion.Tipo.VENTA``.
        monto_divisa (Decimal): cantidad de divisa que se compra o se vende.
        cotizacion (Cotizacion): la cotización vigente de la moneda.
        segmento (SegmentoCliente | None): el segmento del cliente; sin
            segmento no hay descuento ni comisión.

    Returns:
        dict: ``tasa_base``, ``descuento_compra``, ``tasa_aplicada``,
        ``monto_guaranies``, ``porcentaje_comision``, ``comision`` y
        ``total_guaranies``, todos ``Decimal``.
    """
    return _calcular(tipo, monto_divisa, Decimal(tasa_base_de(cotizacion, tipo)), segmento)


def _calcular(tipo, monto_divisa, tasa_base, segmento):
    """El cálculo de ``calcular`` a partir de una tasa base ya elegida.

    Se separa para poder recalcular con la tasa que el cliente vio en la
    confirmación aunque la cotización ya haya cambiado (ver
    ``confirmar_operacion``).
    """
    monto_divisa = Decimal(monto_divisa)
    descuento = Decimal("0")
    if segmento is not None and tipo == Transaccion.Tipo.COMPRA:
        descuento = Decimal(segmento.descuento_compra)
    tasa_aplicada = (tasa_base * (1 - descuento)).quantize(CUATRO_DECIMALES, ROUND_HALF_UP)

    monto_guaranies = (monto_divisa * tasa_aplicada).quantize(GUARANI, ROUND_HALF_UP)

    porcentaje = Decimal(segmento.porcentaje_comision) if segmento is not None else Decimal("0")
    comision = (monto_guaranies * porcentaje / 100).quantize(GUARANI, ROUND_HALF_UP)

    if tipo == Transaccion.Tipo.COMPRA:
        total = monto_guaranies + comision
    else:
        total = monto_guaranies - comision

    return {
        "tasa_base": tasa_base,
        "descuento_compra": descuento,
        "tasa_aplicada": tasa_aplicada,
        "monto_guaranies": monto_guaranies,
        "porcentaje_comision": porcentaje,
        "comision": comision,
        "total_guaranies": total,
    }


def recotizar(transaccion):
    """Cuánto saldría hoy la misma operación, con la cotización vigente.

    Lo usa la alerta de cancelación: cuando una operación se cancela porque
    cambió la cotización, el cliente ve el total nuevo antes de decidir si
    vuelve a operar. No guarda nada.

    Returns:
        dict | None: el mismo formato que ``calcular``, o ``None`` si la
        moneda ya no tiene cotización vigente.
    """
    vigente = cotizacion_vigente(transaccion.moneda)
    if vigente is None:
        return None
    return calcular(transaccion.tipo, transaccion.monto_divisa, vigente, transaccion.cliente.segmento)


def clientes_habilitados(usuario):
    """Los clientes a nombre de los cuales este usuario puede operar (RN02)."""
    return Cliente.objects.filter(usuarios=usuario).select_related("segmento")


def _descripcion_medio_pago(medio):
    if medio.tipo:
        return f"{medio.alias} ({medio.get_tipo_display()})"
    return medio.alias


def _validar(usuario, cliente, tipo, moneda, monto_divisa, medio_pago):
    """Valida que se pueda operar y devuelve la cotización vigente.

    Raises:
        OperacionInvalida: si el usuario no está asociado al cliente (RN02), el
            monto no es positivo, la moneda no tiene cotización vigente o el
            medio de pago no es del usuario.
    """
    if not clientes_habilitados(usuario).filter(pk=cliente.pk).exists():
        raise OperacionInvalida(
            "Solo podés operar a nombre de un cliente al que estés asociado."
        )
    if tipo not in Transaccion.Tipo.values:
        raise OperacionInvalida("El tipo de operación tiene que ser compra o venta.")
    if monto_divisa is None or Decimal(monto_divisa) <= 0:
        raise OperacionInvalida("El monto tiene que ser mayor que cero.")
    if not moneda.activo:
        raise OperacionInvalida(f"La moneda {moneda.codigo} no está habilitada para operar.")

    cotizacion = cotizacion_vigente(moneda)
    if cotizacion is None:
        raise OperacionInvalida(f"La moneda {moneda.codigo} no tiene una cotización vigente.")

    if medio_pago is not None and (medio_pago.usuario_id != usuario.pk or not medio_pago.activo):
        raise OperacionInvalida("Ese medio de pago no está disponible para tu usuario.")
    return cotizacion


def crear_operacion(usuario, cliente, tipo, moneda, monto_divisa, medio_pago=None):
    """Crea una operación pendiente de pago, con la cotización de este momento.

    Raises:
        OperacionInvalida: ver ``_validar``.
    """
    cotizacion = _validar(usuario, cliente, tipo, moneda, monto_divisa, medio_pago)
    calculo = calcular(tipo, monto_divisa, cotizacion, cliente.segmento)
    return Transaccion.objects.create(
        cliente=cliente,
        usuario=usuario,
        tipo=tipo,
        moneda=moneda,
        monto_divisa=Decimal(monto_divisa),
        cotizacion=cotizacion,
        medio_pago=medio_pago,
        medio_pago_descripcion=_descripcion_medio_pago(medio_pago) if medio_pago else "",
        **calculo,
    )


def cotizar(usuario, cliente, tipo, moneda, monto_divisa, medio_pago=None):
    """Calcula la operación con la cotización vigente, **sin guardarla**.

    Es lo que muestra la maqueta en el modal de confirmación: así tocar
    "Comprar" o "Vender" y no confirmar (cerrar el modal, recargar la página)
    no deja operaciones pendientes en el historial.

    Raises:
        OperacionInvalida: ver ``_validar``.
    """
    cotizacion = _validar(usuario, cliente, tipo, moneda, monto_divisa, medio_pago)
    return calcular(tipo, monto_divisa, cotizacion, cliente.segmento)


def confirmar_operacion(usuario, cliente, tipo, moneda, monto_divisa, tasa_base_vista,
                        medio_pago=None):
    """Registra la operación que el cliente confirmó, ya pagada.

    ``tasa_base_vista`` es la tasa base del cálculo que se le mostró (el de
    ``cotizar``). Si la cotización cambió desde entonces, la operación no se
    cobra: queda registrada como cancelada por cambio de cotización, con el
    cálculo que el cliente vio, igual que ``pagar`` con una pendiente.

    Returns:
        Transaccion: en estado ``PAGADA`` o ``CANCELADA``.

    Raises:
        OperacionInvalida: ver ``_validar``.
    """
    with transaccion_bd.atomic():
        cotizacion = _validar(usuario, cliente, tipo, moneda, monto_divisa, medio_pago)
        tasa_vista = Decimal(tasa_base_vista)
        precio_actual = Decimal(tasa_base_de(cotizacion, tipo))
        ahora = timezone.now()
        datos = {
            "cliente": cliente,
            "usuario": usuario,
            "tipo": tipo,
            "moneda": moneda,
            "monto_divisa": Decimal(monto_divisa),
            "cotizacion": cotizacion,
            "medio_pago": medio_pago,
            "medio_pago_descripcion": _descripcion_medio_pago(medio_pago) if medio_pago else "",
            **_calcular(tipo, monto_divisa, tasa_vista, cliente.segmento),
        }
        if precio_actual == tasa_vista:
            return Transaccion.objects.create(
                **datos, estado=Transaccion.Estado.PAGADA, fecha_pago=ahora
            )
        return Transaccion.objects.create(
            **datos,
            estado=Transaccion.Estado.CANCELADA,
            cancelada_por_cotizacion=True,
            tasa_base_nueva=precio_actual,
            fecha_cancelacion=ahora,
            motivo_cancelacion=(
                f"La cotización de {moneda.codigo} cambió antes del pago: "
                f"pasó de {tasa_vista} a {precio_actual}."
            ),
        )


def puede_gestionar(usuario, transaccion):
    """Si el usuario puede pagar o cancelar la operación: tiene que estar
    asociado al cliente, igual que para crearla (RN02)."""
    return clientes_habilitados(usuario).filter(pk=transaccion.cliente_id).exists()


def puede_ver(usuario, transaccion):
    """Si el usuario puede consultar la operación: quien opera a nombre del
    cliente, o alguno de los roles de ``VEN_TODAS``."""
    if puede_gestionar(usuario, transaccion):
        return True
    return usuario.groups.filter(name__in=VEN_TODAS).exists()


def transacciones_visibles(usuario):
    """Las operaciones que el usuario puede ver en el historial.

    Es la misma regla que ``puede_ver``, pero para una lista: los roles de
    ``VEN_TODAS`` ven todas, y el resto solo las de los clientes a los que
    está asociado (los mismos a nombre de quienes puede operar).
    """
    operaciones = Transaccion.objects.select_related("cliente", "moneda")
    if usuario.groups.filter(name__in=VEN_TODAS).exists():
        return operaciones
    return operaciones.filter(cliente__usuarios=usuario)


def filtrar_historial(operaciones, estado=None, tipo=None, moneda=None,
                      cliente=None, desde=None, hasta=None):
    """Aplica los filtros del historial. Los que llegan vacíos no filtran.

    Args:
        estado, tipo: valores de ``Transaccion.Estado`` y ``Transaccion.Tipo``;
            uno que no existe se ignora en vez de devolver una lista vacía.
        moneda (str): código, por ejemplo ``"USD"``.
        cliente (int): id del cliente.
        desde, hasta (date): rango de fechas, incluidos los dos extremos. Se
            compara por día en la zona horaria del proyecto (Asunción).
    """
    if estado in Transaccion.Estado.values:
        operaciones = operaciones.filter(estado=estado)
    if tipo in Transaccion.Tipo.values:
        operaciones = operaciones.filter(tipo=tipo)
    if moneda:
        operaciones = operaciones.filter(moneda__codigo=moneda)
    if cliente:
        operaciones = operaciones.filter(cliente_id=cliente)
    if desde:
        operaciones = operaciones.filter(fecha_creacion__date__gte=desde)
    if hasta:
        operaciones = operaciones.filter(fecha_creacion__date__lte=hasta)
    return operaciones


def pagar(transaccion, usuario):
    """Intenta pagar una operación pendiente.

    Antes de marcarla como pagada compara el precio que se usó al crearla con
    el que está vigente ahora. Si cambió, o si la moneda se quedó sin
    cotización, la operación se **cancela** en vez de pagarse: cobrarle al
    cliente una tasa que ya no es la del mercado no es válido.

    Se compara el precio y no la cotización en sí porque la cotización puede
    cambiar de dos maneras: la maqueta crea una cotización nueva y desactiva
    la anterior, pero la pantalla de Django edita la misma fila. Comparando el
    precio, las dos se detectan igual.

    Returns:
        Transaccion: la operación, en estado ``PAGADA`` o ``CANCELADA``.

    Raises:
        OperacionInvalida: si no está pendiente o el usuario no puede pagarla.
    """
    if not puede_gestionar(usuario, transaccion):
        raise OperacionInvalida("Esta operación no es de un cliente al que estés asociado.")

    with transaccion_bd.atomic():
        transaccion = Transaccion.objects.select_for_update().get(pk=transaccion.pk)
        if transaccion.estado != Transaccion.Estado.PENDIENTE:
            raise OperacionInvalida(
                f"La operación ya está {transaccion.get_estado_display().lower()}: "
                "solo se puede pagar una operación pendiente."
            )

        vigente = cotizacion_vigente(transaccion.moneda)
        precio_actual = tasa_base_de(vigente, transaccion.tipo) if vigente else None

        if precio_actual is None or Decimal(precio_actual) != transaccion.tasa_base:
            transaccion.estado = Transaccion.Estado.CANCELADA
            transaccion.cancelada_por_cotizacion = True
            transaccion.tasa_base_nueva = precio_actual
            transaccion.fecha_cancelacion = timezone.now()
            if precio_actual is None:
                transaccion.motivo_cancelacion = (
                    f"{transaccion.moneda.codigo} se quedó sin cotización vigente antes del pago."
                )
            else:
                transaccion.motivo_cancelacion = (
                    f"La cotización de {transaccion.moneda.codigo} cambió antes del pago: "
                    f"pasó de {transaccion.tasa_base} a {precio_actual}."
                )
        else:
            transaccion.estado = Transaccion.Estado.PAGADA
            transaccion.fecha_pago = timezone.now()
        transaccion.save()
    return transaccion


def cancelar(transaccion, usuario):
    """El cliente cancela por su cuenta una operación que todavía no pagó.

    Es el otro camino que RN04 le da a una operación pendiente.

    Raises:
        OperacionInvalida: si no está pendiente o el usuario no puede cancelarla.
    """
    if not puede_gestionar(usuario, transaccion):
        raise OperacionInvalida("Esta operación no es de un cliente al que estés asociado.")

    with transaccion_bd.atomic():
        transaccion = Transaccion.objects.select_for_update().get(pk=transaccion.pk)
        if transaccion.estado != Transaccion.Estado.PENDIENTE:
            raise OperacionInvalida("Solo se puede cancelar una operación pendiente de pago.")
        transaccion.estado = Transaccion.Estado.CANCELADA
        transaccion.motivo_cancelacion = "Cancelada por el usuario antes del pago."
        transaccion.fecha_cancelacion = timezone.now()
        transaccion.save()
    return transaccion
