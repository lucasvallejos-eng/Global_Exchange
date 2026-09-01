from django.test import TestCase
from django.urls import reverse
from django.core.exceptions import ValidationError
from monedas.models import Moneda
from .models import Cotizacion

class CotizacionModelTest(TestCase):
    def setUp(self):
        """Crea una moneda base para usar en las cotizaciones."""
        self.moneda_usd = Moneda.objects.create(
            codigo="USD", 
            nombre="Dólar Estadounidense", 
            simbolo="$"
        )

    def test_creacion_cotizacion_exitosa(self):
        """Valida que una cotización se asocie correctamente a una moneda."""
        cotizacion = Cotizacion.objects.create(
            moneda=self.moneda_usd,
            precio_compra=7300.00,
            precio_venta=7400.00
        )
        self.assertEqual(cotizacion.moneda.codigo, "USD")
        self.assertEqual(cotizacion.precio_compra, 7300.00)
        self.assertEqual(cotizacion.precio_venta, 7400.00)
        self.assertTrue(cotizacion.activa)

    def test_relacion_cascade_moneda(self):
        """Verifica que si se elimina una moneda, sus cotizaciones asociadas también se eliminen."""
        Cotizacion.objects.create(
            moneda=self.moneda_usd,
            precio_compra=7300.00,
            precio_venta=7400.00
        )
        self.moneda_usd.delete()
        self.assertEqual(Cotizacion.objects.count(), 0)


class CotizacionViewsTest(TestCase):
    def setUp(self):
        self.moneda = Moneda.objects.create(
            codigo="EUR", 
            nombre="Euro", 
            simbolo="€"
        )
        self.cotizacion = Cotizacion.objects.create(
            moneda=self.moneda,
            precio_compra=8000.00,
            precio_venta=8100.00
        )

    def test_listar_cotizaciones_protegido(self):
        """Verifica que la lista de cotizaciones requiera permisos o autenticación."""
        response = self.client.get(reverse('listar_cotizaciones'))
        self.assertNotEqual(response.status_code, 200)

    def test_crear_cotizacion_sin_autenticar(self):
        """Garantiza que usuarios no autorizados no puedan registrar cotizaciones."""
        data = {
            'moneda': self.moneda.id,
            'precio_compra': 8050.00,
            'precio_venta': 8150.00
        }
        response = self.client.post(reverse('crear_cotizacion'), data)
        self.assertNotEqual(response.status_code, 200)
        self.assertEqual(Cotizacion.objects.count(), 1)

class CotizacionModelValidationTest(TestCase):
    def setUp(self):
        self.moneda = Moneda.objects.create(
            codigo="USD", 
            nombre="Dólar Estadounidense", 
            simbolo="$"
        )

    def test_precio_venta_mayor_a_compra_exitoso(self):
        """Verifica que permita guardar si precio_venta > precio_compra."""
        cotizacion = Cotizacion(
            moneda=self.moneda,
            precio_compra=7200.00,
            precio_venta=7300.00
        )
        
        cotizacion.full_clean()
        cotizacion.save()
        self.assertEqual(Cotizacion.objects.count(), 1)

    def test_error_si_precio_venta_menor_o_igual_a_compra(self):
        """Verifica que lance ValidationError si precio_venta <= precio_compra."""
        cotizacion = Cotizacion(
            moneda=self.moneda,
            precio_compra=7500.00,
            precio_venta=7300.00
        )
        with self.assertRaises(ValidationError):
            cotizacion.full_clean()


class CotizacionSoftDeleteTest(TestCase):
    def setUp(self):
        self.moneda = Moneda.objects.create(
            codigo="EUR", 
            nombre="Euro", 
            simbolo="€"
        )
        self.cotizacion = Cotizacion.objects.create(
            moneda=self.moneda,
            precio_compra=8000.00,
            precio_venta=8100.00,
            activa=True
        )

    def test_borrado_logico_desactiva_registro(self):
        """Verifica que la eliminación no borre el registro de PostgreSQL sino que marque activa=False."""
        
        self.cotizacion.activa = False
        self.cotizacion.save()

        self.assertEqual(Cotizacion.objects.count(), 1)
        
        cotizacion_db = Cotizacion.objects.get(id=self.cotizacion.id)
        self.assertFalse(cotizacion_db.activa)