from django.shortcuts import render, redirect, get_object_or_404
from cuentas.decorators import rol_requerido
from .models import Moneda


@rol_requerido("administrador")
def listar_monedas(request):
    """
    Obtiene y muestra el listado completo de monedas registradas en la plataforma.

    :param request: Objeto HttpRequest de Django.
    :return: HttpResponse con el renderizado de la plantilla 'monedas/lista.html'.
    """
    monedas = Moneda.objects.all()
    return render(request, 'monedas/lista.html', {'monedas': monedas})


@rol_requerido("administrador")
def crear_moneda(request):
    """
    Gestiona el registro de una nueva moneda en el sistema.

    Si la petición es POST, extrae los parámetros ('codigo', 'nombre', 'simbolo')
    del formulario y crea la instancia correspondiente en la base de datos.
    Si la petición es GET, renderiza el formulario de creación.

    :param request: Objeto HttpRequest con los datos del formulario (POST) o la solicitud del render.
    :return: Redirect a la vista 'listar_monedas' si se guarda con éxito,
             o HttpResponse con la plantilla 'monedas/formulario.html'.
    """
    if request.method == 'POST':
        Moneda.objects.create(
            codigo=request.POST.get('codigo'),
            nombre=request.POST.get('nombre'),
            simbolo=request.POST.get('simbolo'),
        )
        return redirect('listar_monedas')
    return render(request, 'monedas/formulario.html', {'titulo': 'Nueva Moneda'})


@rol_requerido("administrador")
def editar_moneda(request, pk):
    """
    Permite la modificación de los datos de una moneda existente.

    Busca la instancia de :class:`Moneda` mediante su clave primaria (`pk`).
    Si la petición es POST, actualiza sus campos ('codigo', 'nombre', 'simbolo')
    y guarda los cambios. En caso contrario, despliega el formulario poblado con la información actual.

    :param request: Objeto HttpRequest.
    :param pk: Clave primaria (ID) de la moneda a modificar.
    :return: Redirect a 'listar_monedas' al actualizar, o HttpResponse con el formulario de edición.
    :raises Http404: Si no existe ninguna moneda con la clave primaria especificada.
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
    """
    Elimina un registro de moneda de la base de datos.

    Recupera la instancia de :class:`Moneda` correspondiente al `pk` recibido y la remueve.

    :param request: Objeto HttpRequest.
    :param pk: Clave primaria (ID) de la moneda a eliminar.
    :return: Redirect a la vista 'listar_monedas'.
    :raises Http404: Si la moneda con el `pk` provisto no existe.
    """
    moneda = get_object_or_404(Moneda, pk=pk)
    moneda.delete()
    return redirect('listar_monedas')