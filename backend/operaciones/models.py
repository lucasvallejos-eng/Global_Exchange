from django.db import models
from django.utils import timezone
from datetime import timedelta
from django.conf import settings  # <-- Importante

class Transaccion(models.Model):
    ESTADOS = [
        ('PENDIENTE_PAGO', 'Pendiente de Pago'),
        ('COMPLETADA', 'Completada'),
        ('CANCELADA_COTIZACION', 'Cancelada por cambio de cotización'),
        ('EXPIRADA', 'Expirada'),
    ]

    cliente = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE,
        related_name='transacciones'
    )
    
    moneda_origen = models.ForeignKey('monedas.Moneda', related_name='transacciones_origen', on_delete=models.PROTECT)
    moneda_destino = models.ForeignKey('monedas.Moneda', related_name='transacciones_destino', on_delete=models.PROTECT)
    
    monto_origen = models.DecimalField(max_digits=12, decimal_places=2)
    monto_destino = models.DecimalField(max_digits=12, decimal_places=2)
    
    cotizacion_congelada = models.DecimalField(max_digits=12, decimal_places=4)
    
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    expira_en = models.DateTimeField()
    
    estado = models.CharField(max_length=30, choices=ESTADOS, default='PENDIENTE_PAGO')

    def save(self, *args, **kwargs):
        if not self.expira_en:
            self.expira_en = timezone.now() + timedelta(minutes=5)
        super().save(*args, **kwargs)

    def esta_expirada(self) -> bool:
        return timezone.now() > self.expira_en