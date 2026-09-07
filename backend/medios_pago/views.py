from django.shortcuts import render, redirect, get_object_or_404
from cuentas.decorators import rol_requerido
from .models import MedioPago

#READ
@rol_requerido("cliente", "administrador", "cajero")
def listar_medios_pago(request):
    # Si es cliente, solo ve sus propios medios de pago
    if request.user.groups.filter(name="cliente").exists():
        medios = MedioPago.objects.filter(usuario=request.user, activo=True)
    else:
        medios = MedioPago.objects.filter(activo=True)
        
    return render(request, 'medios_pago/lista.html', {'medios': medios})

#CREATE
@rol_requerido("cliente", "administrador")
def crear_medio_pago(request):
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
    medio = get_object_or_404(MedioPago, pk=pk, usuario=request.user)
    medio.activo = False
    medio.save()
    return redirect('listar_medios_pago')