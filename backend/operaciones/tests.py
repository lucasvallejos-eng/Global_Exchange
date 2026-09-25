from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from django.contrib.auth import get_user_model
from monedas.models import Moneda
from operaciones.models import Transaccion

User = get_user_model()

class TransaccionPagoTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='cliente_test', password='password123')
        self.usd = Moneda.objects.create(nombre='Dólar', codigo='USD', cotizacion_actual=7300.00)
        self.pyg = Moneda.objects.create(nombre='Guaraní', codigo='PYG', cotizacion_actual=1.00)
        
        self.transaccion = Transaccion.objects.create(
            cliente=self.user,
            moneda_origen=self.usd,
            moneda_destino=self.pyg,
            monto_origen=100.00,
            monto_destino=730000.00,
            cotizacion_congelada=7300.00
        )
        self.client.force_login(self.user)

    def test_pago_exitoso_si_cotizacion_se_mantiene(self):
        url = reverse('procesar_pago', kwargs={'pk': self.transaccion.pk})
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.transaccion.refresh_from_db()
        self.assertEqual(self.transaccion.estado, 'COMPLETADA')

    def test_cancelacion_si_cambia_cotizacion(self):
        # Simulamos una fluctuación de cotización antes del cobro
        self.usd.cotizacion_actual = 7400.00
        self.usd.save()

        url = reverse('procesar_pago', kwargs={'pk': self.transaccion.pk})
        response = self.client.post(url)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.transaccion.refresh_from_db()
        self.assertEqual(self.transaccion.estado, 'CANCELADA_COTIZACION')