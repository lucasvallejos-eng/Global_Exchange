"""Pruebas de la alerta de cancelación por cambio de cotización (IS2GE-71)."""
from decimal import Decimal

from django.contrib.auth.models import Group
from django.urls import reverse

from . import servicios
from . import tests as base
from .models import Transaccion


class RecotizarTest(base.BaseOperacionesTest):
    """Cuánto saldría hoy una operación cancelada."""

    def test_usa_la_cotizacion_vigente(self):
        t = self.crear(Transaccion.Tipo.COMPRA, "100")
        self.cotizacion.precio_venta = Decimal("7600")
        self.cotizacion.save()
        calculo = servicios.recotizar(t)
        # 7600 con 5 % de descuento = 7220; 100 USD = 722.000; +1 % = 729.220.
        self.assertEqual(calculo["tasa_aplicada"], Decimal("7220.0000"))
        self.assertEqual(calculo["total_guaranies"], Decimal("729220"))

    def test_sin_cotizacion_vigente_devuelve_none(self):
        t = self.crear()
        self.cotizacion.activa = False
        self.cotizacion.save()
        self.assertIsNone(servicios.recotizar(t))


class AlertaEnPantallaTest(base.BaseOperacionesTest):
    """La alerta que ve el cliente en el detalle de la operación."""

    def setUp(self):
        super().setUp()
        self.entrar(self.usuario)

    def cancelar_por_cotizacion(self, precio_venta="7600"):
        t = self.crear(Transaccion.Tipo.COMPRA, "100")
        self.cotizacion.precio_venta = Decimal(precio_venta)
        self.cotizacion.save()
        return servicios.pagar(t, self.usuario)

    def detalle(self, t):
        return self.client.get(reverse("detalle_operacion", args=[t.pk]))

    def test_explica_que_paso_y_que_no_se_cobro(self):
        respuesta = self.detalle(self.cancelar_por_cotizacion())
        self.assertContains(respuesta, 'role="alert"')
        self.assertContains(respuesta, "No se te cobró nada")
        self.assertContains(respuesta, "Volver a operar con la cotización actual")

    def test_muestra_el_total_nuevo_y_la_diferencia(self):
        respuesta = self.detalle(self.cancelar_por_cotizacion())
        contexto = respuesta.context
        self.assertEqual(contexto["recotizacion"]["total_guaranies"], Decimal("729220"))
        # Antes 710.030, ahora 729.220: 19.190 más.
        self.assertEqual(contexto["diferencia"], Decimal("19190"))
        self.assertTrue(contexto["diferencia_es_mayor"])

    def test_el_boton_lleva_al_formulario_con_los_mismos_datos(self):
        t = self.cancelar_por_cotizacion()
        respuesta = self.detalle(t)
        self.assertContains(respuesta, f"moneda={self.usd.pk}")
        self.assertContains(respuesta, "monto=100.00")
        self.assertContains(respuesta, f"cliente={self.cliente.pk}")

        formulario = self.client.get(
            reverse("operar"),
            {"tipo": "COMPRA", "moneda": self.usd.pk, "monto": "100.00", "cliente": self.cliente.pk},
        )
        self.assertContains(formulario, 'value="100.00"')
        self.assertContains(formulario, '<option value="COMPRA" selected>')

    def test_sin_cotizacion_vigente_no_ofrece_volver_a_operar(self):
        t = self.crear()
        self.cotizacion.activa = False
        self.cotizacion.save()
        respuesta = self.detalle(servicios.pagar(t, self.usuario))
        self.assertContains(respuesta, "se quedó sin cotización vigente")
        self.assertNotContains(respuesta, "Volver a operar")

    def test_la_cancelacion_manual_no_muestra_la_alerta(self):
        t = servicios.cancelar(self.crear(), self.usuario)
        respuesta = self.detalle(t)
        self.assertContains(respuesta, "Cancelada por el usuario")
        self.assertNotContains(respuesta, 'role="alert"')

    def test_quien_solo_consulta_no_ve_el_boton_de_volver_a_operar(self):
        t = self.cancelar_por_cotizacion()
        admin = base.Usuario.objects.create_user(username="admin")
        admin.groups.add(Group.objects.get_or_create(name="administrador")[0])
        self.entrar(admin)
        respuesta = self.detalle(t)
        self.assertContains(respuesta, "No se te cobró nada")
        self.assertNotContains(respuesta, "Volver a operar")
