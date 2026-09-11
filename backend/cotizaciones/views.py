"""Vistas para la gestión de Cotizaciones mediante plantillas HTML (CRUD)."""
from django.core.exceptions import ValidationError
from django.shortcuts import render, redirect, get_object_or_404
from cuentas.decorators import rol_requerido
from .models import Cotizacion
from monedas.models import Moneda


def _contexto_formulario(request, cotizacion=None, errores=None):
    """Construye el diccionario de contexto para renderizar el formulario de cotización.

    Compartido por las vistas de creación y edición. En caso de fallas de validación,
    preserva los datos ingresados en la solicitud `POST` dentro de la clave ``enviado``
    para evitar que el usuario vuelva a completar el formulario.

    Args:
        request (HttpRequest): Objeto de la solicitud HTTP.
        cotizacion (Cotizacion, optional): Instancia del modelo a editar. Por defecto es None.
        errores (list, optional): Lista de mensajes de error de validación. Por defecto es None.

    Returns:
        dict: Diccionario estructurado con las monedas disponibles, la cotización,
        el título de la página y los datos o errores de formulario.
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
    """Muestra la lista de todas las cotizaciones registradas.

    Permite el acceso a administradores y analistas cambiarios. Optimiza la consulta
    a la base de datos precargando la moneda asociada mediante ``select_related``.

    Args:
        request (HttpRequest): Objeto de la solicitud HTTP.

    Returns:
        HttpResponse: Renderiza la plantilla ``cotizaciones/lista.html`` con el queryset.
    """
    cotizaciones = Cotizacion.objects.select_related('moneda').all()
    return render(request, 'cotizaciones/lista.html', {'cotizaciones': cotizaciones})

#CREATE
@rol_requerido(*GESTIONAN_TASAS)
def crear_cotizacion(request):
    """Despliega y procesa el formulario para dar de alta una nueva cotización.

    Ejecuta el método ``full_clean()`` para hacer cumplir la regla de negocio RN10
    (la tasa de compra siempre debe ser menor a la de venta) antes de persistir los datos.

    Args:
        request (HttpRequest): Objeto de la solicitud HTTP.

    Returns:
        HttpResponse: Renderiza ``cotizaciones/formulario.html`` (GET o fallo en validación)
        o redirige a ``listar_cotizaciones`` (POST exitoso).

    Raises:
        Http404: Si el identificador de la moneda enviado en el formulario no existe.
    """
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
    """Permite modificar los datos de una cotización existente.

    Carga la cotización mediante su clave primaria y valida la regla RN10 a través de
    ``full_clean()`` antes de guardar la actualización.

    Args:
        request (HttpRequest): Objeto de la solicitud HTTP.
        pk (int): Identificador primario de la cotización a editar.

    Returns:
        HttpResponse: Renderiza ``cotizaciones/formulario.html`` (GET o fallo en validación)
        o redirige a ``listar_cotizaciones`` tras guardar la modificación (POST).

    Raises:
        Http404: Si la cotización o la moneda especificada no existen en la base de datos.
    """
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
    """Aplica un borrado lógico sobre la cotización seleccionada.

    Cambia el estado del campo ``activa`` a ``False`` sin eliminar físicamente
    el registro de la base de datos.

    Args:
        request (HttpRequest): Objeto de la solicitud HTTP.
        pk (int): Identificador primario de la cotización.

    Returns:
        HttpResponseRedirect: Redirecciona al listado general de cotizaciones.

    Raises:
        Http404: Si no existe ninguna cotización asociada al identificador.
    """
    cotizacion = get_object_or_404(Cotizacion, pk=pk)
    cotizacion.activa = False  # Borrado lógico
    cotizacion.save()
    return redirect('listar_cotizaciones')
