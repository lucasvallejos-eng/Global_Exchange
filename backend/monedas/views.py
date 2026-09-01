from django.shortcuts import render, redirect, get_object_or_404
from cuentas.decorators import rol_requerido
from .models import Moneda

#READ
@rol_requerido("administrador")
def listar_monedas(request):
    monedas = Moneda.objects.all()
    return render(request, 'monedas/lista.html', {'monedas': monedas})

#CREATE
@rol_requerido("administrador")
def crear_moneda(request):
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
    moneda = get_object_or_404(Moneda, pk=pk)
    moneda.delete()
    return redirect('listar_monedas')