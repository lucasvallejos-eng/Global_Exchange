"""Vistas para la gestión de Medios de Pago mediante plantillas HTML (CRUD)."""
from django.shortcuts import render, redirect, get_object_or_404
from cuentas.decorators import rol_requerido
from .models import MedioPago

#READ
@rol_requerido("cliente", "administrador", "cajero")
def listar_medios_pago(request):
    """Muestra el listado de medios de pago activos en el sistema.

    Filtra los resultados dependiendo del rol del usuario autenticado: si el usuario
    pertenece al grupo "cliente", solo visualiza sus propios medios de pago; para
    administradores y cajeros muestra todos los registros activos del sistema.

    Args:
        request (HttpRequest): Objeto de la solicitud HTTP.

    Returns:
        HttpResponse: Renderiza la plantilla ``medios_pago/lista.html`` con los
        medios de pago filtrados.
    """
    # Si es cliente, solo ve sus propios medios de pago
    if request.user.groups.filter(name="cliente").exists():
        medios = MedioPago.objects.filter(usuario=request.user, activo=True)
    else:
        medios = MedioPago.objects.filter(activo=True)
        
    return render(request, 'medios_pago/lista.html', {'medios': medios})

#CREATE
@rol_requerido("cliente", "administrador")
def crear_medio_pago(request):
    """Despliega el formulario y procesa el alta de un nuevo medio de pago.

    Asigna automáticamente el usuario en sesión como propietario del registro.

    Args:
        request (HttpRequest): Objeto de la solicitud HTTP.

    Returns:
        HttpResponse: Renderiza ``medios_pago/formulario.html`` con las opciones de tipo (GET)
        o redirecciona a ``listar_medios_pago`` tras registrar (POST).
    """
    if request.method == 'POST':
        MedioPago.objects.create(
            usuario=request.user,
            tipo=request.POST.get('tipo'),
            alias=request.POST.get('alias'),
            numero_cuenta_o_tarjeta=request.POST.get('numero'),
            banco_o_proveedor=request.POST.get('banco')
        )
        return redirect('listar_medios_pago')

    return render(request, 'medios_pago/formulario.html', {
        'tipos': MedioPago.TIPO_CHOICES,
        'titulo': 'Registrar Medio de Pago'
    })

#UPDATE
@rol_requerido("cliente", "administrador")
def editar_medio_pago(request, pk):
    """Permite modificar un medio de pago perteneciente al usuario en sesión.

    Args:
        request (HttpRequest): Objeto de la solicitud HTTP.
        pk (int): Identificador primario del medio de pago a modificar.

    Returns:
        HttpResponse: Renderiza ``medios_pago/formulario.html`` prellenado (GET)
        o redirecciona a ``listar_medios_pago`` tras guardar los cambios (POST).

    Raises:
        Http404: Si el medio de pago no existe o no pertenece al usuario autenticado.
    """
    medio = get_object_or_404(MedioPago, pk=pk, usuario=request.user)
    if request.method == 'POST':
        medio.tipo = request.POST.get('tipo')
        medio.alias = request.POST.get('alias')
        medio.numero_cuenta_o_tarjeta = request.POST.get('numero')
        medio.banco_o_proveedor = request.POST.get('banco')
        medio.save()
        return redirect('listar_medios_pago')

    return render(request, 'medios_pago/formulario.html', {
        'medio': medio,
        'tipos': MedioPago.TIPO_CHOICES,
        'titulo': 'Editar Medio de Pago'
    })

#DELETE
@rol_requerido("cliente", "administrador")
def eliminar_medio_pago(request, pk):
    """Aplica un borrado lógico marcando el medio de pago como inactivo.

    Args:
        request (HttpRequest): Objeto de la solicitud HTTP.
        pk (int): Identificador primario del medio de pago a desactivar.

    Returns:
        HttpResponseRedirect: Redirecciona al listado general de medios de pago.

    Raises:
        Http404: Si el medio de pago no existe o no pertenece al usuario autenticado.
    """
    medio = get_object_or_404(MedioPago, pk=pk, usuario=request.user)
    medio.activo = False
    medio.save()
    return redirect('listar_medios_pago')