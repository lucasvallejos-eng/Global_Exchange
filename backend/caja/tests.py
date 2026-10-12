import json
import time
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from monedas.models import Denominacion, Moneda
from clientes.models import Cliente
from comisiones.models import SegmentoCliente
from cotizaciones.models import Cotizacion
from medios_pago.models import MedioPago

from .models import AperturaCaja, CompraCaja


class CajaApiTests(TestCase):
    def setUp(self):
        self.usuario = get_user_model().objects.create_user("cajero")
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
