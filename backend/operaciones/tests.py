"""Pruebas de las operaciones de compra y venta (Sprint 3)."""
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase

from clientes.models import Cliente
from comisiones.models import SegmentoCliente
from cotizaciones.models import Cotizacion
from medios_pago.models import MedioPago
from monedas.models import Moneda

from . import servicios
from .models import Transaccion
from .servicios import OperacionInvalida

Usuario = get_user_model()


class BaseOperacionesTest(TestCase):
    """Un cliente VIP con un usuario asociado, y USD a 7300 / 7400."""

    def setUp(self):
        self.usuario = Usuario.objects.create_user(username="clara")
        self.usuario.groups.add(Group.objects.get_or_create(name="cliente")[0])
        self.otro_usuario = Usuario.objects.create_user(username="intruso")
        self.otro_usuario.groups.add(Group.objects.get_or_create(name="cliente")[0])

        self.segmento = SegmentoCliente.objects.create(
            nombre="Prueba VIP",
            porcentaje_comision=Decimal("1.00"),
            descuento_compra=Decimal("0.05"),
        )
        self.cliente = Cliente.objects.create(
            nombre="Clara Cliente",
            tipo=Cliente.Tipo.FISICA,
            direccion="Asunción",
            cuenta_acreditar="001",
            correo="clara@example.com",
            segmento=self.segmento,
        )
        self.cliente.usuarios.add(self.usuario)

        self.usd = Moneda.objects.create(codigo="USD", nombre="Dólar", simbolo="$")
        self.cotizacion = Cotizacion.objects.create(
            moneda=self.usd, precio_compra=Decimal("7300"), precio_venta=Decimal("7400")
        )

    def crear(self, tipo=Transaccion.Tipo.COMPRA, monto="100", **extra):
        return servicios.crear_operacion(
            self.usuario, self.cliente, tipo, self.usd, Decimal(monto), **extra
        )


class CalculoTest(BaseOperacionesTest):
    """Cálculo de comisión y tasa aplicada."""

    def test_compra_aplica_descuento_sobre_precio_de_venta_y_suma_comision(self):
        t = self.crear(Transaccion.Tipo.COMPRA, "100")
        # 7400 con 5 % de descuento = 7030; 100 USD = 703.000 Gs; 1 % = 7.030.
        self.assertEqual(t.tasa_base, Decimal("7400"))
        self.assertEqual(t.tasa_aplicada, Decimal("7030.0000"))
        self.assertEqual(t.monto_guaranies, Decimal("703000"))
        self.assertEqual(t.comision, Decimal("7030"))
        self.assertEqual(t.total_guaranies, Decimal("710030"))

    def test_venta_usa_precio_de_compra_sin_descuento_y_resta_comision(self):
        t = self.crear(Transaccion.Tipo.VENTA, "100")
        # 100 USD a 7300 = 730.000 Gs; 1 % = 7.300 que se descuentan.
        self.assertEqual(t.tasa_base, Decimal("7300"))
        self.assertEqual(t.descuento_compra, Decimal("0"))
        self.assertEqual(t.tasa_aplicada, Decimal("7300.0000"))
        self.assertEqual(t.monto_guaranies, Decimal("730000"))
        self.assertEqual(t.comision, Decimal("7300"))
        self.assertEqual(t.total_guaranies, Decimal("722700"))

    def test_cliente_sin_segmento_no_tiene_descuento_ni_comision(self):
        self.cliente.segmento = None
        self.cliente.save()
        t = self.crear(Transaccion.Tipo.COMPRA, "100")
        self.assertEqual(t.tasa_aplicada, Decimal("7400.0000"))
        self.assertEqual(t.comision, Decimal("0"))
        self.assertEqual(t.total_guaranies, Decimal("740000"))

    def test_los_guaranies_se_redondean_a_enteros(self):
        t = self.crear(Transaccion.Tipo.VENTA, "0.33")
        # 0,33 × 7300 = 2409 exacto; 1 % = 24,09 → 24.
        self.assertEqual(t.monto_guaranies, Decimal("2409"))
        self.assertEqual(t.comision, Decimal("24"))
        self.assertEqual(t.total_guaranies, Decimal("2385"))

    def test_el_calculo_queda_guardado_aunque_cambie_el_segmento(self):
        t = self.crear(Transaccion.Tipo.COMPRA, "100")
        self.segmento.porcentaje_comision = Decimal("50")
        self.segmento.save()
        t.refresh_from_db()
        self.assertEqual(t.comision, Decimal("7030"))


