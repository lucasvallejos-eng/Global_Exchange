"""Pruebas de la terminal de autoservicio: reserva, depósito, entrega y cancelación."""
import json
from decimal import Decimal

from django.contrib.auth.models import Group
from django.urls import reverse

from cotizaciones.models import Cotizacion
from facturacion.models import Factura
from medios_pago.models import MedioPago
from monedas.models import Denominacion, Moneda
from operaciones import servicios as operaciones
from operaciones import tests as base
from operaciones.models import Transaccion

from . import servicio
from .models import BilleteTerminal, OperacionTerminal, Terminal
from .servicio import TerminalInvalida

# Lo que tiene la terminal al empezar cada prueba.
STOCK = {
    "USD": {100: 5, 20: 5, 10: 5, 1: 10},
    "PYG": {100000: 10, 10000: 20, 1000: 20, 100: 50, 50: 10},
}


class BaseTerminalTest(base.BaseOperacionesTest):
    """Clara sin segmento (tasas limpias: compra a 7400, venta a 7300) y una
    terminal con billetes de USD y PYG."""

    def setUp(self):
        super().setUp()
        self.cliente.segmento = None
        self.cliente.save()
        Moneda.objects.create(codigo="PYG", nombre="Guaraní", simbolo="₲", es_local=True)
        self.terminal = Terminal.objects.create(nombre="Terminal Centro", ubicacion="Asunción")
        self.billete = {}
        for codigo, billetes in STOCK.items():
            moneda = Moneda.objects.get(codigo=codigo)
            for valor, cantidad in billetes.items():
                denominacion = Denominacion.objects.create(moneda=moneda, valor=Decimal(valor))
                self.billete[(codigo, valor)] = denominacion
                BilleteTerminal.objects.create(terminal=self.terminal, denominacion=denominacion,
                                               cantidad=cantidad)

    def reservada(self, tipo=Transaccion.Tipo.COMPRA, monto="100"):
        return servicio.reservar(self.crear(tipo, monto), self.usuario)

    def deposito(self, codigo, **billetes):
        """``deposito("PYG", b100000=8)`` -> ``{id: 8}``."""
        return {str(self.billete[(codigo, int(clave[1:]))].pk): cantidad for clave, cantidad in billetes.items()}

    def stock(self, codigo, valor):
        return BilleteTerminal.objects.get(terminal=self.terminal,
                                           denominacion=self.billete[(codigo, valor)]).cantidad


class ReservaTest(BaseTerminalTest):
    def test_da_un_codigo_y_marca_el_medio_de_pago(self):
        reserva = self.reservada()
        self.assertEqual(len(reserva.codigo), 8)
        self.assertTrue(set(reserva.codigo) <= set(servicio.ALFABETO))
        self.assertEqual(reserva.estado, OperacionTerminal.Estado.ESPERANDO)
        reserva.transaccion.refresh_from_db()
        self.assertEqual(reserva.transaccion.medio_pago_descripcion, servicio.DESCRIPCION_MEDIO)
        # Reservar de nuevo devuelve la misma.
        self.assertEqual(servicio.reservar(reserva.transaccion, self.usuario).pk, reserva.pk)

    def test_solo_quien_opera_a_nombre_del_cliente(self):
        with self.assertRaisesMessage(TerminalInvalida, "no es de un cliente"):
            servicio.reservar(self.crear(), self.otro_usuario)

    def test_solo_una_pendiente_y_sin_tarjeta(self):
        pagada = operaciones.pagar(self.crear(), self.usuario)
        with self.assertRaisesMessage(TerminalInvalida, "pendiente"):
            servicio.reservar(pagada, self.usuario)
        tarjeta = MedioPago.objects.create(usuario=self.usuario, alias="Visa", activo=True,
                                           stripe_payment_method_id="pm_123")
        with self.assertRaisesMessage(TerminalInvalida, "tarjeta"):
            servicio.reservar(self.crear(medio_pago=tarjeta), self.usuario)

    def test_buscar_ignora_mayusculas_espacios_y_guiones(self):
        reserva = self.reservada()
        escrito = f" {reserva.codigo[:4].lower()}-{reserva.codigo[4:]} "
        self.assertEqual(servicio.buscar(escrito).pk, reserva.pk)
        with self.assertRaisesMessage(TerminalInvalida, "No hay ninguna operación"):
            servicio.buscar("ZZZZZZZZ")


