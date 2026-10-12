"""Pruebas de las notificaciones (Stripe simulado, como en las demás apps)."""
import json
import time
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse

from caja import tests as caja_tests
from clientes.models import Cliente
from cotizaciones.models import Cotizacion, HistorialCotizacion
from medios_pago.models import MedioPago
from operaciones.models import Transaccion
from operaciones import tests as operaciones_tests
from pagos.servicio import Cobro, PagoRechazado

from . import servicio
from .models import Notificacion

Usuario = get_user_model()


def _cobro(estado="aprobado"):
    return Cobro("pi_1", estado, "pi_1_secret")


def _entrar(client, usuario):
    client.force_login(usuario)
    sesion = client.session
    sesion["oidc_id_token_expiration"] = time.time() + 3600
    sesion.save()


class FormatoTest(TestCase):
    def test_numeros_como_en_paraguay(self):
        self.assertEqual(servicio.formatear_numero(Decimal("74000")), "74.000")
        self.assertEqual(servicio.formatear_numero(Decimal("10.00")), "10")
        self.assertEqual(servicio.formatear_numero(Decimal("1250.50")), "1.250,5")


class OperacionesWebTest(operaciones_tests.BaseOperacionesTest):
    def setUp(self):
        super().setUp()
        self.tarjeta = MedioPago.objects.create(
            usuario=self.usuario, tipo="TARJETA_CREDITO", alias="Mi Visa",
            stripe_payment_method_id="pm_1", banco_o_proveedor="Visa", numero_cuenta_o_tarjeta="4242",
        )

    def _confirmar(self, tipo="COMPRA", medio=None):
        self.entrar(self.usuario)
        return self.client.post(reverse("api_operaciones_confirmar"), data=json.dumps({
            "clienteId": self.cliente.pk, "tipo": tipo, "moneda": "USD", "monto": "100",
            "medioPagoId": medio.pk if medio else None, "tasaBase": "7400" if tipo == "COMPRA" else "7300",
        }), content_type="application/json")

    def _unica(self):
        [n] = Notificacion.objects.filter(usuario=self.usuario)
        return n

    def test_compra_exitosa_con_medio_y_valor(self):
        with patch("pagos.servicio.cobrar", return_value=_cobro()):
            self._confirmar(medio=self.tarjeta)
        n = self._unica()
        self.assertEqual((n.tipo, n.titulo), (Notificacion.Tipo.OPERACION_EXITOSA, "Compra exitosa"))
        self.assertIn("Compraste 100 USD por 710.030 PYG", n.mensaje)
        self.assertIn("Mi Visa (Visa •••• 4242)", n.mensaje)

    def test_venta_exitosa_dice_lo_que_se_cobro(self):
        with patch("pagos.servicio.cobrar", return_value=_cobro()):
            self._confirmar("VENTA", self.tarjeta)
        n = self._unica()
        self.assertEqual(n.titulo, "Venta exitosa")
        self.assertIn("Se cobraron 100 USD a Mi Visa", n.mensaje)

    def test_tarjeta_rechazada_notifica_aunque_no_se_registre(self):
        with patch("pagos.servicio.cobrar", side_effect=PagoRechazado("La tarjeta fue rechazada: fondos insuficientes.")):
            respuesta = self._confirmar(medio=self.tarjeta)
        self.assertEqual(respuesta.status_code, 400)
        self.assertFalse(Transaccion.objects.exists())
        n = self._unica()
        self.assertEqual((n.tipo, n.titulo), (Notificacion.Tipo.OPERACION_FALLIDA, "Compra fallida"))
        self.assertIn("fondos insuficientes", n.mensaje)
        self.assertIsNone(n.datos["operacionId"])

    def test_cotizacion_cambiada_es_fallida_con_motivo(self):
        self.cotizacion.precio_venta = Decimal("7500")
        self.cotizacion.save()
        self._confirmar(medio=self.tarjeta)
        n = self._unica()
        self.assertEqual(n.tipo, Notificacion.Tipo.OPERACION_FALLIDA)
        self.assertIn("cotización de USD cambió", n.mensaje)

    def test_3d_secure_no_aprobado(self):
        with patch("pagos.servicio.cobrar", return_value=_cobro("requiere_accion")):
            datos = self._confirmar(medio=self.tarjeta).json()
        self.assertFalse(Notificacion.objects.exists())  # pendiente: todavía nada
        with patch("pagos.servicio.verificar_cobro", side_effect=PagoRechazado("El pago no se completó (la verificación del banco no se aprobó).")):
            self.client.post(reverse("api_operaciones_verificar_pago", args=[datos["id"]]))
        n = self._unica()
        self.assertEqual(n.tipo, Notificacion.Tipo.OPERACION_FALLIDA)
        self.assertIn("verificación del banco", n.mensaje)
        self.assertEqual(n.datos["operacionId"], datos["id"])

    def test_cancelada_por_el_usuario(self):
        from operaciones import servicios
        t = self.crear()
        servicios.cancelar(t, self.usuario)
        n = self._unica()
        self.assertEqual(n.titulo, "Compra fallida")
        self.assertIn("Cancelada por el usuario", n.mensaje)

    def test_errores_de_validacion_no_notifican(self):
        self.entrar(self.usuario)
        self.client.post(reverse("api_operaciones_confirmar"), data=json.dumps({
            "clienteId": self.cliente.pk, "tipo": "COMPRA", "moneda": "USD", "monto": "0", "tasaBase": "7400",
        }), content_type="application/json")
        self.assertFalse(Notificacion.objects.exists())


