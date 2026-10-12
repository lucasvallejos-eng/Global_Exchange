"""Simulación completa de transacciones, de punta a punta.

Cada prueba recorre una transacción entera **por la API**, como lo hace la
maqueta, y con cada rol haciendo su parte:

1. el administrador da de alta al cliente (con su RUC) y le asocia un usuario;
2. el usuario cotiza y confirma la operación (o el cajero la registra en la
   ventanilla);
3. la operación queda pagada, o cancelada si la cotización cambió;
4. llega la notificación;
5. se genera la factura a nombre del cliente, que la ve y la descarga;
6. el analista la encuentra en el reporte de ganancias.

Es lo que pide el alcance del Sprint 5 ("simulación completa de
transacciones"): que todas las piezas de los sprints anteriores funcionen
juntas. Nada sale a la red: Stripe no interviene (se paga sin tarjeta) y
Factura Segura se reemplaza por un doble.
"""
import json
import time
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase, override_settings
from django.urls import reverse

from caja.models import CompraCaja, VentaCaja
from comisiones.models import SegmentoCliente
from cotizaciones.models import Cotizacion
from facturacion.models import Factura
from facturacion.servicio import SinConfirmar
from facturacion.tests import CDC, CONFIGURADO, respuesta_de_factura_segura
from monedas.models import Denominacion, Moneda
from notificaciones.models import Notificacion
from operaciones.models import Transaccion

Usuario = get_user_model()


class BaseTransaccionCompleta(TestCase):
    """Un usuario de cada rol, USD a 7300 / 7400 y un segmento con 1 % de comisión."""

    def setUp(self):
        self.admin = self.usuario_con_rol("ana", "administrador")
        self.analista = self.usuario_con_rol("andres", "analista_cambiario")
        self.cajero = self.usuario_con_rol("carlos", "cajero")
        self.clara = self.usuario_con_rol("clara", "cliente")
        self.intruso = self.usuario_con_rol("ivan", "cliente")

        self.usd = Moneda.objects.create(codigo="USD", nombre="Dólar", simbolo="$")
        self.cotizacion = Cotizacion.objects.create(
            moneda=self.usd, precio_compra=Decimal("7300"), precio_venta=Decimal("7400")
        )
        self.segmento = SegmentoCliente.objects.create(
            nombre="Corporativo", porcentaje_comision=Decimal("1.00"), descuento_compra=Decimal("0")
        )
        self.cliente_id = self.alta_de_cliente()

    def usuario_con_rol(self, nombre, rol):
        usuario = Usuario.objects.create_user(username=nombre, email=f"{nombre}@example.com")
        usuario.groups.add(Group.objects.get_or_create(name=rol)[0])
        return usuario

    def entrar(self, usuario):
        """Inicia sesión como lo dejaría Keycloak (ver tests/README.md)."""
        self.client.force_login(usuario)
        sesion = self.client.session
        sesion["oidc_id_token_expiration"] = time.time() + 3600
        sesion.save()

    def post(self, ruta, cuerpo=None, **kwargs):
        """Un POST a la API. Los ``on_commit`` (la factura) corren como en producción."""
        with self.captureOnCommitCallbacks(execute=True):
            return self.client.post(
                reverse(ruta, **kwargs), data=json.dumps(cuerpo or {}), content_type="application/json"
            )

    def alta_de_cliente(self):
        """El administrador crea el cliente con su RUC y le asocia a Clara."""
        self.entrar(self.admin)
        respuesta = self.post("clientes_lista", {
            "nombre": "Comercial Clara S.A.", "tipo": "Jurídica", "direccion": "Asunción",
            "cuentaAcreditar": "001-1", "correo": "facturas@clara.com.py", "ruc": "80002247-5",
            "segmento": self.segmento.pk, "usuarios": [self.clara.pk],
        })
        self.assertEqual(respuesta.status_code, 201, respuesta.content)
        return respuesta.json()["id"]

    def operacion(self, tipo="COMPRA", monto=100):
        return {"clienteId": self.cliente_id, "tipo": tipo, "moneda": "USD", "monto": monto}

    def comprar(self, tipo="COMPRA", monto=100):
        """Clara cotiza y confirma, como en el modal de la maqueta."""
        self.entrar(self.clara)
        presupuesto = self.post("api_operaciones_cotizar", self.operacion(tipo, monto)).json()
        respuesta = self.post(
            "api_operaciones_confirmar", {**self.operacion(tipo, monto), "tasaBase": presupuesto["tasaBase"]}
        )
        self.assertEqual(respuesta.status_code, 201, respuesta.content)
        return presupuesto, respuesta.json()


