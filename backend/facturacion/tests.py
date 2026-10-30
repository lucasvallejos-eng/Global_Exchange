"""Pruebas de la facturación electrónica, sin llamar a Factura Segura de verdad.

``servicio._pedir`` (el único punto que sale a la red) se reemplaza por un
doble: se prueba qué le mandamos, cómo interpretamos lo que responde y, sobre
todo, que **no se gasten números de factura** cuando no corresponde.
"""
import dataclasses
import io
import json
import urllib.error
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch

from django.test import override_settings
from django.urls import reverse
from django.utils.formats import number_format

from operaciones import servicios as operaciones
from operaciones import tests as base
from operaciones.models import Transaccion

from . import servicio
from .models import Factura
from .servicio import ErrorFacturaSegura, FacturaInvalida, SinConfirmar

EMISOR = {
    "ruc": "80002247", "dv": "5", "tipo_contribuyente": "2",
    "nombre": "Global Exchange S.A.", "direccion": "Av. Mcal. López 100", "numero_casa": "100",
    "departamento_codigo": "1", "departamento": "CAPITAL",
    "ciudad_codigo": "1", "ciudad": "ASUNCION (DISTRITO)",
    "telefono": "021000000", "email": "emisor@example.com",
    "actividad_codigo": "66190", "actividad": "Casa de cambios",
}
NUMERACION = {
    "timbrado": "12345678", "timbrado_inicio": "2026-01-01",
    "establecimiento": "001", "punto_expedicion": "003",
    "factura_desde": 382, "factura_hasta": 393,
}
CONFIGURADO = {
    "FACTURA_SEGURA_TOKEN": "token-de-prueba",
    "FACTURA_SEGURA_LOCAL_ONLY": False,
    "FACTURA_SEGURA_EMISOR": EMISOR,
    "FACTURA_SEGURA_NUMERACION": NUMERACION,
}
CDC = "0" * 43 + "1"


def respuesta_de_factura_segura(operation, params):
    """Lo que respondería Factura Segura cuando todo sale bien."""
    if operation == "calcular_de":
        return [{"DE": {**params["DE"], "dTotGralOpe": "calculado"}}]
    if operation == "generar_de":
        return [{"CDC": CDC}]
    raise AssertionError(f"Operación inesperada: {operation}")


class BaseFacturacionTest(base.BaseOperacionesTest):
    """Un cliente con RUC y ``_pedir`` reemplazado por un doble."""

    def setUp(self):
        super().setUp()
        self.cliente.ruc = "2595733-3"
        self.cliente.save()
        parche = patch("facturacion.servicio._pedir", side_effect=respuesta_de_factura_segura)
        self.pedir = parche.start()
        self.addCleanup(parche.stop)

    def pagada(self, tipo=Transaccion.Tipo.COMPRA, monto="100"):
        return operaciones.pagar(self.crear(tipo, monto), self.usuario)

    def operaciones_pedidas(self):
        return [llamada.args[0] for llamada in self.pedir.call_args_list]

    def emitida(self, origen=None):
        """Lo que pasa en pantalla: el pago la deja simulada y el administrador la emite."""
        return servicio.reintentar(servicio.facturar(origen or self.pagada()))


class DigitoVerificadorTest(base.TestCase):
    def test_ruc_de_ejemplo_de_la_especificacion(self):
        self.assertEqual(servicio.digito_verificador("80002247"), 5)
        self.assertEqual(servicio.digito_verificador("2595733"), 3)