class OperacionesCajaTest(TestCase):
    _apertura = caja_tests.CajaApiTests._apertura

    def setUp(self):
        caja_tests.CajaApiTests.setUp(self)
        Cotizacion.objects.create(moneda=self.moneda, precio_compra=7300, precio_venta=7400)
        self.cliente = Cliente.objects.create(
            nombre="Clara Cliente", tipo=Cliente.Tipo.FISICA, direccion="x", cuenta_acreditar="1",
            correo="c@example.com",
        )
        self.titular = Usuario.objects.create_user("titular")
        self.cliente.usuarios.add(self.titular)
        self.tarjeta = MedioPago.objects.create(
            usuario=self.titular, alias="Mi Visa", stripe_payment_method_id="pm_1",
            banco_o_proveedor="Visa", numero_cuenta_o_tarjeta="4242",
        )
        self._apertura()

    def _operar(self, ruta, **extra):
        return self.client.post(reverse(ruta), data=json.dumps(
            {"cliente_id": self.cliente.id, "moneda": "USD", "monto_divisa": "2", **extra}),
            content_type="application/json")

    def test_venta_en_efectivo_solo_al_cajero(self):
        self._operar("api_caja_ventas", tipo_pago="EFECTIVO")
        [n] = Notificacion.objects.all()
        self.assertEqual((n.usuario, n.titulo), (self.usuario, "Venta en caja exitosa"))
        self.assertIn("Vendiste 2 USD a Clara Cliente por 14.800 PYG. Medio de pago: Efectivo", n.mensaje)

    def test_con_tarjeta_avisa_tambien_al_duenio(self):
        with patch("pagos.servicio.cobrar", return_value=_cobro()):
            self._operar("api_caja_compras", medio_pago_id=self.tarjeta.id)
        cajero = Notificacion.objects.get(usuario=self.usuario)
        duenio = Notificacion.objects.get(usuario=self.titular)
        self.assertEqual(cajero.titulo, "Compra en caja exitosa")
        self.assertEqual(duenio.titulo, "Cobro con tu tarjeta en caja")
        self.assertIn("Se cobraron 2 USD a Mi Visa (Visa •••• 4242)", duenio.mensaje)

    def test_rechazo_avisa_a_los_dos(self):
        with patch("pagos.servicio.cobrar", side_effect=PagoRechazado("La tarjeta fue rechazada.")):
            self._operar("api_caja_ventas", medio_pago_id=self.tarjeta.id)
        self.assertEqual(
            set(Notificacion.objects.values_list("usuario__username", "titulo")),
            {("cajero", "Venta en caja fallida"), ("titular", "Cobro rechazado en caja")},
        )