class CompraEnTerminalTest(BaseTerminalTest):
    """El cliente compra 100 USD: deposita guaraníes (740.000) y retira dólares."""

    def test_deposita_recibe_la_divisa_y_el_vuelto(self):
        reserva = self.reservada()
        resultado = servicio.completar(reserva, self.terminal, self.deposito("PYG", b100000=8))
        self.assertEqual(resultado.estado, OperacionTerminal.Estado.COMPLETADA)
        self.assertEqual(resultado.depositado, {"PYG": {"100000": 8}})
        # 100 USD en un billete de 100; vuelto de 60.000 en billetes de 10.000.
        self.assertEqual(resultado.entregado, {"USD": {"100": 1}, "PYG": {"10000": 6}})
        self.assertIn("Vuelto: 60.000 PYG", resultado.detalle)
        transaccion = Transaccion.objects.get(pk=reserva.transaccion_id)
        self.assertEqual(transaccion.estado, Transaccion.Estado.PAGADA)
        self.assertEqual((self.stock("PYG", 100000), self.stock("PYG", 10000), self.stock("USD", 100)),
                         (18, 14, 4))

    def test_si_no_alcanza_no_cambia_nada(self):
        reserva = self.reservada()
        with self.assertRaisesMessage(TerminalInvalida, "Depositaste 700.000 PYG"):
            servicio.completar(reserva, self.terminal, self.deposito("PYG", b100000=7))
        reserva.refresh_from_db()
        self.assertEqual(reserva.estado, OperacionTerminal.Estado.ESPERANDO)
        self.assertEqual(reserva.transaccion.estado, Transaccion.Estado.PENDIENTE)
        self.assertEqual(self.stock("PYG", 100000), 10)

    def test_sin_billetes_para_entregar_sigue_esperando(self):
        # 1000 USD: la terminal tiene 660.
        reserva = self.reservada(monto="1000")
        with self.assertRaisesMessage(TerminalInvalida, "no tiene billetes para entregarte 1.000 USD"):
            servicio.completar(reserva, self.terminal, self.deposito("PYG", b100000=74))
        reserva.refresh_from_db()
        self.assertEqual(reserva.estado, OperacionTerminal.Estado.ESPERANDO)

    def test_sin_cambio_para_el_vuelto_pide_el_monto_justo(self):
        self.cliente.segmento = self.segmento  # con descuento y comisión: total 710.030
        self.cliente.save()
        reserva = self.reservada()
        with self.assertRaisesMessage(TerminalInvalida, "no tiene cambio"):
            # Vuelto de 89.970: la terminal no tiene monedas de 10 ni de 20.
            servicio.completar(reserva, self.terminal, self.deposito("PYG", b100000=8))

    def test_no_recibe_billetes_de_otra_moneda(self):
        reserva = self.reservada()
        with self.assertRaisesMessage(TerminalInvalida, "solo recibe billetes de PYG"):
            servicio.completar(reserva, self.terminal, self.deposito("USD", b100=10))

    def test_si_cambio_la_cotizacion_se_cancela_y_devuelve_los_billetes(self):
        reserva = self.reservada()
        Cotizacion.objects.filter(pk=self.cotizacion.pk).update(precio_venta=Decimal("7500"))
        resultado = servicio.completar(reserva, self.terminal, self.deposito("PYG", b100000=8))
        self.assertEqual(resultado.estado, OperacionTerminal.Estado.CANCELADA)
        self.assertIn("cambió antes del pago", resultado.detalle)
        transaccion = Transaccion.objects.get(pk=reserva.transaccion_id)
        self.assertTrue(transaccion.cancelada_por_cotizacion)
        self.assertEqual((self.stock("PYG", 100000), self.stock("USD", 100)), (10, 5))

    def test_no_se_completa_dos_veces(self):
        reserva = self.reservada()
        servicio.completar(reserva, self.terminal, self.deposito("PYG", b100000=8))
        with self.assertRaisesMessage(TerminalInvalida, "ya está completada"):
            servicio.completar(reserva, self.terminal, self.deposito("PYG", b100000=8))

    def test_una_terminal_fuera_de_servicio_no_atiende(self):
        self.terminal.activa = False
        with self.assertRaisesMessage(TerminalInvalida, "fuera de servicio"):
            servicio.completar(self.reservada(), self.terminal, self.deposito("PYG", b100000=8))

    def test_al_pagarse_se_genera_la_factura(self):
        reserva = self.reservada()
        with self.captureOnCommitCallbacks(execute=True):
            servicio.completar(reserva, self.terminal, self.deposito("PYG", b100000=8))
        self.assertTrue(Factura.objects.filter(transaccion_id=reserva.transaccion_id).exists())


