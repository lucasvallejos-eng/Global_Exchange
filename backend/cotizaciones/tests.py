import time

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse
from django.core.exceptions import ValidationError
from monedas.models import Moneda
from .models import Cotizacion

User = get_user_model()

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


class CotizacionVistaRN10Test(TestCase):
    """RN10 desde la vista, que es por donde entran los datos de verdad.

    Los tests de CotizacionModelValidationTest ya comprobaban que
    Cotizacion.clean() rechaza compra >= venta, pero probaban el modelo
    llamando a full_clean() a mano. La vista usaba Cotizacion.objects.create(),
    que NO ejecuta clean(), así que la regla se podía violar por la pantalla
    aunque el modelo estuviera bien. Estos tests cubren justamente ese hueco.
    """

    def setUp(self):
        self.moneda = Moneda.objects.create(
            codigo="USD",
            nombre="Dólar Estadounidense",
            simbolo="$"
        )
        grupo_admin, _ = Group.objects.get_or_create(name="administrador")
        self.admin = User.objects.create_user(username="admin_cotiz")
        self.admin.groups.add(grupo_admin)

        # Igual que en tests/test_flujo_basico.py: el login real pasa por
        # Keycloak, acá se simula con force_login más un token "vigente".
        self.client.force_login(self.admin)
        session = self.client.session
        session["oidc_id_token_expiration"] = time.time() + 3600
        session.save()

    def test_crear_rechaza_compra_mayor_que_venta(self):
        """La vista de alta no debe guardar una cotización que viola RN10."""
        respuesta = self.client.post(reverse('crear_cotizacion'), {
            'moneda': self.moneda.id,
            'precio_compra': 9000.00,
            'precio_venta': 5000.00,
        })

        # No se creó nada y se vuelve a mostrar el formulario (no redirige).
        self.assertEqual(Cotizacion.objects.count(), 0)
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "mayor al precio de compra")

    def test_crear_rechaza_compra_igual_a_venta(self):
        """RN10 pide compra estrictamente menor que venta, no menor o igual."""
        self.client.post(reverse('crear_cotizacion'), {
            'moneda': self.moneda.id,
            'precio_compra': 7000.00,
            'precio_venta': 7000.00,
        })
        self.assertEqual(Cotizacion.objects.count(), 0)

    def test_crear_acepta_cotizacion_valida(self):
        """El camino feliz sigue funcionando después de agregar la validación."""
        respuesta = self.client.post(reverse('crear_cotizacion'), {
            'moneda': self.moneda.id,
            'precio_compra': 7300.00,
            'precio_venta': 7400.00,
        })

        self.assertRedirects(respuesta, reverse('listar_cotizaciones'))
        self.assertEqual(Cotizacion.objects.count(), 1)

    def test_editar_rechaza_cotizacion_que_viola_rn10(self):
        """Editar tampoco puede dejar una cotización inválida guardada."""
        cotizacion = Cotizacion.objects.create(
            moneda=self.moneda,
            precio_compra=7300.00,
            precio_venta=7400.00,
        )

        self.client.post(reverse('editar_cotizacion', args=[cotizacion.pk]), {
            'moneda': self.moneda.id,
            'precio_compra': 9000.00,
            'precio_venta': 5000.00,
        })

        # Los valores en la base de datos quedaron como estaban.
        cotizacion.refresh_from_db()
        self.assertEqual(cotizacion.precio_compra, 7300.00)
        self.assertEqual(cotizacion.precio_venta, 7400.00)


class CotizacionPermisosAnalistaTest(TestCase):
    """El analista_cambiario gestiona las tasas, como dice la ERS.

    La ERS le asigna "modificar tasas y ver ganancias", así que sobre
    cotizaciones tiene los mismos permisos que el administrador. Lo que sigue
    fuera de su alcance es la administración (monedas, clientes, comisiones).
    """

    def setUp(self):
        self.moneda = Moneda.objects.create(codigo="USD", nombre="Dólar", simbolo="$")
        self.cotizacion = Cotizacion.objects.create(
            moneda=self.moneda, precio_compra=7300, precio_venta=7400
        )
        grupo, _ = Group.objects.get_or_create(name="analista_cambiario")
        self.analista = User.objects.create_user(username="un_analista")
        self.analista.groups.add(grupo)

        self.client.force_login(self.analista)
        session = self.client.session
        session["oidc_id_token_expiration"] = time.time() + 3600
        session.save()

    def test_puede_listar_cotizaciones(self):
        self.assertEqual(self.client.get(reverse('listar_cotizaciones')).status_code, 200)

    def test_puede_crear_cotizaciones(self):
        self.client.post(reverse('crear_cotizacion'), {
            'moneda': self.moneda.id, 'precio_compra': 7350, 'precio_venta': 7450,
        })
        self.assertEqual(Cotizacion.objects.count(), 2)

    def test_puede_editar_cotizaciones(self):
        self.client.post(reverse('editar_cotizacion', args=[self.cotizacion.pk]), {
            'moneda': self.moneda.id, 'precio_compra': 7350, 'precio_venta': 7450,
        })
        self.cotizacion.refresh_from_db()
        self.assertEqual(self.cotizacion.precio_venta, 7450)

    def test_puede_anular_cotizaciones(self):
        self.client.post(reverse('eliminar_cotizacion', args=[self.cotizacion.pk]))
        self.cotizacion.refresh_from_db()
        self.assertFalse(self.cotizacion.activa)

    def test_no_puede_administrar_monedas(self):
        """"Sin administración": las monedas siguen siendo del administrador."""
        self.assertEqual(self.client.get(reverse('listar_monedas')).status_code, 403)

    def test_no_puede_configurar_comisiones(self):
        self.assertEqual(self.client.get(reverse('listar_segmentos')).status_code, 403)


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