class CrearOperacionTest(BaseOperacionesTest):
    """Validaciones al crear la operación."""

    def test_nace_pendiente_y_guarda_la_cotizacion_usada(self):
        t = self.crear()
        self.assertEqual(t.estado, Transaccion.Estado.PENDIENTE)
        self.assertEqual(t.cotizacion, self.cotizacion)
        self.assertEqual(t.usuario, self.usuario)

    def test_rn02_no_se_opera_a_nombre_de_un_cliente_ajeno(self):
        with self.assertRaises(OperacionInvalida):
            servicios.crear_operacion(
                self.otro_usuario, self.cliente, Transaccion.Tipo.COMPRA,
                self.usd, Decimal("100"),
            )
        self.assertFalse(Transaccion.objects.exists())

    def test_el_monto_tiene_que_ser_positivo(self):
        for monto in ("0", "-5"):
            with self.assertRaises(OperacionInvalida):
                self.crear(monto=monto)

    def test_moneda_sin_cotizacion_vigente(self):
        self.cotizacion.activa = False
        self.cotizacion.save()
        with self.assertRaises(OperacionInvalida):
            self.crear()

    def test_moneda_deshabilitada(self):
        self.usd.activo = False
        self.usd.save()
        with self.assertRaises(OperacionInvalida):
            self.crear()

    def test_medio_de_pago_propio_queda_registrado(self):
        medio = MedioPago.objects.create(
            usuario=self.usuario, tipo="TARJETA_DEBITO", alias="Débito Itaú"
        )
        t = self.crear(medio_pago=medio)
        self.assertEqual(t.medio_pago, medio)
        self.assertEqual(t.medio_pago_descripcion, "Débito Itaú (Tarjeta de Débito)")

    def test_no_se_usa_el_medio_de_pago_de_otro_usuario(self):
        ajeno = MedioPago.objects.create(usuario=self.otro_usuario, alias="Ajeno")
        with self.assertRaises(OperacionInvalida):
            self.crear(medio_pago=ajeno)

    def test_borrar_el_medio_de_pago_no_borra_la_operacion(self):
        medio = MedioPago.objects.create(usuario=self.usuario, alias="Billetera")
        t = self.crear(medio_pago=medio)
        medio.delete()
        t.refresh_from_db()
        self.assertIsNone(t.medio_pago)
        self.assertEqual(t.medio_pago_descripcion, "Billetera")


class PagoYCancelacionTest(BaseOperacionesTest):
    """Pago, y cancelación por cambio de cotización antes del pago."""

    def test_se_paga_si_la_cotizacion_no_cambio(self):
        t = servicios.pagar(self.crear(), self.usuario)
        self.assertEqual(t.estado, Transaccion.Estado.PAGADA)
        self.assertIsNotNone(t.fecha_pago)
        self.assertFalse(t.cancelada_por_cotizacion)

    def test_se_cancela_si_editaron_la_cotizacion(self):
        # Así cambia la cotización la pantalla de Django: edita la misma fila.
        t = self.crear(Transaccion.Tipo.COMPRA)
        self.cotizacion.precio_venta = Decimal("7500")
        self.cotizacion.save()

        t = servicios.pagar(t, self.usuario)
        self.assertEqual(t.estado, Transaccion.Estado.CANCELADA)
        self.assertTrue(t.cancelada_por_cotizacion)
        self.assertEqual(t.tasa_base_nueva, Decimal("7500"))
        self.assertIn("7500", t.motivo_cancelacion)
        self.assertIsNone(t.fecha_pago)

    def test_se_cancela_si_hay_una_cotizacion_nueva(self):
        # Así la cambia la maqueta: crea una nueva y desactiva la anterior.
        t = self.crear(Transaccion.Tipo.VENTA)
        self.cotizacion.activa = False
        self.cotizacion.save()
        Cotizacion.objects.create(
            moneda=self.usd, precio_compra=Decimal("7250"), precio_venta=Decimal("7400")
        )

        t = servicios.pagar(t, self.usuario)
        self.assertEqual(t.estado, Transaccion.Estado.CANCELADA)
        self.assertEqual(t.tasa_base_nueva, Decimal("7250"))

    def test_solo_importa_el_precio_que_usa_la_operacion(self):
        # Una compra usa el precio de venta: si solo cambió el de compra, se paga.
        t = self.crear(Transaccion.Tipo.COMPRA)
        self.cotizacion.precio_compra = Decimal("7000")
        self.cotizacion.save()
        self.assertEqual(servicios.pagar(t, self.usuario).estado, Transaccion.Estado.PAGADA)

    def test_cotizacion_nueva_con_el_mismo_precio_no_cancela(self):
        t = self.crear()
        self.cotizacion.activa = False
        self.cotizacion.save()
        Cotizacion.objects.create(
            moneda=self.usd, precio_compra=Decimal("7300"), precio_venta=Decimal("7400")
        )
        self.assertEqual(servicios.pagar(t, self.usuario).estado, Transaccion.Estado.PAGADA)

    def test_se_cancela_si_la_moneda_se_quedo_sin_cotizacion(self):
        t = self.crear()
        self.cotizacion.activa = False
        self.cotizacion.save()

        t = servicios.pagar(t, self.usuario)
        self.assertEqual(t.estado, Transaccion.Estado.CANCELADA)
        self.assertTrue(t.cancelada_por_cotizacion)
        self.assertIsNone(t.tasa_base_nueva)

    def test_no_se_paga_dos_veces(self):
        t = servicios.pagar(self.crear(), self.usuario)
        with self.assertRaises(OperacionInvalida):
            servicios.pagar(t, self.usuario)

    def test_una_cancelada_no_se_puede_pagar(self):
        t = servicios.cancelar(self.crear(), self.usuario)
        with self.assertRaises(OperacionInvalida):
            servicios.pagar(t, self.usuario)

    def test_otro_usuario_no_puede_pagar(self):
        t = self.crear()
        with self.assertRaises(OperacionInvalida):
            servicios.pagar(t, self.otro_usuario)
        t.refresh_from_db()
        self.assertEqual(t.estado, Transaccion.Estado.PENDIENTE)

    def test_cancelar_a_mano(self):
        t = servicios.cancelar(self.crear(), self.usuario)
        self.assertEqual(t.estado, Transaccion.Estado.CANCELADA)
        self.assertFalse(t.cancelada_por_cotizacion)
        self.assertIsNotNone(t.fecha_cancelacion)

    def test_no_se_cancela_una_pagada(self):
        t = servicios.pagar(self.crear(), self.usuario)
        with self.assertRaises(OperacionInvalida):
            servicios.cancelar(t, self.usuario)