@override_settings(**CONFIGURADO)
class DocumentoElectronicoTest(BaseFacturacionTest):
    """Qué se manda en el JSON de la factura."""

    def test_el_receptor_es_el_cliente_y_no_el_usuario(self):
        self.usuario.first_name, self.usuario.last_name = "Ursula", "Usuaria"
        self.usuario.save()
        de = servicio.armar_de(self.pagada(), 382)
        self.assertEqual(de["dNomRec"], "Clara Cliente")
        self.assertEqual(de["dEmailRec"], "clara@example.com")
        self.assertEqual((de["dRucRec"], de["dDVRec"]), ("2595733", "3"))
        self.assertNotIn("Ursula", json.dumps(de))

    def test_numero_timbrado_y_emisor(self):
        de = servicio.armar_de(self.pagada(), 382)
        self.assertEqual((de["dEst"], de["dPunExp"], de["dNumDoc"]), ("001", "003", "0000382"))
        self.assertEqual(de["dNumTim"], "12345678")
        self.assertEqual((de["dRucEm"], de["dDVEmi"]), ("80002247", "5"))
        self.assertEqual(de["cMoneOpe"], "PYG")

    def test_compra_del_cliente_es_venta_de_divisa_con_comision_gravada(self):
        # 100 USD a 7030 = 703.000 Gs; comisión 1 % = 7.030; total 710.030.
        de = servicio.armar_de(self.pagada(Transaccion.Tipo.COMPRA), 382)
        self.assertEqual(de["iTipTra"], "5")
        divisa, comision = de["gCamItem"]
        self.assertEqual((divisa["dPUniProSer"], divisa["iAfecIVA"]), ("703000", "3"))
        self.assertEqual((comision["dPUniProSer"], comision["iAfecIVA"], comision["dTasaIVA"]),
                         ("7030", "1", "10"))
        self.assertEqual(de["gPaConEIni"][0]["dMonTiPag"], "710030")

    def test_venta_del_cliente_es_compra_de_divisa_con_la_comision_descontada(self):
        # 100 USD a 7300 = 730.000 Gs; comisión 1 % = 7.300; recibe 722.700.
        de = servicio.armar_de(self.pagada(Transaccion.Tipo.VENTA), 382)
        self.assertEqual(de["iTipTra"], "6")
        (divisa,) = de["gCamItem"]
        self.assertEqual((divisa["dPUniProSer"], divisa["dDescItem"]), ("730000", "7300"))
        self.assertEqual(de["gPaConEIni"][0]["dMonTiPag"], "722700")

    def test_sin_medio_de_pago_es_efectivo(self):
        self.assertEqual(servicio.armar_de(self.pagada(), 382)["gPaConEIni"][0]["iTiPago"], "1")

    def test_cliente_con_cedula_es_no_contribuyente(self):
        self.cliente.ruc = "4.567.890"
        self.cliente.save()
        de = servicio.armar_de(self.pagada(), 382)
        self.assertEqual((de["iNatRec"], de["iTipIDRec"], de["dNumIDRec"]), ("2", "1", "4567890"))
        self.assertNotIn("dRucRec", de)

    def test_ruc_con_digito_verificador_equivocado(self):
        self.cliente.ruc = "2595733-9"
        self.cliente.save()
        with self.assertRaisesMessage(FacturaInvalida, "no es válido"):
            servicio.armar_de(self.pagada(), 382)


