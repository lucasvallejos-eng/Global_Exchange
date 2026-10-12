from django.test import TestCase
from django.urls import reverse
from django.db import IntegrityError
from .models import Moneda, Denominacion

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
        import time
        from django.contrib.auth.models import Group, User

        from cotizaciones.models import Cotizacion

        self.Cotizacion = Cotizacion
        grupo_analista, _ = Group.objects.get_or_create(name="analista_cambiario")
        analista = User.objects.create_user("analista", password="x")
        analista.groups.add(grupo_analista)
        self.client.force_login(analista)
        session = self.client.session
        session["oidc_id_token_expiration"] = time.time() + 3600
        session.save()

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


class DenominacionModelTest(TestCase):
    def setUp(self):
        self.moneda = Moneda.objects.create(codigo="USD", nombre="Dólar Estadounidense", simbolo="$")

    def test_crear_denominacion_exitosa(self):
        """Verifica la creación básica de una denominación asociada a una moneda."""
        denominacion = Denominacion.objects.create(moneda=self.moneda, valor=100)
        self.assertEqual(denominacion.moneda, self.moneda)
        self.assertEqual(denominacion.valor, 100)
        self.assertEqual(str(denominacion), "USD 100")
        self.assertIn(denominacion, self.moneda.denominaciones.all())

    def test_denominacion_unica_por_moneda_y_valor(self):
        """No permite duplicar el mismo valor para una misma divisa."""
        Denominacion.objects.create(moneda=self.moneda, valor=50)
        with self.assertRaises(IntegrityError):
            Denominacion.objects.create(moneda=self.moneda, valor=50)

    def test_borrado_en_cascada_al_eliminar_moneda(self):
        """Al borrar una moneda, sus denominaciones se eliminan en cascada (ON DELETE CASCADE)."""
        Denominacion.objects.create(moneda=self.moneda, valor=10)
        Denominacion.objects.create(moneda=self.moneda, valor=20)
        self.assertEqual(Denominacion.objects.filter(moneda=self.moneda).count(), 2)

        self.moneda.delete()
        self.assertEqual(Denominacion.objects.count(), 0)


class DenominacionApiTest(TestCase):
    def setUp(self):
        import json
        import time
        from django.contrib.auth.models import Group, User
        self.json = json

        grupo_admin, _ = Group.objects.get_or_create(name="administrador")
        admin = User.objects.create_user("admin_user", password="secret_password")
        admin.groups.add(grupo_admin)
        self.client.force_login(admin)
        session = self.client.session
        session["oidc_id_token_expiration"] = time.time() + 3600
        session.save()

        self.usd = Moneda.objects.create(codigo="USD", nombre="Dólar", simbolo="$")
        self.eur = Moneda.objects.create(codigo="EUR", nombre="Euro", simbolo="€")
        self.d1 = Denominacion.objects.create(moneda=self.usd, valor=100)
        self.d2 = Denominacion.objects.create(moneda=self.usd, valor=50)
        self.d3 = Denominacion.objects.create(moneda=self.eur, valor=20)

        self.list_url = reverse("api_denominaciones_lista")


    def test_listar_todas_las_denominaciones(self):
        res = self.client.get(self.list_url)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(len(data), 3)

    def test_filtrar_por_moneda(self):
        res = self.client.get(f"{self.list_url}?moneda_id={self.usd.id}")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(len(data), 2)
        self.assertTrue(all(item["monedaCodigo"] == "USD" for item in data))

    def test_crear_denominacion(self):
        payload = {"moneda_id": self.usd.id, "valor": 20}
        res = self.client.post(self.list_url, self.json.dumps(payload), content_type="application/json")
        self.assertEqual(res.status_code, 201)
        data = res.json()
        self.assertEqual(data["valor"], 20.0)
        self.assertEqual(data["monedaCodigo"], "USD")
        self.assertTrue(Denominacion.objects.filter(moneda=self.usd, valor=20).exists())

    def test_crear_denominacion_duplicada_falla(self):
        payload = {"moneda_id": self.usd.id, "valor": 100}
        res = self.client.post(self.list_url, self.json.dumps(payload), content_type="application/json")
        self.assertEqual(res.status_code, 400)
        self.assertIn("error", res.json())

    def test_crear_denominacion_valor_invalido_falla(self):
        payload = {"moneda_id": self.usd.id, "valor": -5}
        res = self.client.post(self.list_url, self.json.dumps(payload), content_type="application/json")
        self.assertEqual(res.status_code, 400)

        payload_cero = {"moneda_id": self.usd.id, "valor": 0}
        res_cero = self.client.post(self.list_url, self.json.dumps(payload_cero), content_type="application/json")
        self.assertEqual(res_cero.status_code, 400)

    def test_crear_denominacion_moneda_inexistente_falla(self):
        payload = {"moneda_id": 99999, "valor": 10}
        res = self.client.post(self.list_url, self.json.dumps(payload), content_type="application/json")
        self.assertEqual(res.status_code, 404)

    def test_detalle_denominacion(self):
        url = reverse("api_denominaciones_detalle", args=[self.d1.id])
        res = self.client.get(url)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["id"], self.d1.id)
        self.assertEqual(data["valor"], 100.0)

    def test_actualizar_denominacion(self):
        url = reverse("api_denominaciones_detalle", args=[self.d1.id])
        payload = {"valor": 200}
        res = self.client.put(url, self.json.dumps(payload), content_type="application/json")
        self.assertEqual(res.status_code, 200)
        self.d1.refresh_from_db()
        self.assertEqual(self.d1.valor, 200)

    def test_eliminar_denominacion(self):
        url = reverse("api_denominaciones_detalle", args=[self.d1.id])
        res = self.client.delete(url)
        self.assertEqual(res.status_code, 204)
        self.assertFalse(Denominacion.objects.filter(id=self.d1.id).exists())