class TransaccionWebCompletaTest(BaseTransaccionCompleta):
    """Compra y venta por la web, de la cotización a la factura."""

    def test_compra_de_la_cotizacion_a_la_factura(self):
        presupuesto, operacion = self.comprar("COMPRA", 100)

        # El presupuesto que vio el cliente es lo que se le cobró.
        # 100 USD a 7400 = 740.000 Gs; comisión 1 % = 7.400; total 747.400.
        self.assertEqual(presupuesto["totalGuaranies"], 747400)
        self.assertEqual(operacion["estado"], "PAGADA")
        self.assertEqual(operacion["totalGuaranies"], 747400)

        # Le llegó la notificación de la compra.
        aviso = Notificacion.objects.get(usuario=self.clara)
        self.assertEqual(aviso.tipo, Notificacion.Tipo.OPERACION_EXITOSA)

        # Se generó la factura, a nombre del cliente y no de la usuaria.
        facturas = self.client.get(reverse("api_facturas")).json()["facturas"]
        self.assertEqual(len(facturas), 1)
        factura = facturas[0]
        self.assertEqual(factura["cliente"], "Comercial Clara S.A.")
        self.assertEqual(factura["documento"], "80002247-5")
        self.assertEqual((factura["origen"], factura["operacionId"]), ("Web", operacion["id"]))
        self.assertEqual(factura["monto"], 747400)
        self.assertEqual(factura["estado"], "SIMULADA")  # la emisión está apagada

        # Queda en el historial del cliente...
        historial = self.client.get(reverse("api_operaciones")).json()
        self.assertEqual([o["estado"] for o in historial["operaciones"]], ["PAGADA"])

        # ...y el analista la ve en el reporte con su ganancia:
        # comisión 7.400 + 50 por dólar sobre el precio medio (7350).
        self.entrar(self.analista)
        reporte = self.client.get(reverse("api_reportes_transacciones")).json()
        self.assertEqual(reporte["totales"]["operaciones"], 1)
        self.assertEqual(reporte["operaciones"][0]["ganancia"], 7400 + 5000)

    def test_venta_recibe_el_monto_menos_la_comision(self):
        _, operacion = self.comprar("VENTA", 100)
        # 100 USD a 7300 = 730.000 Gs; comisión 1 % = 7.300; recibe 722.700.
        self.assertEqual(operacion["totalGuaranies"], 722700)
        factura = Factura.objects.get()
        self.assertEqual(factura.total, Decimal("722700"))
        self.assertEqual(factura.de["iTipTra"], "6")  # compra de divisas

    def test_si_la_cotizacion_cambia_antes_de_pagar_no_se_cobra_ni_se_factura(self):
        self.entrar(self.clara)
        presupuesto = self.post("api_operaciones_cotizar", self.operacion()).json()
        # Mientras el cliente mira el presupuesto, el precio sube.
        Cotizacion.objects.filter(pk=self.cotizacion.pk).update(precio_venta=Decimal("7500"))

        operacion = self.post(
            "api_operaciones_confirmar", {**self.operacion(), "tasaBase": presupuesto["tasaBase"]}
        ).json()

        self.assertEqual(operacion["estado"], "CANCELADA")
        self.assertTrue(operacion["canceladaPorCotizacion"])
        self.assertEqual(operacion["tasaBaseNueva"], 7500)
        self.assertFalse(Factura.objects.exists())
        aviso = Notificacion.objects.get(usuario=self.clara)
        self.assertEqual(aviso.tipo, Notificacion.Tipo.OPERACION_FALLIDA)

    def test_una_pendiente_se_factura_recien_al_pagarla(self):
        self.entrar(self.clara)
        operacion = self.post("api_operaciones", self.operacion()).json()
        self.assertEqual(operacion["estado"], "PENDIENTE")
        self.assertFalse(Factura.objects.exists())

        pagada = self.post("api_operaciones_pagar", kwargs={"pk": operacion["id"]}).json()
        self.assertEqual(pagada["estado"], "PAGADA")
        self.assertEqual(Factura.objects.get().transaccion_id, operacion["id"])

    def test_una_cancelada_por_el_cliente_no_se_factura(self):
        self.entrar(self.clara)
        operacion = self.post("api_operaciones", self.operacion()).json()
        cancelada = self.post("api_operaciones_cancelar", kwargs={"pk": operacion["id"]}).json()
        self.assertEqual(cancelada["estado"], "CANCELADA")
        self.assertFalse(Factura.objects.exists())

    def test_otro_usuario_no_puede_operar_ni_ver_nada_del_cliente(self):
        self.comprar()
        self.entrar(self.intruso)
        rechazo = self.post("api_operaciones_confirmar", {**self.operacion(), "tasaBase": 7400})
        self.assertEqual(rechazo.status_code, 400)
        self.assertEqual(self.client.get(reverse("api_facturas")).json()["total"], 0)
        self.assertEqual(self.client.get(reverse("api_operaciones")).json()["total"], 0)
        self.assertEqual(self.client.get(reverse("api_reportes_ganancias")).status_code, 403)

    def test_cliente_sin_ruc_se_paga_igual_y_la_factura_se_reintenta(self):
        self.entrar(self.admin)
        self.client.patch(reverse("clientes_detalle", args=[self.cliente_id]),
                          data=json.dumps({"ruc": ""}), content_type="application/json")

        _, operacion = self.comprar()
        self.assertEqual(operacion["estado"], "PAGADA")  # la factura no frena el pago
        factura = self.client.get(reverse("api_facturas")).json()["facturas"][0]
        self.assertEqual(factura["estado"], "ERROR")
        self.assertTrue(factura["sePuedeEmitir"])

        # El administrador carga el RUC y el cliente reintenta.
        self.entrar(self.admin)
        self.client.patch(reverse("clientes_detalle", args=[self.cliente_id]),
                          data=json.dumps({"ruc": "80002247-5"}), content_type="application/json")
        self.entrar(self.clara)
        reintento = self.post("api_facturas_reintentar", kwargs={"pk": factura["id"]}).json()
        self.assertEqual(reintento["estado"], "SIMULADA")