class VentaEnTerminalTest(BaseTerminalTest):
    """El cliente vende 10 USD a 7300: deposita los dólares y recibe 73.000 PYG."""

    def test_retira_los_guaranies_en_efectivo(self):
        reserva = self.reservada(Transaccion.Tipo.VENTA, "10")
        resultado = servicio.completar(reserva, self.terminal, self.deposito("USD", b10=1))
        self.assertEqual(resultado.estado, OperacionTerminal.Estado.COMPLETADA)
        self.assertEqual(resultado.entregado, {"PYG": {"10000": 7, "1000": 3}})
        self.assertEqual((self.stock("USD", 10), self.stock("PYG", 10000)), (6, 13))

    def test_o_se_acreditan_en_la_cuenta_del_cliente(self):
        reserva = self.reservada(Transaccion.Tipo.VENTA, "10")
        resultado = servicio.completar(reserva, self.terminal, self.deposito("USD", b10=1),
                                       OperacionTerminal.Entrega.CUENTA)
        self.assertEqual(resultado.entrega, OperacionTerminal.Entrega.CUENTA)
        self.assertEqual(resultado.entregado, {})
        self.assertIn("Se acreditaron 73.000 PYG en la cuenta 001", resultado.detalle)
        self.assertEqual(self.stock("PYG", 10000), 20)

    def test_sin_cuenta_no_se_puede_acreditar(self):
        self.cliente.cuenta_acreditar = ""
        self.cliente.save()
        reserva = self.reservada(Transaccion.Tipo.VENTA, "10")
        with self.assertRaisesMessage(TerminalInvalida, "no tiene una cuenta"):
            servicio.completar(reserva, self.terminal, self.deposito("USD", b10=1),
                               OperacionTerminal.Entrega.CUENTA)

    def test_en_una_compra_la_acreditacion_se_ignora(self):
        resultado = servicio.completar(self.reservada(), self.terminal, self.deposito("PYG", b100000=8),
                                       OperacionTerminal.Entrega.CUENTA)
        self.assertEqual(resultado.entrega, OperacionTerminal.Entrega.EFECTIVO)


class CancelacionTest(BaseTerminalTest):
    def test_el_cliente_cancela_en_la_terminal(self):
        reserva = servicio.cancelar(self.reservada(), self.terminal)
        self.assertEqual(reserva.estado, OperacionTerminal.Estado.CANCELADA)
        self.assertEqual(Transaccion.objects.get(pk=reserva.transaccion_id).estado, Transaccion.Estado.CANCELADA)

    def test_si_se_cancelo_en_la_web_la_terminal_no_la_completa(self):
        reserva = self.reservada()
        operaciones.cancelar(reserva.transaccion, self.usuario)
        self.assertEqual(servicio.buscar(reserva.codigo).estado, OperacionTerminal.Estado.CANCELADA)
        with self.assertRaisesMessage(TerminalInvalida, "ya está cancelada"):
            servicio.completar(reserva, self.terminal, self.deposito("PYG", b100000=8))


class DesgloseTest(base.TestCase):
    def test_usa_los_billetes_mas_grandes_que_hay(self):
        disponibles = {Decimal(100): 1, Decimal(20): 5, Decimal(5): 2}
        self.assertEqual(servicio.desglosar(Decimal(150), disponibles),
                         {Decimal(100): 1, Decimal(20): 2, Decimal(5): 2})
        self.assertIsNone(servicio.desglosar(Decimal(3), disponibles))
        self.assertEqual(servicio.desglosar(Decimal(0), disponibles), {})


