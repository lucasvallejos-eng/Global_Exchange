import json
import time
from unittest.mock import patch

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from .models import MedioPago
from django.contrib.auth.models import Group
from django.test import TestCase, override_settings

User = get_user_model()


class MedioPagoModelTest(TestCase):
    def setUp(self):
        self.usuario = User.objects.create_user(
            username="cliente1",
            email="cliente1@example.com"
        )

    def test_creacion_medio_pago_exitoso(self):
        """Verifica que el medio de pago se cree correctamente asignado al usuario."""
        medio = MedioPago.objects.create(
            usuario=self.usuario,
            tipo="TARJETA_CREDITO",
            alias="Mi Tarjeta Itaú",
            numero_cuenta_o_tarjeta="****1234",
            banco_o_proveedor="Itaú"
        )
        self.assertEqual(medio.usuario, self.usuario)
        self.assertEqual(medio.alias, "Mi Tarjeta Itaú")
        self.assertTrue(medio.activo)

    def test_borrado_logico_medio_pago(self):
        """Verifica que el borrado cambie activa a False sin eliminarlo de la BD."""
        medio = MedioPago.objects.create(
            usuario=self.usuario,
            tipo="CUENTA_BANCARIA",
            alias="Cuenta Cajas",
            numero_cuenta_o_tarjeta="123456789"
        )
        medio.activo = False
        medio.save()

        self.assertEqual(MedioPago.objects.count(), 1)
        self.assertFalse(MedioPago.objects.get(id=medio.id).activo)


class MedioPagoViewsTest(TestCase):
    def setUp(self):
        self.cliente_a = User.objects.create_user(username="cliente_a")
        self.cliente_b = User.objects.create_user(username="cliente_b")

        self.medio_a = MedioPago.objects.create(
            usuario=self.cliente_a,
            tipo="TARJETA_DEBITO",
            alias="Tarjeta Cliente A",
            numero_cuenta_o_tarjeta="1111"
        )

    def test_acceso_protegido_sin_autenticacion(self):
        """Verifica que usuarios no autenticados no puedan listar ni editar."""
        response = self.client.get(reverse('listar_medios_pago'))
        self.assertNotEqual(response.status_code, 200)

    def test_aislamiento_entre_clientes(self):
        """Garantiza que un cliente no pueda editar un medio de pago que pertenece a otro."""
        self.client.force_login(self.cliente_b)
        
        # El cliente B intenta editar la tarjeta del cliente A
        response = self.client.post(
            reverse('editar_medio_pago', kwargs={'pk': self.medio_a.pk}),
            {'alias': 'Intento Hackeo'}
        )
        self.assertEqual(response.status_code, 403)
        
        # Confirmar que el alias no cambió en la base de datos
        self.medio_a.refresh_from_db()
        self.assertEqual(self.medio_a.alias, "Tarjeta Cliente A")

@override_settings(MIDDLEWARE=[
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
])