class SinGastarNumerosTest(BaseFacturacionTest):
    """Por defecto no se emite nada."""

    def test_sin_token_queda_simulada_y_no_se_llama_a_nadie(self):
        factura = servicio.facturar(self.pagada())
        self.assertEqual(factura.estado, Factura.Estado.SIMULADA)
        self.assertIsNone(factura.numero)
        self.assertEqual(factura.cdc, "")
        self.pedir.assert_not_called()

    @override_settings(**{
        **CONFIGURADO, "FACTURA_SEGURA_LOCAL_ONLY": True, "FACTURA_SEGURA_EMITIR": True,
    })
    def test_modo_local_no_llama_a_factura_segura_aunque_emision_este_prendida(self):
        factura = servicio.facturar(self.pagada())
        self.assertEqual(factura.estado, Factura.Estado.SIMULADA)
        self.assertIsNone(factura.numero)
        self.assertIsNone(factura.cdc or None)
        self.pedir.assert_not_called()

    @override_settings(**CONFIGURADO, FACTURA_SEGURA_EMITIR=False)
    def test_con_token_y_emision_apagada_solo_se_valida(self):
        factura = servicio.facturar(self.pagada())
        self.assertEqual(factura.estado, Factura.Estado.SIMULADA)
        self.assertIsNone(factura.numero)
        self.assertEqual(self.operaciones_pedidas(), ["calcular_de"])
        self.assertEqual(factura.de["dTotGralOpe"], "calculado")

    @override_settings(**CONFIGURADO, FACTURA_SEGURA_EMITIR=True)
    def test_una_operacion_sin_pagar_no_se_factura(self):
        self.assertIsNone(servicio.facturar(self.crear()))
        self.assertFalse(Factura.objects.exists())
        self.pedir.assert_not_called()

    def test_guarda_a_nombre_de_quien_salio(self):
        factura = servicio.facturar(self.pagada())
        self.assertEqual(factura.receptor_nombre, "Clara Cliente")
        self.assertEqual(factura.receptor_documento, "2595733-3")
        self.assertEqual(factura.total, Decimal("710030"))

    def test_cliente_sin_ruc_queda_en_error_y_se_puede_reintentar(self):
        self.cliente.ruc = ""
        self.cliente.save()
        factura = servicio.facturar(self.pagada())
        self.assertEqual(factura.estado, Factura.Estado.ERROR)
        self.assertIn("no tiene RUC", factura.detalle)

        self.cliente.ruc = "2595733-3"
        self.cliente.save()
        factura.refresh_from_db()
        self.assertEqual(servicio.reintentar(factura).estado, Factura.Estado.SIMULADA)

    def test_una_simulada_no_se_reintenta_con_la_emision_apagada(self):
        factura = servicio.facturar(self.pagada())
        with self.assertRaises(FacturaInvalida):
            servicio.reintentar(factura)


