import json
import time
from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from monedas.models import Denominacion, Moneda
from clientes.models import Cliente
from comisiones.models import SegmentoCliente
from cotizaciones.models import Cotizacion
from medios_pago.models import MedioPago, TipoMedioPago

from .models import AperturaCaja, CompraCaja, VentaCaja


class CajaApiTests(TestCase):
    def setUp(self):
        self.usuario = get_user_model().objects.create_user("cajero")
        self.usuario.groups.add(Group.objects.get_or_create(name="cajero")[0])
        self.client.force_login(self.usuario)
        session = self.client.session
        session["keycloak_claims"] = {"sub": "usuario-keycloak-1"}
        session["oidc_id_token_expiration"] = time.time() + 3600
        session.save()
        self.client.force_login(self.usuario)
        self.moneda = Moneda.objects.create(
            codigo="USD", nombre="Dólar", simbolo="$"
        )
        self.denominacion = Denominacion.objects.create(
            moneda=self.moneda, valor=100
        )

    def _apertura(self):
        return self.client.post(
            reverse("api_caja_apertura"),
            data=json.dumps({
                "denominaciones": [{
                    "denominacion_id": self.denominacion.id,
                    "cantidad_unidades": 2,
                }]
            }),
            content_type="application/json",
        )

    def test_estado_diario_informa_si_hay_apertura(self):
        respuesta = self.client.get(reverse("api_caja_estado_diario"))
        self.assertFalse(respuesta.json()["aperturada"])
        self.assertEqual(self._apertura().status_code, 201)
        self.assertTrue(self.client.get(reverse("api_caja_estado_diario")).json()["aperturada"])

    def test_apertura_unica_por_dia(self):
        self.assertEqual(self._apertura().status_code, 201)
        segunda = self._apertura()
        self.assertEqual(segunda.status_code, 400)
        self.assertEqual(AperturaCaja.objects.count(), 1)

    def test_apertura_de_otra_fecha_no_bloquea_hoy(self):
        apertura = AperturaCaja.objects.create(
            cajero_id="usuario-keycloak-1",
            totales_consolidado={"USD": 200},
        )
        AperturaCaja.objects.filter(pk=apertura.pk).update(
            fecha_hora_apertura=timezone.now() - timedelta(days=1)
        )
        self.assertEqual(self._apertura().status_code, 201)

    def test_compra_recalcula_y_persiste_tasa_preferencial(self):
        segmento = SegmentoCliente.objects.create(
            nombre="VIP Caja Test", porcentaje_comision="10", descuento_compra="0"
        )
        cliente = Cliente.objects.create(
            nombre="Cliente", tipo=Cliente.Tipo.FISICA, direccion="Calle",
            cuenta_acreditar="123", correo="cliente@example.com", segmento=segmento,
        )
        MedioPago.objects.create(usuario=self.usuario, alias="Efectivo")
        Cotizacion.objects.create(moneda=self.moneda, precio_compra=100, precio_venta=120)
        self._apertura()
        respuesta = self.client.post(
            reverse("api_caja_compras"),
            data=json.dumps({
                "cliente_id": cliente.id, "moneda": "USD", "monto_divisa": "2",
            }),
            content_type="application/json",
        )
        self.assertEqual(respuesta.status_code, 201)
        self.assertEqual(respuesta.json()["cotizacionFinal"], 110)
        self.assertEqual(CompraCaja.objects.get(pk=respuesta.json()["id"]).medio_pago.alias, "Efectivo")


class CajaPermisosTests(TestCase):
    """Los endpoints de caja solo los puede usar un cajero."""

    def _iniciar_sesion(self, rol):
        usuario = get_user_model().objects.create_user(f"usuario_{rol}")
        usuario.groups.add(Group.objects.get_or_create(name=rol)[0])
        self.client.force_login(usuario)
        session = self.client.session
        session["oidc_id_token_expiration"] = time.time() + 3600
        session.save()

    def test_roles_sin_permiso_reciben_403(self):
        rutas_get = ["api_caja_denominaciones", "api_caja_estado_diario", "api_caja_resumen_cierre"]
        rutas_post = ["api_caja_apertura", "api_caja_compras", "api_caja_ventas", "api_caja_cierre"]
        for rol in ("cliente", "analista_cambiario", "administrador"):
            self._iniciar_sesion(rol)
            for nombre in rutas_get:
                with self.subTest(rol=rol, ruta=nombre):
                    self.assertEqual(self.client.get(reverse(nombre)).status_code, 403)
            for nombre in rutas_post:
                with self.subTest(rol=rol, ruta=nombre):
                    respuesta = self.client.post(reverse(nombre), data="{}", content_type="application/json")
                    self.assertEqual(respuesta.status_code, 403)
        self.assertFalse(AperturaCaja.objects.exists())

    def test_cajero_accede(self):
        self._iniciar_sesion("cajero")
        self.assertEqual(self.client.get(reverse("api_caja_estado_diario")).status_code, 200)

    def test_403_de_la_api_es_json_con_codigo(self):
        self._iniciar_sesion("cliente")
        respuesta = self.client.get(reverse("api_caja_estado_diario"))
        self.assertEqual(respuesta.status_code, 403)
        self.assertEqual(respuesta.json()["codigo"], "acceso_denegado")
        self.assertEqual(respuesta.json()["detalle"], "Se necesita el rol: cajero.")