class MedioPagoAvanceViewsTest(TestCase):
    def setUp(self):
        self.cliente_1 = User.objects.create_user(username="cliente_1")
        self.cliente_2 = User.objects.create_user(username="cliente_2")

        grupo_cliente, _ = Group.objects.get_or_create(name="cliente")
        self.cliente_1.groups.add(grupo_cliente)
        self.cliente_2.groups.add(grupo_cliente)

        # Medio de pago activo de cliente 1
        self.medio_activo = MedioPago.objects.create(
            usuario=self.cliente_1,
            tipo="TARJETA_CREDITO",
            alias="Tarjeta Cliente 1",
            numero_cuenta_o_tarjeta="1111",
            activo=True
        )

        # Medio de pago inactivo de cliente 1
        self.medio_inactivo = MedioPago.objects.create(
            usuario=self.cliente_1,
            tipo="CUENTA_BANCARIA",
            alias="Tarjeta Inactiva",
            numero_cuenta_o_tarjeta="2222",
            activo=False
        )

        # Medio de pago de cliente 2
        self.medio_cliente_2 = MedioPago.objects.create(
            usuario=self.cliente_2,
            tipo="TARJETA_DEBITO",
            alias="Tarjeta Cliente 2",
            numero_cuenta_o_tarjeta="3333",
            activo=True
        )




    def test_crear_medio_pago_asigna_usuario_actual(self):
        """Verifica que la vista asigne automáticamente el usuario autenticado al crear."""
        self.client.force_login(self.cliente_1)
        data = {
            'tipo': 'BILLETERA_DIGITAL',
            'alias': 'Mi Tigo Money',
            'numero': '0981123456',
            'banco': 'Tigo'
        }
        response = self.client.post(reverse('crear_medio_pago'), data)
        self.assertEqual(response.status_code, 302) 

        nuevo_medio = MedioPago.objects.get(alias='Mi Tigo Money')
        self.assertEqual(nuevo_medio.usuario, self.cliente_1)

    def test_lista_solo_muestra_medios_activos_del_usuario(self):
        """Verifica que el cliente no vea registros inactivos ni de otros clientes."""
        self.client.force_login(self.cliente_1)
        response = self.client.get(reverse('listar_medios_pago'))

        print("Redirigido a:", response.get('Location'))

        self.assertEqual(response.status_code, 200)
        medios_en_contexto = response.context['medios']

        self.assertIn(self.medio_activo, medios_en_contexto)
        self.assertNotIn(self.medio_inactivo, medios_en_contexto)
        self.assertNotIn(self.medio_cliente_2, medios_en_contexto)

    def test_vista_eliminar_aplica_soft_delete(self):
        """Verifica que llamar a la vista de eliminación deshabilite el medio de pago."""
        self.client.force_login(self.cliente_1)
        response = self.client.post(reverse('eliminar_medio_pago', kwargs={'pk': self.medio_activo.pk}))
        
        self.assertEqual(response.status_code, 302)
        self.medio_activo.refresh_from_db()
        self.assertFalse(self.medio_activo.activo)

class MedioPagoVisibilidadApiTest(TestCase):
    """Qué medios de pago ve cada rol en la API JSON."""

    def setUp(self):
        dueno = User.objects.create_user(username="dueno")
        self.activo = MedioPago.objects.create(usuario=dueno, alias="Activo", activo=True)
        self.inactivo = MedioPago.objects.create(usuario=dueno, alias="Inactivo", activo=False)

    def _iniciar_sesion(self, rol):
        usuario = User.objects.create_user(username=f"usuario_{rol}")
        usuario.groups.add(Group.objects.get_or_create(name=rol)[0])
        self.client.force_login(usuario)
        session = self.client.session
        session["oidc_id_token_expiration"] = time.time() + 3600
        session.save()

    def _ids_listados(self):
        respuesta = self.client.get(reverse("api_medios_lista"))
        self.assertEqual(respuesta.status_code, 200)
        return {medio["id"] for medio in respuesta.json()["medios"]}

    def test_administrador_ve_inactivos(self):
        self._iniciar_sesion("administrador")
        self.assertEqual(self._ids_listados(), {self.activo.pk, self.inactivo.pk})

    def test_administrador_reactiva_un_inactivo(self):
        self._iniciar_sesion("administrador")
        respuesta = self.client.patch(
            reverse("api_medios_detalle", args=[self.inactivo.pk]),
            data=json.dumps({"activo": True}),
            content_type="application/json",
        )
        self.assertEqual(respuesta.status_code, 200)
        self.inactivo.refresh_from_db()
        self.assertTrue(self.inactivo.activo)

    def test_cajero_solo_ve_activos(self):
        self._iniciar_sesion("cajero")
        self.assertEqual(self._ids_listados(), {self.activo.pk})