@override_settings(**CONFIGURADO, FACTURA_SEGURA_EMITIR=True)
class EmisionTest(BaseFacturacionTest):
    """Con la emisión prendida."""

    def test_un_pago_no_emite_solo(self):
        with self.captureOnCommitCallbacks(execute=True):
            transaccion = self.pagada()
        factura = transaccion.factura
        self.assertEqual((factura.estado, factura.numero), (Factura.Estado.SIMULADA, None))
        self.assertIn("Falta que el administrador la emita", factura.detalle)
        self.assertEqual(self.operaciones_pedidas(), ["calcular_de"])

    def test_emite_con_el_primer_numero_del_rango(self):
        factura = self.emitida()
        self.assertEqual(factura.estado, Factura.Estado.ENVIADA)
        self.assertEqual(factura.numero, 382)
        self.assertEqual(factura.numero_completo, "001-003-0000382")
        self.assertEqual(factura.cdc, CDC)
        # Se valida al pagar, y al emitir se vuelve a calcular y se genera.
        self.assertEqual(self.operaciones_pedidas(), ["calcular_de", "calcular_de", "generar_de"])
        # A generar_de va el documento que devolvió calcular_de.
        self.assertEqual(self.pedir.call_args.args[1]["DE"]["dTotGralOpe"], "calculado")

    def test_cada_factura_toma_el_numero_siguiente(self):
        numeros = [self.emitida().numero for _ in range(3)]
        self.assertEqual(numeros, [382, 383, 384])

    def test_emitir_dos_veces_no_gasta_dos_numeros(self):
        factura = self.emitida()
        self.assertEqual(servicio.facturar(factura.transaccion).pk, factura.pk)
        with self.assertRaises(FacturaInvalida):
            servicio.reintentar(factura)
        self.assertEqual(self.operaciones_pedidas().count("generar_de"), 1)

    def test_si_factura_segura_dice_que_no_el_numero_queda_libre(self):
        self.pedir.side_effect = ErrorFacturaSegura("El valor del campo iTiOpe no es permitido")
        fallida = self.emitida()
        self.assertEqual(fallida.estado, Factura.Estado.ERROR)
        self.assertIsNone(fallida.numero)
        self.assertIn("iTiOpe", fallida.detalle)

        self.pedir.side_effect = respuesta_de_factura_segura
        self.assertEqual(self.emitida().numero, 382)

    def test_si_no_hay_respuesta_al_generar_conserva_el_numero(self):
        def se_corta_al_generar(operation, params):
            if operation == "generar_de":
                raise SinConfirmar("No hubo respuesta de Factura Segura.")
            return respuesta_de_factura_segura(operation, params)

        self.pedir.side_effect = se_corta_al_generar
        factura = self.emitida()
        self.assertEqual(factura.estado, Factura.Estado.SIN_CONFIRMAR)
        self.assertEqual(factura.numero, 382)
        # Otra factura no le saca el número...
        self.pedir.side_effect = respuesta_de_factura_segura
        self.assertEqual(self.emitida().numero, 383)
        # ...un segundo aviso de pago no la toca...
        self.assertEqual(servicio.facturar(factura.transaccion).estado, Factura.Estado.SIN_CONFIRMAR)
        # ...y el reintento manda el mismo.
        reintentada = servicio.reintentar(factura)
        self.assertEqual((reintentada.numero, reintentada.estado), (382, Factura.Estado.ENVIADA))

    def sin_confirmar(self):
        """Una factura a la que se le cortó la conexión justo al emitir."""
        def se_corta_al_generar(operation, params):
            if operation == "generar_de":
                raise SinConfirmar("No hubo respuesta de Factura Segura.")
            return respuesta_de_factura_segura(operation, params)

        self.pedir.side_effect = se_corta_al_generar
        factura = self.emitida()
        self.pedir.side_effect = respuesta_de_factura_segura
        return factura

    def test_un_no_al_reintentar_una_sin_confirmar_no_libera_el_numero(self):
        # La primera vez sí se había emitido: al reenviarla, Factura Segura
        # dice que ya existe. El 382 está gastado y nadie más lo puede tomar.
        factura = self.sin_confirmar()

        def ya_existe(operation, params):
            if operation == "generar_de":
                raise ErrorFacturaSegura("El documento 001-003-0000382 ya existe")
            return respuesta_de_factura_segura(operation, params)

        self.pedir.side_effect = ya_existe
        reintentada = servicio.reintentar(factura)
        self.assertEqual((reintentada.numero, reintentada.estado), (382, Factura.Estado.SIN_CONFIRMAR))
        self.assertIn("ya existe", reintentada.detalle)

        self.pedir.side_effect = respuesta_de_factura_segura
        self.assertEqual(self.emitida().numero, 383)

    def test_una_sin_confirmar_no_se_vuelve_simulada_con_la_emision_apagada(self):
        factura = self.sin_confirmar()
        self.pedir.reset_mock()
        with override_settings(FACTURA_SEGURA_EMITIR=False):
            reintentada = servicio.reintentar(factura)
        self.assertEqual((reintentada.numero, reintentada.estado), (382, Factura.Estado.SIN_CONFIRMAR))
        self.assertIn("emisión está apagada", reintentada.detalle)
        self.pedir.assert_not_called()

    def test_si_se_corta_al_calcular_no_queda_nada_sin_confirmar(self):
        self.pedir.side_effect = SinConfirmar("No hubo respuesta de Factura Segura.")
        factura = self.emitida()
        self.assertEqual(factura.estado, Factura.Estado.ERROR)
        self.assertIsNone(factura.numero)

    def test_cuando_se_acaban_los_numeros_no_se_emite(self):
        with override_settings(FACTURA_SEGURA_NUMERACION={**NUMERACION, "factura_hasta": 382}):
            self.emitida()
            factura = servicio.facturar(self.pagada())
            self.pedir.reset_mock()
            factura = servicio.reintentar(factura)
        self.assertEqual(factura.estado, Factura.Estado.ERROR)
        self.assertIn("Se acabaron los números", factura.detalle)
        self.pedir.assert_not_called()

    def test_sin_datos_del_emisor_no_se_llama_a_factura_segura(self):
        with override_settings(FACTURA_SEGURA_EMISOR={**EMISOR, "ruc": ""}):
            factura = self.emitida()
        self.assertEqual(factura.estado, Factura.Estado.ERROR)
        self.assertIn("ruc", factura.detalle)
        self.assertIsNone(factura.numero)
        self.pedir.assert_not_called()

    def test_la_actividad_puede_venir_sola_o_como_lista(self):
        lista = [{"cActEco": "66190", "dDesActEco": "Casa de cambios"},
                 {"cActEco": "62010", "dDesActEco": "Programación"}]
        con_lista = {**EMISOR, "actividad_codigo": "", "actividad": "", "actividades": json.dumps(lista)}
        sin_lista = {**EMISOR, "actividades": ""}
        with override_settings(FACTURA_SEGURA_EMISOR=con_lista):
            self.assertEqual(self.emitida().estado, Factura.Estado.ENVIADA)
            self.assertEqual(servicio.armar_de(self.pagada(), 382)["gActEco"], lista)
        with override_settings(FACTURA_SEGURA_EMISOR=sin_lista):
            self.assertEqual(self.emitida().estado, Factura.Estado.ENVIADA)

    def test_sin_actividad_economica_no_se_emite(self):
        sin_nada = {**EMISOR, "actividad_codigo": "", "actividad": "", "actividades": "[]"}
        with override_settings(FACTURA_SEGURA_EMISOR=sin_nada):
            factura = self.emitida()
        self.assertEqual((factura.estado, factura.numero), (Factura.Estado.ERROR, None))
        self.assertIn("actividad económica", factura.detalle)

    def test_una_simulada_se_puede_emitir_a_pedido(self):
        with override_settings(FACTURA_SEGURA_EMITIR=False):
            factura = servicio.facturar(self.pagada())
        self.assertEqual(factura.estado, Factura.Estado.SIMULADA)
        # Prender la emisión no la emite sola...
        self.assertEqual(servicio.facturar(factura.transaccion).estado, Factura.Estado.SIMULADA)
        # ...hay que pedirlo.
        self.assertEqual(servicio.reintentar(factura).estado, Factura.Estado.ENVIADA)