class CajaConTarjetaTest(TestCase):
    """Compra y venta de caja cobradas con una tarjeta de Stripe (simulado)."""

    # Mismo cajero, moneda y apertura que CajaApiTests, sin repetir sus tests.
    _apertura = CajaApiTests._apertura

    def setUp(self):
        CajaApiTests.setUp(self)
        self.segmento = SegmentoCliente.objects.create(
            nombre="Sin comision", porcentaje_comision="0", descuento_compra="0"
        )
        self.cliente = Cliente.objects.create(
            nombre="Cliente", tipo=Cliente.Tipo.FISICA, direccion="Calle",
            cuenta_acreditar="123", correo="cliente@example.com", segmento=self.segmento,
        )
        self.titular = get_user_model().objects.create_user("titular")
        self.cliente.usuarios.add(self.titular)
        self.tarjeta = MedioPago.objects.create(
            usuario=self.titular, tipo="TARJETA_CREDITO", alias="Visa",
            stripe_payment_method_id="pm_1", banco_o_proveedor="Visa", numero_cuenta_o_tarjeta="4242",
        )
        Cotizacion.objects.create(moneda=self.moneda, precio_compra=7300, precio_venta=7400)
        self._apertura()

    def _operar(self, ruta, **extra):
        return self.client.post(
            reverse(ruta),
            data=json.dumps({"cliente_id": self.cliente.id, "moneda": "USD", "monto_divisa": "2",
                             "medio_pago_id": self.tarjeta.id, **extra}),
            content_type="application/json",
        )

    def _cobro(self, estado="aprobado"):
        from pagos.servicio import Cobro
        return Cobro("pi_1", estado, "pi_1_secret")

    def test_venta_de_caja_cobra_guaranies(self):
        with patch("pagos.servicio.cobrar", return_value=self._cobro()) as cobrar:
            respuesta = self._operar("api_caja_ventas")
        self.assertEqual(respuesta.status_code, 201)
        self.assertTrue(respuesta.json()["pagoConTarjeta"])
        _, monto, moneda = cobrar.call_args.args
        self.assertEqual((monto, moneda), (Decimal("14800"), "PYG"))
        self.assertEqual(VentaCaja.objects.get().stripe_payment_intent_id, "pi_1")

    def test_compra_de_caja_cobra_la_divisa_y_no_cuenta_para_el_arqueo(self):
        with patch("pagos.servicio.cobrar", return_value=self._cobro()) as cobrar:
            respuesta = self._operar("api_caja_compras")
        self.assertEqual(respuesta.status_code, 201)
        _, monto, moneda = cobrar.call_args.args
        self.assertEqual((monto, moneda), (Decimal("2"), "USD"))
        resumen = self.client.get(reverse("api_caja_resumen_cierre")).json()["resumen"]
        self.assertEqual(resumen[0]["compras"], 0)

    def test_tarjeta_rechazada_no_registra(self):
        from pagos.servicio import PagoRechazado
        with patch("pagos.servicio.cobrar", side_effect=PagoRechazado("La tarjeta fue rechazada")):
            respuesta = self._operar("api_caja_ventas")
        self.assertEqual(respuesta.status_code, 400)
        self.assertFalse(VentaCaja.objects.exists())

    def test_3d_secure_y_reintento_con_el_pago(self):
        with patch("pagos.servicio.cobrar", return_value=self._cobro("requiere_accion")):
            respuesta = self._operar("api_caja_ventas")
        self.assertEqual(respuesta.status_code, 202)
        self.assertEqual(respuesta.json()["pagoPendiente"]["paymentIntentId"], "pi_1")
        self.assertFalse(VentaCaja.objects.exists())

        with patch("pagos.servicio.verificar_cobro", return_value=self._cobro()):
            respuesta = self._operar("api_caja_ventas", payment_intent_id="pi_1")
        self.assertEqual(respuesta.status_code, 201)
        # El mismo pago no puede registrar una segunda operación.
        with patch("pagos.servicio.verificar_cobro", return_value=self._cobro()):
            respuesta = self._operar("api_caja_ventas", payment_intent_id="pi_1")
        self.assertEqual(respuesta.status_code, 400)

    def test_tarjeta_de_otro_cliente_se_rechaza(self):
        self.cliente.usuarios.clear()
        with patch("pagos.servicio.cobrar") as cobrar:
            respuesta = self._operar("api_caja_ventas")
        self.assertEqual(respuesta.status_code, 400)
        cobrar.assert_not_called()

    def test_lista_tarjetas_del_cliente(self):
        MedioPago.objects.create(usuario=self.titular, alias="Transferencia")
        respuesta = self.client.get(reverse("api_caja_tarjetas_cliente", args=[self.cliente.id]))
        self.assertEqual([t["id"] for t in respuesta.json()], [self.tarjeta.id])