class CotizacionTest(TestCase):
    def setUp(self):
        from monedas.models import Moneda
        self.analista = Usuario.objects.create_user("analista")
        self.analista.groups.add(Group.objects.get_or_create(name="analista_cambiario")[0])
        self.otro = Usuario.objects.create_user("otro")
        self.inactivo = Usuario.objects.create_user("inactivo", is_active=False)
        self.usd = Moneda.objects.create(codigo="USD", nombre="Dólar", simbolo="$")
        self.cotizacion = Cotizacion.objects.create(moneda=self.usd, precio_compra=7300, precio_venta=7400)
        _entrar(self.client, self.analista)

    def _destinatarios(self):
        return set(Notificacion.objects.filter(tipo=Notificacion.Tipo.COTIZACION).values_list("usuario__username", flat=True))

    def test_desde_la_api_de_monedas(self):
        with self.captureOnCommitCallbacks(execute=True):
            self.client.patch(reverse("api_monedas_detalle", args=[self.usd.pk]),
                              data=json.dumps({"precioCompra": 7350, "precioVenta": 7450}),
                              content_type="application/json")
        self.assertEqual(self._destinatarios(), {"otro"})
        n = Notificacion.objects.get(usuario=self.otro)
        self.assertEqual(n.titulo, "Cambió la cotización de USD")
        self.assertIn("compra 7.300 → 7.350, venta 7.400 → 7.450", n.mensaje)

    def test_desde_la_pantalla_de_django(self):
        with self.captureOnCommitCallbacks(execute=True):
            self.client.post(reverse("editar_cotizacion", args=[self.cotizacion.pk]),
                             {"moneda": self.usd.pk, "precio_compra": "7300", "precio_venta": "7500"})
        self.assertEqual(HistorialCotizacion.objects.count(), 1)
        self.assertEqual(self._destinatarios(), {"otro"})
        self.assertIn("venta 7.400 → 7.500", Notificacion.objects.get().mensaje)

    def test_sin_cambio_de_precio_no_avisa(self):
        with self.captureOnCommitCallbacks(execute=True):
            self.client.post(reverse("editar_cotizacion", args=[self.cotizacion.pk]),
                             {"moneda": self.usd.pk, "precio_compra": "7300", "precio_venta": "7400"})
        self.assertFalse(Notificacion.objects.exists())


class ApiTest(TestCase):
    def setUp(self):
        self.ana = Usuario.objects.create_user("ana")
        self.beto = Usuario.objects.create_user("beto")
        servicio.notificar([self.ana], Notificacion.Tipo.COTIZACION, "A1", "m")
        servicio.notificar([self.ana], Notificacion.Tipo.COTIZACION, "A2", "m")
        servicio.notificar([self.beto], Notificacion.Tipo.COTIZACION, "B1", "m")
        _entrar(self.client, self.ana)

    def test_cada_uno_ve_las_suyas(self):
        datos = self.client.get(reverse("api_notificaciones")).json()
        self.assertEqual(datos["noLeidas"], 2)
        self.assertEqual([n["titulo"] for n in datos["notificaciones"]], ["A2", "A1"])

    def test_marcar_leidas(self):
        [a2, a1] = self.client.get(reverse("api_notificaciones")).json()["notificaciones"]
        respuesta = self.client.post(reverse("api_notificaciones_marcar_leidas"),
                                     data=json.dumps({"ids": [a1["id"]]}), content_type="application/json")
        self.assertEqual(respuesta.json()["noLeidas"], 1)
        self.client.post(reverse("api_notificaciones_marcar_leidas"), data="{}", content_type="application/json")
        self.assertEqual(self.client.get(reverse("api_notificaciones")).json()["noLeidas"], 0)
        self.assertFalse(Notificacion.objects.get(titulo="B1").leida)

    def test_sin_sesion_no_accede(self):
        self.client.logout()
        self.assertNotEqual(self.client.get(reverse("api_notificaciones")).status_code, 200)