@override_settings(**CONFIGURADO, FACTURA_SEGURA_EMITIR=True)
class EstadoSifenTest(BaseFacturacionTest):
    """Cómo se interpreta ``get_estado_sifen``."""

    def setUp(self):
        super().setUp()
        self.factura = self.emitida()

    def consultar(self, **estado):
        self.pedir.side_effect = None
        self.pedir.return_value = [estado]
        return servicio.actualizar_estado(self.factura)

    def test_aprobada(self):
        factura = self.consultar(estado_sifen="Aprobado", desc_sifen="0260 - Aprobado")
        self.assertEqual(factura.estado, Factura.Estado.APROBADA)
        self.assertEqual(self.pedir.call_args.args,
                         ("get_estado_sifen", {"CDC": CDC, "dRucEm": "80002247"}))

    def test_aprobada_con_observacion(self):
        factura = self.consultar(estado_sifen="Aprobado con observación")
        self.assertEqual(factura.estado, Factura.Estado.APROBADA)

    def test_rechazada_guarda_el_motivo_y_se_puede_reintentar(self):
        factura = self.consultar(estado_sifen="Rechazado", desc_sifen="1001", error_sifen="RUC inexistente")
        self.assertEqual(factura.estado, Factura.Estado.RECHAZADA)
        self.assertEqual(factura.detalle, "1001 RUC inexistente")
        self.assertTrue(factura.se_puede_reintentar)

    def test_todavia_en_proceso(self):
        self.assertEqual(self.consultar(estado_sifen="ENVIADO_A_SIFEN").estado, Factura.Estado.ENVIADA)

    def test_la_cancelacion_se_mira_antes_que_la_aprobacion(self):
        factura = self.consultar(estado_sifen="Aprobado", estado_can="Aprobado", desc_can="Cancelado")
        self.assertEqual(factura.estado, Factura.Estado.CANCELADA)

    def test_una_simulada_no_se_consulta(self):
        with override_settings(FACTURA_SEGURA_EMITIR=False):
            simulada = servicio.facturar(self.pagada())
        self.pedir.reset_mock()
        servicio.actualizar_estado(simulada)
        self.pedir.assert_not_called()