class ArqueoConMonedaLocalTest(TestCase):
    """El arqueo sigue también los guaraníes del cajón."""

    _apertura = CajaApiTests._apertura

    def setUp(self):
        CajaApiTests.setUp(self)
        self.guarani = Moneda.objects.create(codigo="PYG", nombre="Guaraní", simbolo="Gs", es_local=True)
        billete = Denominacion.objects.create(moneda=self.guarani, valor=100000)
        Cotizacion.objects.create(moneda=self.moneda, precio_compra=7300, precio_venta=7400)
        self.cliente = Cliente.objects.create(
            nombre="Cliente", tipo=Cliente.Tipo.FISICA, direccion="Calle",
            cuenta_acreditar="123", correo="cliente@example.com",
        )
        # Apertura: 2 billetes de 100 USD y 10 de 100.000 Gs.
        self.client.post(
            reverse("api_caja_apertura"),
            data=json.dumps({"denominaciones": [
                {"denominacion_id": self.denominacion.id, "cantidad_unidades": 2},
                {"denominacion_id": billete.id, "cantidad_unidades": 10},
            ]}),
            content_type="application/json",
        )

    def _operar(self, ruta, monto, **extra):
        respuesta = self.client.post(
            reverse(ruta),
            data=json.dumps({"cliente_id": self.cliente.id, "moneda": "USD", "monto_divisa": monto, **extra}),
            content_type="application/json",
        )
        self.assertEqual(respuesta.status_code, 201, respuesta.content)

    def _resumen(self):
        filas = self.client.get(reverse("api_caja_resumen_cierre")).json()["resumen"]
        return {fila["moneda"]: fila for fila in filas}

    def test_venta_en_efectivo_entra_guaranies(self):
        self._operar("api_caja_ventas", "10", tipo_pago="EFECTIVO")  # 10 x 7400
        resumen = self._resumen()
        self.assertEqual(resumen["PYG"]["saldoTeorico"], 1_000_000 + 74_000)
        self.assertEqual(resumen["USD"]["saldoTeorico"], 200 - 10)

    def test_venta_por_transferencia_no_entra_al_cajon(self):
        TipoMedioPago.objects.get_or_create(clave="TRANSFERENCIA", defaults={"nombre": "Transferencia"})
        self._operar("api_caja_ventas", "10", tipo_pago="TRANSFERENCIA")
        self.assertEqual(self._resumen()["PYG"]["saldoTeorico"], 1_000_000)

    def test_compra_saca_guaranies(self):
        self._operar("api_caja_compras", "10")  # la casa paga 10 x 7300
        resumen = self._resumen()
        self.assertEqual(resumen["PYG"]["saldoTeorico"], 1_000_000 - 73_000)
        self.assertEqual(resumen["USD"]["saldoTeorico"], 200 + 10)
        self.assertEqual(resumen["PYG"]["cantidadVentas"], 1)

    def test_el_cierre_usa_el_mismo_calculo(self):
        self._operar("api_caja_ventas", "10", tipo_pago="EFECTIVO")
        respuesta = self.client.post(
            reverse("api_caja_cierre"),
            data=json.dumps({"totales_reales": {"USD": 190, "PYG": 1_074_000}}),
            content_type="application/json",
        )
        self.assertEqual(respuesta.json()["diferencia"], {"USD": 0, "PYG": 0})

    def test_la_moneda_local_no_se_opera(self):
        respuesta = self.client.post(
            reverse("api_caja_ventas"),
            data=json.dumps({"cliente_id": self.cliente.id, "moneda": "PYG", "monto_divisa": "1000", "tipo_pago": "EFECTIVO"}),
            content_type="application/json",
        )
        self.assertEqual(respuesta.status_code, 400)
        self.assertIn("moneda local", respuesta.json()["error"])


