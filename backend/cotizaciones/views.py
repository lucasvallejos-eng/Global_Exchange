from django.core.exceptions import ValidationError
from django.shortcuts import render, redirect, get_object_or_404
from cuentas.decorators import rol_requerido
from .models import Cotizacion
from monedas.models import Moneda


def _contexto_formulario(request, cotizacion=None, errores=None):
    """Arma el contexto del formulario de cotizaciones.

    Lo comparten el alta y la edición. Cuando la validación falla se le pasa
    ``errores`` y además se devuelve ``enviado`` con lo que el usuario había
    escrito, para no hacerle cargar todo de nuevo.
    """
    contexto = {
        'monedas': Moneda.objects.all(),
        'cotizacion': cotizacion,
        'titulo': 'Editar Cotización' if cotizacion else 'Nueva Cotización',
    }
    if errores:
        contexto['errores'] = errores
        contexto['enviado'] = {
            'moneda': request.POST.get('moneda'),
            'precio_compra': request.POST.get('precio_compra'),
            'precio_venta': request.POST.get('precio_venta'),
        }
    return contexto


# Las cotizaciones son las tasas del sistema, y según la ERS el
# analista_cambiario está para "modificar tasas". Por eso tiene los mismos
# permisos que el administrador sobre este módulo. Lo que sigue fuera de su
# alcance es la administración: monedas, clientes, medios de pago y comisiones.
GESTIONAN_TASAS = ("administrador", "analista_cambiario")


#READ
@rol_requerido(*GESTIONAN_TASAS)
def listar_cotizaciones(request):
    cotizaciones = Cotizacion.objects.select_related('moneda').all()
    return render(request, 'cotizaciones/lista.html', {'cotizaciones': cotizaciones})

#CREATE
@rol_requerido(*GESTIONAN_TASAS)
def crear_cotizacion(request):
    if request.method == 'POST':
        moneda = get_object_or_404(Moneda, id=request.POST.get('moneda'))
        cotizacion = Cotizacion(
            moneda=moneda,
            precio_compra=request.POST.get('precio_compra'),
            precio_venta=request.POST.get('precio_venta'),
        )
        # full_clean() es lo que dispara Cotizacion.clean(), donde vive RN10
        # (la tasa de compra siempre menor que la de venta). Con
        # Cotizacion.objects.create() esa validación NO se ejecuta: Django solo
        # la corre desde los formularios o desde full_clean().
        try:
            cotizacion.full_clean()
        except ValidationError as e:
            return render(request, 'cotizaciones/formulario.html',
                          _contexto_formulario(request, errores=e.messages))
        cotizacion.save()
        return redirect('listar_cotizaciones')

    return render(request, 'cotizaciones/formulario.html', _contexto_formulario(request))

#UPDATE
@rol_requerido(*GESTIONAN_TASAS)
def editar_cotizacion(request, pk):
    cotizacion = get_object_or_404(Cotizacion, pk=pk)
    if request.method == 'POST':
        # get_object_or_404 en vez de asignar el id crudo: full_clean() no
        # comprueba que la moneda exista (eso lo hace recién la base de datos),
        # así que un id inventado terminaría en un error 500 al guardar.
        cotizacion.moneda = get_object_or_404(Moneda, id=request.POST.get('moneda'))
        cotizacion.precio_compra = request.POST.get('precio_compra')
        cotizacion.precio_venta = request.POST.get('precio_venta')
        # Misma razón que en el alta: sin full_clean() se puede guardar una
        # cotización que viola RN10.
        try:
            cotizacion.full_clean()
        except ValidationError as e:
            return render(request, 'cotizaciones/formulario.html',
                          _contexto_formulario(request, cotizacion=cotizacion, errores=e.messages))
        cotizacion.save()
        return redirect('listar_cotizaciones')

    return render(request, 'cotizaciones/formulario.html',
                  _contexto_formulario(request, cotizacion=cotizacion))

#DELETE
@rol_requerido(*GESTIONAN_TASAS)
def eliminar_cotizacion(request, pk):
    cotizacion = get_object_or_404(Cotizacion, pk=pk)
    cotizacion.activa = False  # Borrado lógico
    cotizacion.save()
    return redirect('listar_cotizaciones')