class MonedaLocalTest(TestCase):
    """La moneda local (guaraní): sin cotización y una sola."""

    def setUp(self):
        import time
        from django.contrib.auth.models import Group, User

        analista = User.objects.create_user("analista_local")
        analista.groups.add(Group.objects.get_or_create(name="analista_cambiario")[0])
        self.client.force_login(analista)
        session = self.client.session
        session["oidc_id_token_expiration"] = time.time() + 3600
        session.save()

    def _crear(self, **datos):
        import json
        return self.client.post(reverse("api_monedas_lista"), data=json.dumps(datos), content_type="application/json")

    def test_se_crea_sin_precios(self):
        respuesta = self._crear(codigo="PYG", nombre="Guaraní", esLocal=True)
        self.assertEqual(respuesta.status_code, 201)
        self.assertTrue(respuesta.json()["esLocal"])
        self.assertIsNone(respuesta.json()["precioCompra"])
        self.assertEqual(Moneda.local().codigo, "PYG")

    def test_ignora_precios_y_no_crea_cotizacion(self):
        respuesta = self._crear(codigo="PYG", nombre="Guaraní", esLocal=True, precioCompra=1, precioVenta=1)
        self.assertEqual(respuesta.status_code, 201)
        self.assertFalse(Moneda.objects.get(codigo="PYG").cotizaciones.exists())

    def test_solo_una_moneda_local(self):
        self._crear(codigo="PYG", nombre="Guaraní", esLocal=True)
        respuesta = self._crear(codigo="ARS", nombre="Peso", esLocal=True)
        self.assertEqual(respuesta.status_code, 400)
        self.assertIn("solo puede haber una", respuesta.json()["error"])
        with self.assertRaises(IntegrityError):
            Moneda.objects.create(codigo="UYU", nombre="Peso uruguayo", simbolo="$", es_local=True)

    def test_la_moneda_local_no_admite_cotizacion(self):
        from django.core.exceptions import ValidationError

        from cotizaciones.models import Cotizacion

        guarani = Moneda.objects.create(codigo="PYG", nombre="Guaraní", simbolo="Gs", es_local=True)
        with self.assertRaisesMessage(ValidationError, "moneda local"):
            Cotizacion(moneda=guarani, precio_compra=1, precio_venta=2).clean()

    def test_pasar_a_local_desactiva_la_cotizacion(self):
        import json

        from cotizaciones.models import Cotizacion

        moneda = Moneda.objects.create(codigo="PYG", nombre="Guaraní", simbolo="Gs")
        Cotizacion.objects.create(moneda=moneda, precio_compra=1, precio_venta=2, activa=True)
        respuesta = self.client.patch(reverse("api_monedas_detalle", args=[moneda.pk]),
                                      data=json.dumps({"esLocal": True}), content_type="application/json")
        self.assertEqual(respuesta.status_code, 200)
        self.assertFalse(moneda.cotizaciones.filter(activa=True).exists())
        self.assertIsNone(respuesta.json()["precioVenta"])


class BorrarMonedaApiTest(TestCase):
    """Eliminar monedas desde la maqueta."""

    # Mismo analista logueado que MonedaLocalTest, sin repetir sus tests.
    setUp = MonedaLocalTest.setUp

    def test_moneda_sin_operaciones_se_elimina(self):
        moneda = Moneda.objects.create(codigo="GS", nombre="Guarani", simbolo="Gs")
        respuesta = self.client.delete(reverse("api_monedas_detalle", args=[moneda.pk]))
        self.assertEqual(respuesta.status_code, 204)
        self.assertFalse(Moneda.objects.filter(pk=moneda.pk).exists())

    def test_moneda_con_operaciones_no_se_elimina(self):
        from caja.models import AperturaCaja, CompraCaja
        from clientes.models import Cliente

        moneda = Moneda.objects.create(codigo="USD", nombre="Dólar", simbolo="$")
        CompraCaja.objects.create(
            apertura=AperturaCaja.objects.create(cajero_id="c1"), cajero_id="c1",
            cliente=Cliente.objects.create(nombre="C", tipo=Cliente.Tipo.FISICA, direccion="x",
                                           cuenta_acreditar="1", correo="c@example.com"),
            moneda=moneda, monto_divisa=1, cotizacion_aplicada=1, monto_local_total=1,
        )
        respuesta = self.client.delete(reverse("api_monedas_detalle", args=[moneda.pk]))
        self.assertEqual(respuesta.status_code, 400)
        self.assertIn("desactivarla", respuesta.json()["error"])
        self.assertTrue(Moneda.objects.filter(pk=moneda.pk).exists())

    def test_el_204_no_lleva_cuerpo(self):
        """Un 204 con cuerpo rompe la respuesta siguiente de la misma conexión
        (keep-alive): la maqueta no podía recargar la lista después de borrar."""
        moneda = Moneda.objects.create(codigo="ZZZ", nombre="Prueba", simbolo="z")
        respuesta = self.client.delete(reverse("api_monedas_detalle", args=[moneda.pk]))
        self.assertEqual(respuesta.status_code, 204)
        self.assertEqual(respuesta.content, b"")