class HistorialCajaTest(TestCase):
    _apertura = CajaApiTests._apertura

    def setUp(self):
        CajaApiTests.setUp(self)
        Cotizacion.objects.create(moneda=self.moneda, precio_compra=7300, precio_venta=7400)
        self.cliente = Cliente.objects.create(
            nombre="Cliente", tipo=Cliente.Tipo.FISICA, direccion="Calle",
            cuenta_acreditar="123", correo="cliente@example.com",
        )
        self._apertura()
        self.client.post(reverse("api_caja_compras"), data=json.dumps(
            {"cliente_id": self.cliente.id, "moneda": "USD", "monto_divisa": "3"}), content_type="application/json")
        self.client.post(reverse("api_caja_ventas"), data=json.dumps(
            {"cliente_id": self.cliente.id, "moneda": "USD", "monto_divisa": "1", "tipo_pago": "EFECTIVO"}),
            content_type="application/json")
        # La caja de otro cajero.
        otra = AperturaCaja.objects.create(cajero_id="otro-cajero", totales_consolidado={"USD": 50})
        self.otra_id = otra.id

    def test_el_cajero_ve_sus_cajas_con_sus_operaciones(self):
        [caja] = self.client.get(reverse("api_caja_historial")).json()["aperturas"]
        self.assertEqual(caja["cajero"], "cajero")
        self.assertEqual(caja["estado"], "activa")
        self.assertEqual([(o["tipo"], o["montoDivisa"]) for o in caja["operaciones"]], [("VENTA", 1.0), ("COMPRA", 3.0)])
        self.assertEqual(caja["operaciones"][0]["formaPago"], "EFECTIVO")

    def test_el_administrador_ve_todas(self):
        admin = get_user_model().objects.create_user("admin_caja")
        admin.groups.add(Group.objects.get_or_create(name="administrador")[0])
        self.client.force_login(admin)
        session = self.client.session
        session["oidc_id_token_expiration"] = time.time() + 3600
        session.save()
        ids = [c["id"] for c in self.client.get(reverse("api_caja_historial")).json()["aperturas"]]
        self.assertIn(self.otra_id, ids)
        self.assertEqual(len(ids), 2)

    def test_el_cliente_no_accede(self):
        cliente = get_user_model().objects.create_user("cliente_caja")
        cliente.groups.add(Group.objects.get_or_create(name="cliente")[0])
        self.client.force_login(cliente)
        session = self.client.session
        session["oidc_id_token_expiration"] = time.time() + 3600
        session.save()
        self.assertEqual(self.client.get(reverse("api_caja_historial")).status_code, 403)

    def test_resumen_informa_compras_con_tarjeta_y_valor_en_guaranies(self):
        from pagos.servicio import Cobro
        titular = get_user_model().objects.create_user("titular_h")
        self.cliente.usuarios.add(titular)
        tarjeta = MedioPago.objects.create(usuario=titular, alias="Visa", stripe_payment_method_id="pm_1",
                                           banco_o_proveedor="Visa", numero_cuenta_o_tarjeta="4242")
        with patch("pagos.servicio.cobrar", return_value=Cobro("pi_h", "aprobado", "s")):
            self.client.post(reverse("api_caja_compras"), data=json.dumps(
                {"cliente_id": self.cliente.id, "moneda": "USD", "monto_divisa": "4", "medio_pago_id": tarjeta.id}),
                content_type="application/json")
        datos = self.client.get(reverse("api_caja_resumen_cierre")).json()
        [usd] = datos["resumen"]
        self.assertEqual(usd["comprasConTarjeta"], {"cantidad": 1, "monto": 4.0})
        # 200 iniciales + 3 comprados en efectivo - 1 vendido = 202 USD, a 7300.
        self.assertEqual(usd["saldoTeorico"], 202)
        self.assertEqual(usd["valorEnLocal"], 202 * 7300)
        self.assertEqual(datos["totalEnLocal"], 202 * 7300)