@override_settings(**CONFIGURADO)
class ProtocoloTest(base.TestCase):
    """``_pedir``: qué se manda por HTTP y cómo se leen los errores."""

    def pedir(self, respuesta=None, error=None):
        cuerpo = io.BytesIO(json.dumps(respuesta or {}).encode())
        cuerpo.__enter__ = lambda s: s
        cuerpo.__exit__ = lambda s, *a: None
        with patch("facturacion.servicio.urllib.request.urlopen",
                   side_effect=error, return_value=cuerpo) as urlopen:
            try:
                return servicio._pedir("get_estado_sifen", {"CDC": CDC}), urlopen
            finally:
                self.urlopen = urlopen

    def test_manda_la_operacion_con_el_token(self):
        resultados, urlopen = self.pedir({"code": 0, "description": "OK", "results": [{"a": 1}]})
        self.assertEqual(resultados, [{"a": 1}])
        pedido = urlopen.call_args.args[0]
        self.assertEqual(pedido.full_url, "https://apitest.facturasegura.com.py/misife00/v1/esi")
        self.assertEqual(pedido.get_header("Authentication-token"), "token-de-prueba")
        self.assertEqual(json.loads(pedido.data),
                         {"operation": "get_estado_sifen", "params": {"CDC": CDC}})

    def test_codigo_negativo_es_un_error_con_su_descripcion(self):
        with self.assertRaisesMessage(ErrorFacturaSegura, "El RUC del emisor"):
            self.pedir({"code": -10021, "description": "El RUC del emisor se encuentra con estado INACTIVO",
                        "results": []})

    def test_sin_conexion_queda_sin_confirmar(self):
        with self.assertRaises(SinConfirmar):
            self.pedir(error=urllib.error.URLError("sin red"))
        with self.assertRaises(SinConfirmar):
            self.pedir(error=TimeoutError())

    def test_token_rechazado_no_es_sin_confirmar(self):
        error = urllib.error.HTTPError("url", 401, "Unauthorized", {}, None)
        with self.assertRaises(ErrorFacturaSegura) as contexto:
            self.pedir(error=error)
        self.assertNotIsInstance(contexto.exception, SinConfirmar)


class AlPagarTest(BaseFacturacionTest):
    """La factura se genera sola cuando la operación queda pagada."""

    def test_pagar_genera_la_factura(self):
        with self.captureOnCommitCallbacks(execute=True):
            transaccion = self.pagada()
        self.assertEqual(transaccion.factura.estado, Factura.Estado.SIMULADA)

    def test_una_pendiente_o_cancelada_no_genera_factura(self):
        with self.captureOnCommitCallbacks(execute=True):
            operaciones.cancelar(self.crear(), self.usuario)
            self.crear()
        self.assertFalse(Factura.objects.exists())

    def test_un_problema_con_la_factura_no_rompe_el_pago(self):
        with patch("facturacion.servicio.facturar", side_effect=RuntimeError("explotó")):
            with self.assertLogs("facturacion.senales", level="ERROR"):
                with self.captureOnCommitCallbacks(execute=True):
                    transaccion = self.pagada()
        self.assertEqual(transaccion.estado, Transaccion.Estado.PAGADA)


