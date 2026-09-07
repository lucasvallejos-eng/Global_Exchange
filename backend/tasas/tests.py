import time
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse

from cotizaciones.models import Cotizacion
from monedas.models import Moneda

User = get_user_model()


class BaseTasasTest(TestCase):
    """Datos y sesión que comparten los tests de tasas y simulador."""

    def setUp(self):
        self.usd = Moneda.objects.create(codigo="USD", nombre="Dólar", simbolo="$")
        self.cotizacion = Cotizacion.objects.create(
            moneda=self.usd, precio_compra=7300, precio_venta=7400
        )

        grupo_cliente, _ = Group.objects.get_or_create(name="cliente")
        self.usuario = User.objects.create_user(username="un_cliente")
        self.usuario.groups.add(grupo_cliente)

        self.client.force_login(self.usuario)
        session = self.client.session
        session["oidc_id_token_expiration"] = time.time() + 3600
        session.save()


class VerTasasTest(BaseTasasTest):
    def test_un_cliente_puede_consultar_las_tasas(self):
        """RN02: sin cliente asociado igual se pueden consultar las tasas."""
        respuesta = self.client.get(reverse('ver_tasas'))
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "USD")

    def test_no_muestra_cotizaciones_anuladas(self):
        self.cotizacion.activa = False
        self.cotizacion.save()

        respuesta = self.client.get(reverse('ver_tasas'))
        self.assertContains(respuesta, "No hay cotizaciones vigentes")

    def test_muestra_la_cotizacion_mas_reciente(self):
        """Si hay varias, vale la última cargada."""
        Cotizacion.objects.create(moneda=self.usd, precio_compra=7500, precio_venta=7600)

        respuesta = self.client.get(reverse('ver_tasas'))
        self.assertContains(respuesta, "7600")
        self.assertNotContains(respuesta, "7400")


class SimuladorTest(BaseTasasTest):
    def test_comprar_divisa_usa_el_precio_de_venta(self):
        """Si el cliente compra, la casa vende: se aplica precio_venta."""
        respuesta = self.client.post(reverse('simulador'), {
            'operacion': 'compra', 'moneda': self.usd.pk, 'monto': '100',
        })
        self.assertEqual(respuesta.context['resultado']['tasa'], Decimal('7400.00'))
        self.assertEqual(respuesta.context['resultado']['total'], Decimal('740000.00'))

    def test_vender_divisa_usa_el_precio_de_compra(self):
        """Si el cliente vende, la casa compra: se aplica precio_compra."""
        respuesta = self.client.post(reverse('simulador'), {
            'operacion': 'venta', 'moneda': self.usd.pk, 'monto': '100',
        })
        self.assertEqual(respuesta.context['resultado']['tasa'], Decimal('7300.00'))
        self.assertEqual(respuesta.context['resultado']['total'], Decimal('730000.00'))

    def test_vender_siempre_da_menos_que_comprar(self):
        """Consecuencia de RN10: la casa gana la diferencia entre las puntas."""
        compra = self.client.post(reverse('simulador'), {
            'operacion': 'compra', 'moneda': self.usd.pk, 'monto': '100',
        }).context['resultado']['total']
        venta = self.client.post(reverse('simulador'), {
            'operacion': 'venta', 'moneda': self.usd.pk, 'monto': '100',
        }).context['resultado']['total']

        self.assertLess(venta, compra)

    def test_rechaza_monto_no_numerico(self):
        respuesta = self.client.post(reverse('simulador'), {
            'operacion': 'compra', 'moneda': self.usd.pk, 'monto': 'abc',
        })
        self.assertIn('error', respuesta.context)
        self.assertNotIn('resultado', respuesta.context)

    def test_rechaza_monto_cero_o_negativo(self):
        respuesta = self.client.post(reverse('simulador'), {
            'operacion': 'compra', 'moneda': self.usd.pk, 'monto': '0',
        })
        self.assertIn('error', respuesta.context)

    def test_avisa_si_la_moneda_no_tiene_cotizacion_vigente(self):
        euro = Moneda.objects.create(codigo="EUR", nombre="Euro", simbolo="€")
        respuesta = self.client.post(reverse('simulador'), {
            'operacion': 'compra', 'moneda': euro.pk, 'monto': '100',
        })
        self.assertIn('error', respuesta.context)
        self.assertNotIn('resultado', respuesta.context)

    def test_el_simulador_no_guarda_nada(self):
        """Es una simulación: no debe crear ninguna operación ni cotización."""
        antes = Cotizacion.objects.count()
        self.client.post(reverse('simulador'), {
            'operacion': 'compra', 'moneda': self.usd.pk, 'monto': '100',
        })
        self.assertEqual(Cotizacion.objects.count(), antes)