@override_settings(**CONFIGURADO, FACTURA_SEGURA_EMITIR=True)
class TransaccionConFacturaEmitidaTest(BaseTransaccionCompleta):
    """Lo mismo con la emisión prendida, contra un doble de Factura Segura."""

    def setUp(self):
        super().setUp()
        parche = patch("facturacion.servicio._pedir", side_effect=respuesta_de_factura_segura)
        self.pedir = parche.start()
        self.addCleanup(parche.stop)

    def test_de_la_compra_al_kude_aprobado(self):
        self.comprar()

        # La factura se emitió con el primer número del rango.
        factura = self.client.get(reverse("api_facturas")).json()["facturas"][0]
        self.assertEqual(factura["numero"], "001-003-0000382")
        self.assertEqual(factura["estado"], "ENVIADA")
        self.assertEqual(factura["cdc"], CDC)
        self.assertTrue(factura["descargable"])

        # Un minuto después, el SIFEN la aprobó.
        self.pedir.side_effect = None
        self.pedir.return_value = [{"estado_sifen": "Aprobado", "desc_sifen": "0260 - Aprobado"}]
        aprobada = self.post("api_facturas_actualizar", kwargs={"pk": factura["id"]}).json()
        self.assertEqual(aprobada["estado"], "APROBADA")

        # El cliente descarga el KuDE y el XML.
        with patch("facturacion.servicio._bajar", return_value=b"%PDF-1.4"):
            pdf = self.client.get(reverse("api_facturas_descargar", args=[factura["id"], "kude"]))
            xml = self.client.get(reverse("api_facturas_descargar", args=[factura["id"], "xml"]))
        self.assertEqual((pdf.status_code, pdf["Content-Type"]), (200, "application/pdf"))
        self.assertEqual((xml.status_code, xml["Content-Type"]), (200, "application/xml"))

    def test_si_factura_segura_esta_caida_la_operacion_se_paga_igual(self):
        self.pedir.side_effect = SinConfirmar("No hubo respuesta de Factura Segura.")
        _, operacion = self.comprar()
        self.assertEqual(operacion["estado"], "PAGADA")
        # No se llegó a emitir: queda en error, sin gastar número, para reintentar.
        factura = Factura.objects.get()
        self.assertEqual((factura.estado, factura.numero), (Factura.Estado.ERROR, None))