class TarjetasStripeApiTest(TestCase):
    """Alta de tarjetas con Stripe (Stripe simulado)."""

    def setUp(self):
        self.usuario = User.objects.create_user(username="clara")
        self.usuario.groups.add(Group.objects.get_or_create(name="cliente")[0])
        self.client.force_login(self.usuario)
        session = self.client.session
        session["oidc_id_token_expiration"] = time.time() + 3600
        session.save()

    def _post(self, nombre, datos):
        return self.client.post(reverse(nombre), data=json.dumps(datos), content_type="application/json")

    def test_no_se_aceptan_numeros_de_tarjeta_en_crudo(self):
        respuesta = self._post("api_medios_lista", {
            "tipo": "TARJETA_CREDITO", "alias": "Visa", "numeroTarjeta": "4242424242424242", "codigoSeguridad": "123",
        })
        self.assertEqual(respuesta.status_code, 400)
        self.assertFalse(MedioPago.objects.exists())

    def test_preparar_devuelve_client_secret(self):
        with patch("pagos.servicio.preparar_tarjeta", return_value="seti_1_secret"):
            respuesta = self._post("api_tarjetas_preparar", {})
        self.assertEqual(respuesta.json(), {"clientSecret": "seti_1_secret"})

    def test_registrar_guarda_solo_datos_no_sensibles(self):
        tarjeta = {"payment_method_id": "pm_1", "marca": "Visa", "ultimos4": "4242", "vencimiento": "04/31"}
        with patch("pagos.servicio.tarjeta_registrada", return_value=tarjeta) as leer:
            respuesta = self._post("api_tarjetas_registrar", {
                "setupIntentId": "seti_1", "tipo": "TARJETA_DEBITO", "alias": "Mi débito",
            })
        self.assertEqual(respuesta.status_code, 201)
        leer.assert_called_once_with(self.usuario, "seti_1")
        self.assertEqual(respuesta.json()["tarjeta"], {"marca": "Visa", "ultimos4": "4242", "vencimiento": "04/31"})
        medio = MedioPago.objects.get()
        self.assertEqual((medio.tipo, medio.stripe_payment_method_id), ("TARJETA_DEBITO", "pm_1"))

    def test_borrar_desvincula_en_stripe(self):
        medio = MedioPago.objects.create(usuario=self.usuario, tipo="TARJETA_CREDITO", alias="Visa",
                                         stripe_payment_method_id="pm_1")
        with patch("pagos.servicio.desvincular_tarjeta") as desvincular:
            respuesta = self.client.delete(reverse("api_medios_detalle", args=[medio.pk]))
        self.assertEqual(respuesta.status_code, 204)
        desvincular.assert_called_once_with("pm_1")

    def test_borrar_una_tarjeta_usada_en_caja_la_desactiva(self):
        from caja.models import AperturaCaja, VentaCaja
        from clientes.models import Cliente
        from monedas.models import Moneda

        medio = MedioPago.objects.create(usuario=self.usuario, tipo="TARJETA_CREDITO", alias="Visa",
                                         stripe_payment_method_id="pm_1")
        VentaCaja.objects.create(
            apertura=AperturaCaja.objects.create(cajero_id="c1"), cajero_id="c1",
            cliente=Cliente.objects.create(nombre="C", tipo=Cliente.Tipo.FISICA, direccion="x",
                                           cuenta_acreditar="1", correo="c@example.com"),
            moneda=Moneda.objects.create(codigo="USD", nombre="Dólar", simbolo="$"),
            monto_divisa=1, cotizacion_aplicada=1, monto_local_total=1, medio_pago=medio,
        )
        with patch("pagos.servicio.desvincular_tarjeta") as desvincular:
            respuesta = self.client.delete(reverse("api_medios_detalle", args=[medio.pk]))
        self.assertEqual(respuesta.status_code, 204)
        desvincular.assert_called_once_with("pm_1")
        medio.refresh_from_db()
        self.assertFalse(medio.activo)