class PantallasYApiTest(BaseFacturacionTest):
    """Quién ve qué, y las descargas."""

    def setUp(self):
        super().setUp()
        self.factura = servicio.facturar(self.pagada())

    def test_la_api_lista_las_facturas_del_cliente(self):
        self.entrar(self.usuario)
        datos = self.client.get(reverse("api_facturas")).json()
        self.assertEqual(datos["total"], 1)
        self.assertEqual(datos["emision"], "simulada")
        factura = datos["facturas"][0]
        self.assertEqual(factura["cliente"], "Clara Cliente")
        self.assertEqual(factura["monto"], 710030)
        self.assertFalse(factura["descargable"])

    def test_otro_usuario_no_ve_ni_descarga_facturas_ajenas(self):
        self.entrar(self.otro_usuario)
        self.assertEqual(self.client.get(reverse("api_facturas")).json()["total"], 0)
        self.assertEqual(self.client.get(reverse("detalle_factura", args=[self.factura.pk])).status_code, 404)
        descarga = self.client.get(reverse("api_facturas_descargar", args=[self.factura.pk, "kude"]))
        self.assertEqual(descarga.status_code, 404)

    def test_sin_sesion_no_se_ve_nada(self):
        self.assertEqual(self.client.get(reverse("api_facturas")).status_code, 403)

    def test_una_simulada_no_tiene_archivos(self):
        self.entrar(self.usuario)
        descarga = self.client.get(reverse("api_facturas_descargar", args=[self.factura.pk, "kude"]))
        self.assertEqual(descarga.status_code, 409)

    @override_settings(**CONFIGURADO)
    def test_descarga_el_kude_y_el_xml_de_una_emitida(self):
        Factura.objects.filter(pk=self.factura.pk).update(
            cdc=CDC, numero=382, estado=Factura.Estado.APROBADA
        )
        self.entrar(self.usuario)
        with patch("facturacion.servicio._bajar", return_value=b"%PDF-1.4") as bajar:
            pdf = self.client.get(reverse("api_facturas_descargar", args=[self.factura.pk, "kude"]))
            xml = self.client.get(reverse("api_facturas_descargar", args=[self.factura.pk, "xml"]))
        self.assertEqual(pdf.status_code, 200)
        self.assertEqual(pdf.content, b"%PDF-1.4")
        self.assertEqual(pdf["Content-Type"], "application/pdf")
        self.assertIn("factura-001-003-0000382.pdf", pdf["Content-Disposition"])
        self.assertEqual(xml["Content-Type"], "application/xml")
        self.assertEqual([llamada.args[0] for llamada in bajar.call_args_list], ["dwn_kude", "dwn_xml"])

    def test_pantallas_de_lista_y_detalle(self):
        self.entrar(self.usuario)
        lista = self.client.get(reverse("listar_facturas"))
        self.assertContains(lista, "Clara Cliente")
        self.assertContains(lista, "La emisión está apagada")
        detalle = self.client.get(reverse("detalle_factura", args=[self.factura.pk]))
        self.assertContains(detalle, "Venta de divisa: 100 USD a 7030 Gs.")
        self.assertContains(detalle, number_format(710030, force_grouping=True))
        self.assertNotContains(detalle, "Descargar PDF")

    def test_reintentar_desde_la_api(self):
        self.cliente.ruc = ""
        self.cliente.save()
        fallida = servicio.facturar(self.pagada())
        self.cliente.ruc = "2595733-3"
        self.cliente.save()
        self.entrar(self.usuario)
        respuesta = self.client.post(reverse("api_facturas_reintentar", args=[fallida.pk]))
        self.assertEqual(respuesta.status_code, 403)
        # Una que no falló no se reintenta.
        respuesta = self.client.post(reverse("api_facturas_reintentar", args=[self.factura.pk]))
        self.assertEqual(respuesta.status_code, 403)

    @override_settings(**CONFIGURADO, FACTURA_SEGURA_EMITIR=True)
    def test_con_la_emision_prendida_el_cliente_no_puede_emitir(self):
        # self.factura es simulada: emitirla gastaría un número del rango.
        self.entrar(self.usuario)
        self.assertFalse(self.client.get(reverse("api_facturas")).json()["facturas"][0]["sePuedeEmitir"])
        respuesta = self.client.post(reverse("api_facturas_reintentar", args=[self.factura.pk]))
        self.assertEqual(respuesta.status_code, 403)
        self.assertIn("solo el administrador", respuesta.json()["error"])

        detalle = self.client.get(reverse("detalle_factura", args=[self.factura.pk]))
        self.assertNotContains(detalle, "Emitir de verdad")
        pantalla = self.client.post(reverse("reintentar_factura", args=[self.factura.pk]), follow=True)
        self.assertContains(pantalla, "solo el administrador")

        self.factura.refresh_from_db()
        self.assertEqual((self.factura.estado, self.factura.numero), (Factura.Estado.SIMULADA, None))
        self.pedir.assert_not_called()

    @override_settings(**CONFIGURADO, FACTURA_SEGURA_EMITIR=True)
    def test_con_la_emision_prendida_el_administrador_si_puede_emitir(self):
        admin = base.Usuario.objects.create_user(username="admin")
        admin.groups.add(base.Group.objects.get_or_create(name="administrador")[0])
        self.entrar(admin)
        self.assertTrue(self.client.get(reverse("api_facturas")).json()["facturas"][0]["sePuedeEmitir"])
        self.assertContains(self.client.get(reverse("detalle_factura", args=[self.factura.pk])),
                            "Emitir de verdad")
        respuesta = self.client.post(reverse("api_facturas_reintentar", args=[self.factura.pk]))
        self.assertEqual((respuesta.json()["estado"], respuesta.json()["numero"]),
                         ("ENVIADA", "001-003-0000382"))


