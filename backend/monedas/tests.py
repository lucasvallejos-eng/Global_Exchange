from django.test import TestCase
from django.urls import reverse
from django.db import IntegrityError
from .models import Moneda

class MonedaModelTest(TestCase):
    def test_crear_moneda_exitoso(self):
        """Verifica la creación básica de un registro de moneda."""
        moneda = Moneda.objects.create(codigo="USD", nombre="Dólar Estadounidense", simbolo="$")
        self.assertEqual(moneda.codigo, "USD")
        self.assertEqual(str(moneda), "USD - Dólar Estadounidense")

    def test_codigo_moneda_unico(self):
        """Verifica que no se permitan códigos de moneda duplicados."""
        Moneda.objects.create(codigo="USD", nombre="Dólar", simbolo="$")
        with self.assertRaises(IntegrityError):
            Moneda.objects.create(codigo="USD", nombre="Dólar Parallelo", simbolo="$")

class MonedaViewsTest(TestCase):
    def setUp(self):
        self.moneda = Moneda.objects.create(codigo="EUR", nombre="Euro", simbolo="€")

    def test_listar_monedas_sin_autenticar(self):
        """Verifica que usuarios no autorizados no puedan acceder a la lista."""
        response = self.client.get(reverse('listar_monedas'))
        self.assertNotEqual(response.status_code, 200)

class CambioCotizacionApiTest(TestCase):
    """Cambios de cotización desde la API de la maqueta (sin bloqueo temporal)."""

    def setUp(self):
        from django.contrib.auth.models import Group, User

        from cotizaciones.models import Cotizacion

        self.Cotizacion = Cotizacion
        analista = User.objects.create_user("analista", password="x")
        analista.groups.add(Group.objects.create(name="analista_cambiario"))
        self.client.force_login(analista)
        self.moneda = Moneda.objects.create(codigo="USD", nombre="Dólar", simbolo="$")
        Cotizacion.objects.create(
            moneda=self.moneda, precio_compra=7300, precio_venta=7400, activa=True
        )
        self.url = reverse("api_monedas_detalle", args=[self.moneda.pk])

    def _patch(self, compra, venta, **extra):
        import json

        datos = {"nombre": "Dólar", "activo": True, "precioCompra": compra, "precioVenta": venta, **extra}
        return self.client.patch(self.url, json.dumps(datos), content_type="application/json")

    def test_cambia_la_cotizacion(self):
        respuesta = self._patch(7300, 7450)
        self.assertEqual(respuesta.status_code, 200, respuesta.content)
        self.assertEqual(respuesta.json()["precioVenta"], 7450)

    def test_varios_cambios_seguidos(self):
        """Una moneda puede cambiar de cotización varias veces en la misma hora."""
        self._patch(7300, 7450)
        respuesta = self._patch(7300, 7400)
        self.assertEqual(respuesta.status_code, 200, respuesta.content)
        self.assertEqual(respuesta.json()["precioVenta"], 7400)

    def test_editar_sin_cambiar_precios_no_crea_cotizacion(self):
        self._patch(7300, 7450)
        respuesta = self._patch(7300, 7450, nombre="Dólar estadounidense")
        self.assertEqual(respuesta.status_code, 200, respuesta.content)
        self.assertEqual(self.Cotizacion.objects.filter(moneda=self.moneda).count(), 2)
