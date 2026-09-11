"""Consulta de tasas y simulador de conversión.

Cubre dos ítems del alcance del Sprint 2: "Visualización de tasas" y
"Simulador conversión". Son de solo lectura: no crean ni modifican nada, solo
leen las cotizaciones vigentes que cargó el administrador o el analista
cambiario.

Están separados del ABM de cotizaciones a propósito. El ABM es para quien
administra el sistema; esto es lo que mira cualquier usuario, incluso uno sin
cliente asociado (RN02: sin cliente asociado, solo consulta de tasas).
"""
from decimal import Decimal, InvalidOperation

from django.shortcuts import render

from cuentas.decorators import rol_requerido
from cotizaciones.models import Cotizacion
from monedas.models import Moneda

# Todos los roles del sistema. La consulta de tasas está permitida a cualquier
# usuario autenticado.
TODOS_LOS_ROLES = (
    "administrador",
    "analista_cambiario",
    "cajero",
    "cliente",
)


def _cotizaciones_vigentes():
    """Devuelve la última cotización activa de cada moneda activa.

    Una moneda puede tener muchas cotizaciones históricas; la vigente es la
    más reciente que siga activa. El modelo ya ordena por fecha descendente
    (``Cotizacion.Meta.ordering``), así que la primera de cada moneda es la
    que vale.
    """
    vigentes = []
    for moneda in Moneda.objects.filter(activo=True):
        cotizacion = (
            Cotizacion.objects
            .filter(moneda=moneda, activa=True)
            .first()
        )
        if cotizacion:
            vigentes.append(cotizacion)
    return vigentes


@rol_requerido(*TODOS_LOS_ROLES)
def ver_tasas(request):
    """Muestra la tasa de compra y de venta vigente de cada moneda."""
    return render(request, 'tasas/tasas.html', {
        'cotizaciones': _cotizaciones_vigentes(),
    })


@rol_requerido(*TODOS_LOS_ROLES)
def simulador(request):
    """Simula una conversión contra la cotización vigente de una moneda.

    Las tasas se expresan en guaraníes por unidad de moneda extranjera, así
    que la cuenta va en un sentido u otro según quién compra:

    - El cliente **vende** su divisa: la casa se la compra a ``precio_compra``,
      y el cliente recibe ``monto * precio_compra`` guaraníes.
    - El cliente **compra** divisa: la casa se la vende a ``precio_venta``, y
      el cliente paga ``monto * precio_venta`` guaraníes.

    Como RN10 obliga a que la compra sea menor que la venta, la casa siempre
    gana la diferencia entre las dos puntas.

    No aplica comisión: el cálculo de comisión y tasa aplicada corresponde a
    la operación de compra/venta del Sprint 3.
    """
    contexto = {'monedas': Moneda.objects.filter(activo=True)}

    if request.method != 'POST':
        return render(request, 'tasas/simulador.html', contexto)

    # Se conserva lo cargado para que el formulario no se vacíe al responder.
    contexto['enviado'] = {
        'moneda': request.POST.get('moneda'),
        'monto': request.POST.get('monto'),
        'operacion': request.POST.get('operacion'),
    }

    operacion = request.POST.get('operacion')
    if operacion not in ('compra', 'venta'):
        contexto['error'] = "Elegí si querés comprar o vender la divisa."
        return render(request, 'tasas/simulador.html', contexto)

    try:
        monto = Decimal(request.POST.get('monto') or '')
    except (InvalidOperation, TypeError):
        contexto['error'] = "El monto tiene que ser un número."
        return render(request, 'tasas/simulador.html', contexto)

    if monto <= 0:
        contexto['error'] = "El monto tiene que ser mayor que cero."
        return render(request, 'tasas/simulador.html', contexto)

    cotizacion = (
        Cotizacion.objects
        .filter(moneda_id=request.POST.get('moneda'), activa=True)
        .select_related('moneda')
        .first()
    )
    if cotizacion is None:
        contexto['error'] = "Esa moneda no tiene una cotización vigente."
        return render(request, 'tasas/simulador.html', contexto)

    # "compra" y "venta" están dichos desde el lado del cliente: si el cliente
    # compra divisa, la casa se la vende, y por lo tanto se usa precio_venta.
    if operacion == 'compra':
        tasa = cotizacion.precio_venta
        leyenda = f"Comprás {monto} {cotizacion.moneda.codigo} y pagás"
    else:
        tasa = cotizacion.precio_compra
        leyenda = f"Vendés {monto} {cotizacion.moneda.codigo} y recibís"

    contexto['resultado'] = {
        'monto': monto,
        'moneda': cotizacion.moneda,
        'operacion': operacion,
        'tasa': tasa,
        'leyenda': leyenda,
        'total': monto * tasa,
        'fecha_cotizacion': cotizacion.fecha,
    }
    return render(request, 'tasas/simulador.html', contexto)