class PantallasTest(BaseTerminalTest):
    """El recorrido en la pantalla de quiosco, sin iniciar sesión."""

    def test_de_la_reserva_al_comprobante(self):
        transaccion = self.crear()
        self.entrar(self.usuario)
        self.client.post(reverse("terminal_reservar", args=[transaccion.pk]))
        reserva = OperacionTerminal.objects.get(transaccion=transaccion)
        detalle = self.client.get(reverse("detalle_operacion", args=[transaccion.pk]))
        self.assertContains(detalle, reserva.codigo)
        self.client.logout()

        self.assertContains(self.client.get(reverse("terminal_inicio")), "Terminal Centro")
        respuesta = self.client.post(reverse("terminal_codigo", args=[self.terminal.pk]),
                                     {"codigo": reserva.codigo.lower()})
        self.assertRedirects(respuesta, reverse("terminal_operacion", args=[self.terminal.pk, reserva.codigo]))
        pantalla = self.client.get(respuesta["Location"])
        self.assertContains(pantalla, "Comprás 100")
        self.assertContains(pantalla, f'name="billete_{self.billete[("PYG", 100000)].pk}"')

        campo = f"billete_{self.billete[('PYG', 100000)].pk}"
        corto = self.client.post(respuesta["Location"], {campo: "7"})
        self.assertContains(corto, "Depositaste 700.000 PYG")
        listo = self.client.post(respuesta["Location"], {campo: "8"})
        self.assertContains(listo, "Operación completada")
        self.assertContains(listo, "Vuelto: 60.000 PYG")
        # Volver a abrir el código muestra el comprobante, no el formulario.
        self.assertContains(self.client.get(respuesta["Location"]), "Operación completada")

    def test_codigo_equivocado_y_cancelacion(self):
        respuesta = self.client.post(reverse("terminal_codigo", args=[self.terminal.pk]), {"codigo": "NOEXISTE"})
        self.assertContains(respuesta, "No hay ninguna operación")
        reserva = self.reservada()
        cancelada = self.client.post(reverse("terminal_cancelar", args=[self.terminal.pk, reserva.codigo]))
        self.assertContains(cancelada, "Operación cancelada")

    def test_el_estado_de_las_terminales_es_para_administrador_y_cajero(self):
        self.entrar(self.usuario)
        self.assertEqual(self.client.get(reverse("terminal_estado")).status_code, 403)
        cajero = base.Usuario.objects.create_user(username="cajero")
        cajero.groups.add(Group.objects.get_or_create(name="cajero")[0])
        self.entrar(cajero)
        self.assertContains(self.client.get(reverse("terminal_estado")), "Terminal Centro")


class ApiTerminalTest(BaseTerminalTest):
    def test_reserva_desde_la_maqueta_y_lista_las_reservas(self):
        self.entrar(self.usuario)
        respuesta = self.client.post(
            reverse("api_terminal_reservas"),
            data=json.dumps({"clienteId": self.cliente.pk, "tipo": "COMPRA", "moneda": "USD", "monto": 100}),
            content_type="application/json",
        )
        self.assertEqual(respuesta.status_code, 201)
        datos = respuesta.json()
        self.assertEqual(len(datos["codigo"]), 8)
        self.assertEqual(datos["deposita"], {"moneda": "PYG", "monto": 740000})
        self.assertEqual(datos["recibe"], {"moneda": "USD", "monto": 100})
        self.assertEqual(datos["operacion"]["estado"], "PENDIENTE")
        self.assertTrue(datos["urlTerminal"].endswith("/terminal/"))

        lista = self.client.get(reverse("api_terminal_reservas")).json()["reservas"]
        self.assertEqual([r["codigo"] for r in lista], [datos["codigo"]])
        self.assertEqual(self.client.get(reverse("api_terminal_terminales")).json()["terminales"][0]["nombre"],
                         "Terminal Centro")

    def test_otro_usuario_no_ve_ni_reserva_a_nombre_de_clara(self):
        self.reservada()
        self.entrar(self.otro_usuario)
        self.assertEqual(self.client.get(reverse("api_terminal_reservas")).json()["reservas"], [])
        respuesta = self.client.post(
            reverse("api_terminal_reservas"),
            data=json.dumps({"clienteId": self.cliente.pk, "tipo": "COMPRA", "moneda": "USD", "monto": 1}),
            content_type="application/json",
        )
        self.assertEqual(respuesta.status_code, 400)
