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