class RucDelClienteTest(BaseFacturacionTest):
    """El RUC se carga por la API de clientes, como el resto de sus datos."""

    def test_el_administrador_lo_carga_y_la_api_lo_devuelve(self):
        admin = base.Usuario.objects.create_user(username="admin")
        admin.groups.add(base.Group.objects.get_or_create(name="administrador")[0])
        self.entrar(admin)
        respuesta = self.client.patch(
            reverse("clientes_detalle", args=[self.cliente.pk]),
            data=json.dumps({"ruc": "80002247-5"}), content_type="application/json",
        )
        self.assertEqual(respuesta.json()["ruc"], "80002247-5")
        self.cliente.refresh_from_db()
        self.assertEqual(self.cliente.ruc, "80002247-5")


@override_settings(**CONFIGURADO)
class FormaDePagoTest(BaseFacturacionTest):
    """Cómo se informa el pago, en la web y en la caja."""

    def pago(self, **cambios):
        operacion = dataclasses.replace(servicio.operacion_de(self.pagada()), **cambios)
        return servicio.armar_de(operacion, 382)["gPaConEIni"][0]

    def test_tarjeta_en_la_caja_pasa_por_pos(self):
        tarjeta = SimpleNamespace(alias="Visa ****4242", banco_o_proveedor="Stripe")
        pago = self.pago(presencial=True, forma_pago="TARJETA_STRIPE", medio_pago=tarjeta)
        self.assertEqual((pago["iTiPago"], pago["iDenTarj"], pago["iForProPa"]), ("3", "1", "1"))

    def test_tarjeta_en_la_web_es_pago_electronico(self):
        tarjeta = SimpleNamespace(alias="Mastercard ****4444", banco_o_proveedor=None)
        pago = self.pago(forma_pago="TARJETA_CREDITO", medio_pago=tarjeta)
        self.assertEqual((pago["iTiPago"], pago["iDenTarj"], pago["iForProPa"]), ("3", "2", "2"))

    def test_transferencia_y_billetera(self):
        self.assertEqual(self.pago(forma_pago="TRANSFERENCIA")["iTiPago"], "5")
        self.assertEqual(self.pago(forma_pago="BILLETERA_DIGITAL")["iTiPago"], "7")

    def test_una_forma_que_no_se_conoce_va_como_efectivo(self):
        pago = self.pago(forma_pago="Otro medio")
        self.assertEqual(pago["iTiPago"], "1")
        self.assertNotIn("iDenTarj", pago)
