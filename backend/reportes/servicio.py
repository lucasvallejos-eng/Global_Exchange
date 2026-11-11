"""Reportes de transacciones y ganancias de la casa de cambios.

No hay modelos propios: todo se calcula sobre las operaciones **pagadas**
(``operaciones.Transaccion``). Una pendiente, cancelada o anulada no movió
plata, así que no cuenta ni como volumen ni como ganancia. Por ahora no entran
las operaciones de la caja (ventanilla).

**Qué es la ganancia de una operación** (supuesto del equipo; está en un solo
lugar, ``ganancia_de``, para poder cambiarlo):

- La **comisión** cobrada, más
- el **margen de cambio**: la diferencia entre la tasa que se le aplicó al
  cliente y el precio medio de la cotización (el promedio entre compra y
  venta), por el monto de divisa. Cuando la casa vende, gana lo que cobró por
  encima del precio medio; cuando compra, lo que pagó por debajo.

El margen puede ser **negativo**: si el descuento del segmento del cliente es
más grande que el spread, la casa vendió por debajo del precio medio. El
reporte lo muestra tal cual, porque es justamente lo que el analista necesita
ver.

El margen es una estimación: se calcula con la cotización que quedó enlazada
a la operación, y si esa cotización ya no existe, cuenta como cero.
"""
from collections import defaultdict
from datetime import timedelta
from decimal import ROUND_HALF_UP, Decimal

from django.utils import timezone

from operaciones.models import Transaccion

GUARANI = Decimal("1")
CERO = Decimal("0")
# Tope de días que se rellenan con cero en la serie diaria.
MAXIMO_DE_DIAS = 366


def pagadas(desde=None, hasta=None, moneda=None, tipo=None, cliente=None):
    """Las operaciones pagadas que cumplen los filtros, de la más nueva a la más vieja.

    Args:
        desde, hasta (date): rango por **fecha de pago**, incluidos los dos
            extremos, en la zona horaria del proyecto (Asunción).
        moneda (str): código, por ejemplo ``"USD"``.
        tipo (str): ``COMPRA`` o ``VENTA``; otro valor se ignora.
        cliente (int): id del cliente.
    """
    operaciones = Transaccion.objects.select_related(
        "cliente", "moneda", "cotizacion"
    ).filter(estado=Transaccion.Estado.PAGADA).order_by("-fecha_pago")
    if desde:
        operaciones = operaciones.filter(fecha_pago__date__gte=desde)
    if hasta:
        operaciones = operaciones.filter(fecha_pago__date__lte=hasta)
    if moneda:
        operaciones = operaciones.filter(moneda__codigo=moneda)
    if tipo in Transaccion.Tipo.values:
        operaciones = operaciones.filter(tipo=tipo)
    if cliente:
        operaciones = operaciones.filter(cliente_id=cliente)
    return operaciones


def margen_de_cambio(transaccion):
    """Lo que la casa ganó (o perdió) por la tasa, en guaraníes. Ver el módulo."""
    cotizacion = transaccion.cotizacion
    if cotizacion is None:
        return CERO
    precio_medio = (Decimal(cotizacion.precio_compra) + Decimal(cotizacion.precio_venta)) / 2
    if transaccion.tipo == Transaccion.Tipo.COMPRA:
        diferencia = Decimal(transaccion.tasa_aplicada) - precio_medio
    else:
        diferencia = precio_medio - Decimal(transaccion.tasa_aplicada)
    return (Decimal(transaccion.monto_divisa) * diferencia).quantize(GUARANI, ROUND_HALF_UP)


def ganancia_de(transaccion):
    """La ganancia de una operación, separada en sus dos partes.

    Returns:
        dict: ``comision``, ``margen`` y ``total`` (la suma), en guaraníes.
    """
    comision = Decimal(transaccion.comision)
    margen = margen_de_cambio(transaccion)
    return {"comision": comision, "margen": margen, "total": comision + margen}


def _acumulador():
    return {"operaciones": 0, "volumen": CERO, "comisiones": CERO, "margen": CERO, "ganancia": CERO}


def _sumar(acumulado, transaccion, ganancia):
    acumulado["operaciones"] += 1
    acumulado["volumen"] += Decimal(transaccion.monto_guaranies)
    acumulado["comisiones"] += ganancia["comision"]
    acumulado["margen"] += ganancia["margen"]
    acumulado["ganancia"] += ganancia["total"]


def _dia_de(transaccion):
    return timezone.localtime(transaccion.fecha_pago or transaccion.fecha_creacion).date()


def resumen(operaciones, desde=None, hasta=None):
    """Los números del tablero: totales y desgloses por tipo, moneda y día.

    Args:
        operaciones: las operaciones a resumir (ver ``pagadas``).
        desde, hasta (date): extremos de la serie diaria. Si no se pasan, la
            serie va del primer al último día con operaciones.

    Returns:
        dict: ``totales``; ``por_tipo`` (``COMPRA`` y ``VENTA``, siempre los
        dos); ``por_moneda`` (de mayor a menor ganancia, con ``codigo`` y
        ``monto_divisa``); y ``por_dia`` (en orden, con ``fecha`` y los días
        sin operaciones en cero, para que el gráfico no los saltee).
    """
    totales = _acumulador()
    por_tipo = {tipo: _acumulador() for tipo in Transaccion.Tipo.values}
    por_moneda = defaultdict(lambda: {**_acumulador(), "monto_divisa": CERO})
    por_dia = defaultdict(_acumulador)

    for transaccion in operaciones:
        ganancia = ganancia_de(transaccion)
        _sumar(totales, transaccion, ganancia)
        _sumar(por_tipo[transaccion.tipo], transaccion, ganancia)
        moneda = por_moneda[transaccion.moneda.codigo]
        _sumar(moneda, transaccion, ganancia)
        moneda["monto_divisa"] += Decimal(transaccion.monto_divisa)
        _sumar(por_dia[_dia_de(transaccion)], transaccion, ganancia)

    return {
        "totales": totales,
        "por_tipo": por_tipo,
        "por_moneda": sorted(
            ({"codigo": codigo, **datos} for codigo, datos in por_moneda.items()),
            key=lambda fila: (-fila["ganancia"], fila["codigo"]),
        ),
        "por_dia": _serie_diaria(por_dia, desde, hasta),
    }


def _serie_diaria(por_dia, desde, hasta):
    if not por_dia:
        return []
    primero = desde or min(por_dia)
    ultimo = hasta or max(por_dia)
    # Un rango enorme no se rellena entero: se muestran los últimos días.
    primero = max(primero, ultimo - timedelta(days=MAXIMO_DE_DIAS - 1))
    serie, dia = [], primero
    while dia <= ultimo:
        serie.append({"fecha": dia, **por_dia.get(dia, _acumulador())})
        dia += timedelta(days=1)
    return serie