class TransaccionDeCajaCompletaTest(BaseTransaccionCompleta):
    """Venta y compra en la ventanilla, de la apertura a la factura."""

    def setUp(self):
        super().setUp()
        guarani = Moneda.objects.create(codigo="PYG", nombre="Guaraní", simbolo="Gs", es_local=True)
        billete_usd = Denominacion.objects.create(moneda=self.usd, valor=100)
        billete_pyg = Denominacion.objects.create(moneda=guarani, valor=100000)
        self.entrar(self.cajero)
        apertura = self.post("api_caja_apertura", {"denominaciones": [
            {"denominacion_id": billete_usd.pk, "cantidad_unidades": 10},
            {"denominacion_id": billete_pyg.pk, "cantidad_unidades": 100},
        ]})
        self.assertEqual(apertura.status_code, 201, apertura.content)

    def operar(self, ruta, monto, **extra):
        self.entrar(self.cajero)
        respuesta = self.post(ruta, {"cliente_id": self.cliente_id, "moneda": "USD",
                                     "monto_divisa": monto, **extra})
        self.assertEqual(respuesta.status_code, 201, respuesta.content)
        return respuesta.json()

    def test_venta_en_ventanilla_de_la_apertura_a_la_factura(self):
        # La casa vende 100 USD: 7400 menos el 1 % del segmento = 7326.
        operacion = self.operar("api_caja_ventas", "100", tipo_pago="EFECTIVO")
        self.assertEqual(operacion["montoLocalTotal"], 732600)

        # El cajero recibe el aviso y ve la factura de la operación.
        self.assertTrue(Notificacion.objects.filter(
            usuario=self.cajero, tipo=Notificacion.Tipo.OPERACION_EXITOSA).exists())
        factura = self.client.get(reverse("api_facturas")).json()["facturas"][0]
        self.assertEqual(factura["cliente"], "Comercial Clara S.A.")
        self.assertEqual((factura["origen"], factura["operacionId"]), ("Caja", operacion["id"]))
        self.assertEqual(factura["monto"], 732600)

        # La usuaria del cliente también la ve; otro usuario, no.
        self.entrar(self.clara)
        self.assertEqual(self.client.get(reverse("api_facturas")).json()["total"], 1)
        self.entrar(self.intruso)
        self.assertEqual(self.client.get(reverse("api_facturas")).json()["total"], 0)

        # La caja refleja la operación: salieron dólares y entraron guaraníes.
        self.entrar(self.cajero)
        resumen = {fila["moneda"]: fila for fila in
                   self.client.get(reverse("api_caja_resumen_cierre")).json()["resumen"]}
        self.assertEqual(resumen["USD"]["saldoTeorico"], 1000 - 100)
        self.assertEqual(resumen["PYG"]["saldoTeorico"], 10_000_000 + 732_600)

    def test_compra_en_ventanilla_se_factura_como_compra_de_divisas(self):
        self.operar("api_caja_compras", "50")
        factura = Factura.objects.get()
        self.assertEqual(factura.compra_caja, CompraCaja.objects.get())
        self.assertEqual(factura.de["iTipTra"], "6")   # compra de divisas
        self.assertEqual(factura.de["iIndPres"], "1")  # presencial

    def test_cada_operacion_tiene_su_factura(self):
        self.operar("api_caja_ventas", "10", tipo_pago="EFECTIVO")
        self.operar("api_caja_compras", "20")
        self.comprar()
        self.assertEqual(Factura.objects.count(), 3)
        self.assertEqual(Factura.objects.exclude(venta_caja=None).get().venta_caja, VentaCaja.objects.get())
        self.assertEqual(Factura.objects.exclude(transaccion=None).get().transaccion,
                         Transaccion.objects.get())
