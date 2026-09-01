from django.shortcuts import render, redirect, get_object_or_404
from cuentas.decorators import rol_requerido
from .models import Cotizacion
from monedas.models import Moneda

#READ
@rol_requerido("administrador")
def listar_cotizaciones(request):
    cotizaciones = Cotizacion.objects.select_related('moneda').all()
    return render(request, 'cotizaciones/lista.html', {'cotizaciones': cotizaciones})

#CREATE
@rol_requerido("administrador", "analista_cambiario")
def crear_cotizacion(request):
    monedas = Moneda.objects.all()
    if request.method == 'POST':
        moneda_id = request.POST.get('moneda')
        precio_compra = request.POST.get('precio_compra')
        precio_venta = request.POST.get('precio_venta')

        moneda = get_object_or_404(Moneda, id=moneda_id)
        Cotizacion.objects.create(
            moneda=moneda,
            precio_compra=precio_compra,
            precio_venta=precio_venta
        )
        return redirect('listar_cotizaciones')

    return render(request, 'cotizaciones/formulario.html', {'monedas': monedas, 'titulo': 'Nueva Cotización'})

#UPDATE
@rol_requerido("administrador")
def editar_cotizacion(request, pk):
    cotizacion = get_object_or_404(Cotizacion, pk=pk)
    monedas = Moneda.objects.all()
    if request.method == 'POST':
        cotizacion.moneda_id = request.POST.get('moneda')
        cotizacion.precio_compra = request.POST.get('precio_compra')
        cotizacion.precio_venta = request.POST.get('precio_venta')
        cotizacion.save()
        return redirect('listar_cotizaciones')

    return render(request, 'cotizaciones/formulario.html', {'cotizacion': cotizacion, 'monedas': monedas, 'titulo': 'Editar Cotización'})

#DELETE
@rol_requerido("administrador")
def eliminar_cotizacion(request, pk):
    cotizacion = get_object_or_404(Cotizacion, pk=pk)
    cotizacion.activa = False  # Borrado lógico
    cotizacion.save()
    return redirect('listar_cotizaciones')