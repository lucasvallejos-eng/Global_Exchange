from django.shortcuts import render
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from .models import Transaccion

@api_view(['POST'])
def procesar_pago(request, pk):
    """
    Procesa el pago de una transacción verificando la validez de la cotización.

    :param pk: ID de la transacción a procesar.
    :return: Response con el resultado del pago o la cancelación por cambio de precio.
    """
    try:
        transaccion = Transaccion.objects.get(pk=pk)
    except Transaccion.DoesNotExist:
        return Response({'error': 'Transacción no encontrada'}, status=status.HTTP_404_NOT_FOUND)

    # Cotización actual obtenida del modelo Moneda
    cotizacion_actual = transaccion.moneda_origen.cotizacion_actual

    # Validar si venció el tiempo o varió la cotización
    if transaccion.esta_expirada() or cotizacion_actual != transaccion.cotizacion_congelada:
        transaccion.estado = 'CANCELADA_COTIZACION'
        transaccion.save()
        return Response({
            'error': 'La cotización ha cambiado o expiró. La transacción fue cancelada.',
            'estado': transaccion.estado
        }, status=status.HTTP_400_BAD_REQUEST)

    # Si todo está correcto, completar
    transaccion.estado = 'COMPLETADA'
    transaccion.save()
    return Response({'mensaje': 'Pago procesado exitosamente', 'estado': transaccion.estado})

# Create your views here.
