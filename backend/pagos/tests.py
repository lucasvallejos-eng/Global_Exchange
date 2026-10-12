"""Pruebas de la integración con Stripe, sin llamar a Stripe de verdad.

``StripeClient`` se reemplaza por un doble: se prueba lo que mandamos y cómo
interpretamos lo que responde.
"""
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import stripe
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

from . import servicio
from .models import CuentaStripe
from .servicio import PagoRechazado

CLAVES = {"STRIPE_SECRET_KEY": "sk_test_x", "STRIPE_PUBLISHABLE_KEY": "pk_test_x"}


def _intento(status, amount=1000, currency="pyg"):
    return SimpleNamespace(id="pi_123", status=status, client_secret="pi_123_secret",
                           amount=amount, currency=currency)


@override_settings(**CLAVES)
class ServicioStripeTest(TestCase):
    def setUp(self):
        self.usuario = get_user_model().objects.create_user("clara", email="clara@example.com")
        self.cliente_stripe = MagicMock()
        self.cliente_stripe.v1.customers.create.return_value = SimpleNamespace(id="cus_1")
        parche = patch("pagos.servicio.stripe.StripeClient", return_value=self.cliente_stripe)
        parche.start()
        self.addCleanup(parche.stop)
        self.medio = SimpleNamespace(stripe_payment_method_id="pm_1", usuario=self.usuario)

    def test_monto_en_unidad_minima(self):
        self.assertEqual(servicio.monto_en_unidad_minima("710030", "PYG"), 710030)
        self.assertEqual(servicio.monto_en_unidad_minima("100.5", "USD"), 10050)

    def test_customer_se_crea_una_sola_vez(self):
        self.assertEqual(servicio.customer_de(self.usuario), "cus_1")
        self.assertEqual(servicio.customer_de(self.usuario), "cus_1")
        self.cliente_stripe.v1.customers.create.assert_called_once()
        self.assertEqual(CuentaStripe.objects.get().customer_id, "cus_1")

    def test_cobro_aprobado(self):
        self.cliente_stripe.v1.payment_intents.create.return_value = _intento("succeeded")
        cobro = servicio.cobrar(self.medio, 710030, "PYG", "desc", {"transaccion_id": 1})
        self.assertEqual((cobro.id, cobro.estado), ("pi_123", "aprobado"))
        params = self.cliente_stripe.v1.payment_intents.create.call_args.kwargs["params"]
        self.assertEqual(params["amount"], 710030)
        self.assertEqual(params["currency"], "pyg")
        self.assertEqual(params["payment_method"], "pm_1")
        self.assertTrue(params["confirm"])

    def test_cobro_con_3d_secure(self):
        self.cliente_stripe.v1.payment_intents.create.return_value = _intento("requires_action")
        cobro = servicio.cobrar(self.medio, 100, "USD", "desc")
        self.assertEqual(cobro.estado, "requiere_accion")
        self.assertEqual(cobro.client_secret, "pi_123_secret")

    def test_tarjeta_rechazada(self):
        self.cliente_stripe.v1.payment_intents.create.side_effect = stripe.CardError(
            "declined", None, "card_declined"
        )
        with self.assertRaisesMessage(PagoRechazado, "rechazada"):
            servicio.cobrar(self.medio, 100, "USD", "desc")

    def test_verificar_rechaza_monto_distinto(self):
        self.cliente_stripe.v1.payment_intents.retrieve.return_value = _intento("succeeded", amount=1)
        with self.assertRaisesMessage(PagoRechazado, "no corresponde"):
            servicio.verificar_cobro("pi_123", 1000, "PYG")

    def test_verificar_aprobado(self):
        self.cliente_stripe.v1.payment_intents.retrieve.return_value = _intento("succeeded")
        self.assertEqual(servicio.verificar_cobro("pi_123", 1000, "PYG").estado, "aprobado")

    def test_tarjeta_registrada_de_otro_customer_se_rechaza(self):
        self.cliente_stripe.v1.setup_intents.retrieve.return_value = SimpleNamespace(
            customer="cus_ajeno", status="succeeded", payment_method="pm_1"
        )
        with self.assertRaises(PagoRechazado):
            servicio.tarjeta_registrada(self.usuario, "seti_1")

    def test_tarjeta_registrada(self):
        self.cliente_stripe.v1.setup_intents.retrieve.return_value = SimpleNamespace(
            customer="cus_1", status="succeeded", payment_method="pm_1"
        )
        self.cliente_stripe.v1.payment_methods.retrieve.return_value = SimpleNamespace(
            id="pm_1", card=SimpleNamespace(brand="visa", last4="4242", exp_month=4, exp_year=2031)
        )
        self.assertEqual(servicio.tarjeta_registrada(self.usuario, "seti_1"), {
            "payment_method_id": "pm_1", "marca": "Visa", "ultimos4": "4242", "vencimiento": "04/31",
        })


@override_settings(STRIPE_SECRET_KEY="", STRIPE_PUBLISHABLE_KEY="")
class SinClavesTest(TestCase):
    def test_sin_claves_no_cobra(self):
        medio = SimpleNamespace(stripe_payment_method_id="pm_1", usuario=None)
        with self.assertRaisesMessage(PagoRechazado, "no están configurados"):
            servicio.cobrar(medio, 100, "USD", "desc")
