"""Vistas para la gestión de Monedas mediante plantillas HTML (CRUD)."""
from django.shortcuts import render, redirect, get_object_or_404
from cuentas.decorators import rol_requerido
from .models import Moneda

#READ
@rol_requerido("administrador")
def listar_monedas(request):
    """Muestra la lista completa de monedas registradas en el sistema.

    Requiere rol de administrador.

    Args:
        request (HttpRequest): Objeto de la solicitud HTTP.

    Returns:
        HttpResponse: Renderiza la plantilla ``monedas/lista.html`` con el queryset
        de todas las monedas.
    """
    monedas = Moneda.objects.all()
    return render(request, 'monedas/lista.html', {'monedas': monedas})

#CREATE
@rol_requerido("administrador")
def crear_moneda(request):
    """Despliega el formulario de alta y procesa la creación de una nueva moneda.

    Requiere rol de administrador. Si la petición es ``POST``, procesa los campos
    recibidos del formulario y redirecciona a la lista de monedas.

    Args:
        request (HttpRequest): Objeto de la solicitud HTTP.

    Returns:
        HttpResponse: Renderiza ``monedas/formulario.html`` (GET) o redirige
        a ``listar_monedas`` (POST).
    """
    if request.method == 'POST':
        Moneda.objects.create(
            codigo=request.POST.get('codigo'),
            nombre=request.POST.get('nombre'),
            simbolo=request.POST.get('simbolo'),
        )
        return redirect('listar_monedas')
    return render(request, 'monedas/formulario.html', {'titulo': 'Nueva Moneda'})

#UPDATE
@rol_requerido("administrador")
def editar_moneda(request, pk):
    """Permite modificar los datos de una moneda existente.

    Requiere rol de administrador. Carga la moneda por su clave primaria y actualiza
    sus valores al enviar el formulario vía ``POST``.

    Args:
        request (HttpRequest): Objeto de la solicitud HTTP.
        pk (int): Identificador primario de la moneda a editar.

    Returns:
        HttpResponse: Renderiza ``monedas/formulario.html`` prellenado (GET) o redirige
        a ``listar_monedas`` tras guardar (POST).

    Raises:
        Http404: Si no existe ninguna moneda con la clave primaria especificada.
    """
    moneda = get_object_or_404(Moneda, pk=pk)
    if request.method == 'POST':
        moneda.codigo = request.POST.get('codigo')
        moneda.nombre = request.POST.get('nombre')
        moneda.simbolo = request.POST.get('simbolo')
        moneda.save()
        return redirect('listar_monedas')
    return render(request, 'monedas/formulario.html', {'moneda': moneda, 'titulo': 'Editar Moneda'})

#DELETE
@rol_requerido("administrador")
def eliminar_moneda(request, pk):
    """Elimina una moneda de la base de datos.

    Requiere rol de administrador.

    Args:
        request (HttpRequest): Objeto de la solicitud HTTP.
        pk (int): Identificador primario de la moneda a eliminar.

    Returns:
        HttpResponseRedirect: Redirecciona al listado de monedas tras la eliminación.

    Raises:
        Http404: Si no existe ninguna moneda asociada a la clave primaria.
    """
    moneda = get_object_or_404(Moneda, pk=pk)
    moneda.delete()
    return redirect('listar_monedas')