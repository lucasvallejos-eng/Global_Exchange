from django.core.exceptions import ValidationError
from django.db.models import Count
from django.shortcuts import render, redirect, get_object_or_404

from clientes.models import Cliente
from cuentas.decorators import rol_requerido
from .models import SegmentoCliente


def _contexto_formulario(request, segmento=None, errores=None):
    """Arma el contexto del formulario de segmentos.

    Lo comparten el alta y la edición. Si la validación falla se devuelve
    también ``enviado`` con lo que el usuario había cargado, para no obligarlo
    a escribirlo de nuevo.
    """
    contexto = {
        'segmento': segmento,
        'titulo': 'Editar Segmento' if segmento else 'Nuevo Segmento',
    }
    if errores:
        contexto['errores'] = errores
        contexto['enviado'] = {
            'nombre': request.POST.get('nombre'),
            'porcentaje_comision': request.POST.get('porcentaje_comision'),
            'descuento_compra': request.POST.get('descuento_compra'),
            'descripcion': request.POST.get('descripcion'),
        }
    return contexto


#READ
@rol_requerido("administrador")
def listar_segmentos(request):
    """Lista los segmentos configurados, del porcentaje más bajo al más alto.

    Muestra además cuántos clientes tiene asignado cada segmento, para que se
    vea de un vistazo si un porcentaje está en uso antes de darlo de baja.
    """
    segmentos = SegmentoCliente.objects.annotate(cantidad_clientes=Count('clientes'))
    return render(request, 'comisiones/lista.html', {'segmentos': segmentos})


#CREATE
@rol_requerido("administrador")
def crear_segmento(request):
    """Alta de un segmento con su porcentaje de comisión."""
    if request.method == 'POST':
        segmento = SegmentoCliente(
            nombre=request.POST.get('nombre'),
            porcentaje_comision=request.POST.get('porcentaje_comision'),
            descuento_compra=request.POST.get('descuento_compra', 0),
            descripcion=request.POST.get('descripcion', ''),
        )
        # full_clean() corre los validadores del modelo (rango 0-100) y el
        # clean() propio, que evita nombres repetidos. objects.create() no
        # ejecuta ninguna de las dos cosas.
        try:
            segmento.full_clean()
        except ValidationError as e:
            return render(request, 'comisiones/formulario.html',
                          _contexto_formulario(request, errores=e.messages))
        segmento.save()
        return redirect('listar_segmentos')

    return render(request, 'comisiones/formulario.html', _contexto_formulario(request))


#UPDATE
@rol_requerido("administrador")
def editar_segmento(request, pk):
    """Edición del nombre, el porcentaje o la descripción de un segmento."""
    segmento = get_object_or_404(SegmentoCliente, pk=pk)
    if request.method == 'POST':
        segmento.nombre = request.POST.get('nombre')
        segmento.porcentaje_comision = request.POST.get('porcentaje_comision')
        segmento.descuento_compra = request.POST.get('descuento_compra', 0)
        segmento.descripcion = request.POST.get('descripcion', '')
        try:
            segmento.full_clean()
        except ValidationError as e:
            return render(request, 'comisiones/formulario.html',
                          _contexto_formulario(request, segmento=segmento, errores=e.messages))
        segmento.save()
        return redirect('listar_segmentos')

    return render(request, 'comisiones/formulario.html',
                  _contexto_formulario(request, segmento=segmento))


@rol_requerido("administrador")
def asignar_segmentos(request):
    """Asigna a cada cliente el segmento del que sale su comisión.

    Sin esta pantalla los porcentajes quedarían configurados pero sin manera
    de decir a qué cliente le toca cada uno, que es la mitad de lo que pide
    "configuración de porcentajes de comisión por tipo de cliente".

    Se resuelve en una sola pantalla, con un desplegable por cliente, porque
    son pocos clientes y así se ve toda la asignación de una vez.
    """
    if request.method == 'POST':
        segmentos_validos = set(
            SegmentoCliente.objects.filter(activo=True).values_list('pk', flat=True)
        )
        for cliente in Cliente.objects.all():
            enviado = request.POST.get(f'segmento_{cliente.pk}')
            # Un valor que no sea el id de un segmento activo se ignora en vez
            # de guardarse: el desplegable no debería mandarlo nunca, pero el
            # servidor no puede confiar en lo que llega del navegador.
            try:
                nuevo = int(enviado)
            except (TypeError, ValueError):
                nuevo = None
            if nuevo not in segmentos_validos:
                nuevo = None
            if cliente.segmento_id != nuevo:
                cliente.segmento_id = nuevo
                cliente.save(update_fields=['segmento'])
        return redirect('asignar_segmentos')

    return render(request, 'comisiones/asignar.html', {
        'clientes': Cliente.objects.select_related('segmento').all(),
        'segmentos': SegmentoCliente.objects.filter(activo=True),
    })


#DELETE
@rol_requerido("administrador")
def eliminar_segmento(request, pk):
    """Baja lógica: el segmento queda inactivo pero no se borra la fila.

    Igual criterio que en cotizaciones: si mañana una operación quedó
    registrada con este segmento, borrarlo de verdad dejaría la operación sin
    referencia.
    """
    segmento = get_object_or_404(SegmentoCliente, pk=pk)
    segmento.activo = False
    segmento.save()
    return redirect('listar_segmentos')