class PreferenciasTest(TestCase):
    """Suscripciones: cada usuario elige qué notificaciones recibir."""

    def setUp(self):
        from monedas.models import Moneda
        from .models import PreferenciaNotificaciones
        self.Preferencia = PreferenciaNotificaciones
        self.usd = Moneda.objects.create(codigo="USD", nombre="Dólar", simbolo="$")
        self.eur = Moneda.objects.create(codigo="EUR", nombre="Euro", simbolo="€")
        Moneda.objects.create(codigo="PYG", nombre="Guaraní", simbolo="Gs", es_local=True)
        self.ana = Usuario.objects.create_user("ana")
        _entrar(self.client, self.ana)

    def _guardar(self, **datos):
        return self.client.put(reverse("api_notificaciones_preferencias"), data=json.dumps(datos),
                               content_type="application/json")

    def _avisar(self, categoria, moneda=None):
        servicio.notificar([self.ana], Notificacion.Tipo.COTIZACION, "t", "m", categoria=categoria, moneda=moneda)
        return Notificacion.objects.filter(usuario=self.ana).count()

    def test_sin_preferencias_recibe_todo(self):
        datos = self.client.get(reverse("api_notificaciones_preferencias")).json()
        self.assertEqual((datos["compras"], datos["ventas"], datos["cotizaciones"], datos["monedas"]), (True, True, True, []))
        self.assertEqual([m["codigo"] for m in datos["monedasDisponibles"]], ["EUR", "USD"])  # sin la local
        self.assertEqual(self._avisar("COMPRA"), 1)

    def test_solo_ventas(self):
        self._guardar(compras=False, ventas=True, cotizaciones=False)
        self.assertEqual(self._avisar("COMPRA"), 0)
        self.assertEqual(self._avisar("COTIZACION", "USD"), 0)
        self.assertEqual(self._avisar("VENTA"), 1)

    def test_solo_cotizaciones_de_algunas_divisas(self):
        respuesta = self._guardar(compras=False, ventas=False, monedas=["USD"])
        self.assertEqual(respuesta.json()["monedas"], ["USD"])
        self.assertEqual(self._avisar("COTIZACION", "EUR"), 0)
        self.assertEqual(self._avisar("COTIZACION", "USD"), 1)

    def test_divisa_inexistente(self):
        self.assertEqual(self._guardar(monedas=["XXX"]).status_code, 400)

    def test_los_campos_que_no_vienen_no_cambian(self):
        self._guardar(compras=False)
        datos = self._guardar(ventas=False).json()
        self.assertEqual((datos["compras"], datos["ventas"], datos["cotizaciones"]), (False, False, True))

    def test_caja_respeta_el_punto_de_vista_de_cada_uno(self):
        """La casa compra divisa con la tarjeta del cliente: para el cajero es
        una compra; para el dueño de la tarjeta, una venta."""
        from types import SimpleNamespace
        cajero = Usuario.objects.create_user("cajero_pref")
        self.Preferencia.objects.create(usuario=cajero, compras=False)          # no quiere compras
        self.Preferencia.objects.create(usuario=self.ana, ventas=False)         # no quiere ventas
        medio = SimpleNamespace(usuario=self.ana, usuario_id=self.ana.pk, alias="Visa",
                                stripe_payment_method_id="pm", banco_o_proveedor="Visa", numero_cuenta_o_tarjeta="4242")
        obj = SimpleNamespace(pk=1, moneda=self.usd, monto_divisa=Decimal("2"), monto_local_total=Decimal("14600"),
                              cliente=SimpleNamespace(nombre="Clara"))
        servicio.operacion_caja_exitosa(cajero, "compra", obj, "Visa", medio, "2 USD")
        self.assertFalse(Notificacion.objects.exists())
        servicio.operacion_caja_exitosa(cajero, "venta", obj, "Visa", medio, "14.600 PYG")
        self.assertEqual(set(Notificacion.objects.values_list("usuario__username", flat=True)), {"cajero_pref", "ana"})

    def test_cambio_de_cotizacion_respeta_las_divisas_elegidas(self):
        otro = Usuario.objects.create_user("sigue_eur")
        preferencia = self.Preferencia.objects.create(usuario=otro)
        preferencia.monedas.set([self.eur])
        HistorialCotizacion.objects.create(
            moneda=self.usd, administrador=Usuario.objects.create_user("autor"),
            precio_compra_anterior=1, precio_compra_nuevo=2,
            precio_venta_anterior=3, precio_venta_nuevo=4,
        )
        servicio.cotizacion_cambiada(HistorialCotizacion.objects.get())
        self.assertEqual(set(Notificacion.objects.values_list("usuario__username", flat=True)), {"ana"})
