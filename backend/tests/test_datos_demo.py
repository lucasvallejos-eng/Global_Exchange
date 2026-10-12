"""
Tests de los datos de ejemplo (``fixtures/demo.json``).

Es lo que cargan los scripts de despliegue (``levantar_todo.py`` y
``publicar.py --demo``). Tiene que dejar el sistema listo para operar sin
configurar nada a mano, y poder cargarse más de una vez sin duplicar.
"""
import json
import time

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from clientes.models import Cliente
from cuentas.auth import BackendOIDCKeycloak

User = get_user_model()
FIXTURE = str(settings.BASE_DIR / "fixtures" / "demo.json")


class DatosDemoTests(TestCase):
    def setUp(self):
        call_command("loaddata", FIXTURE, verbosity=0)

    def test_trae_un_usuario_por_rol(self):
        roles = {u.username: sorted(g.name for g in u.groups.all()) for u in User.objects.all()}
        self.assertEqual(roles, {
            "admin.test": ["administrador", "analista_cambiario", "cajero", "cliente"],
            "analista.test": ["analista_cambiario", "cliente"],
            "cajero.test": ["cajero", "cliente"],
            "cliente.test": ["cliente"],
        })

    def test_el_login_de_keycloak_encuentra_al_usuario_cargado(self):
        # Keycloak identifica por correo: tiene que dar con el usuario del
        # fixture (el que ya está asociado a un cliente) y no crear otro.
        encontrados = BackendOIDCKeycloak().filter_users_by_claims(
            {"email": "cliente.test@globalexchange.local"}
        )
        self.assertEqual([u.username for u in encontrados], ["cliente.test"])

    def test_el_cliente_puede_operar_sin_configurar_nada(self):
        usuario = User.objects.get(username="cliente.test")
        self.client.force_login(usuario)
        session = self.client.session
        session["oidc_id_token_expiration"] = time.time() + 3600
        session.save()

        cliente = Cliente.objects.get(nombre="Clara Cliente")
        respuesta = self.client.post(
            reverse("api_operaciones_cotizar"),
            data=json.dumps({"clienteId": cliente.pk, "tipo": "COMPRA", "moneda": "USD", "monto": 100}),
            content_type="application/json",
        )
        self.assertEqual(respuesta.status_code, 200, respuesta.content)
        self.assertEqual(respuesta.json()["totalGuaranies"], 740000)

    def test_cargarlo_dos_veces_no_duplica(self):
        antes = (User.objects.count(), Cliente.objects.count())
        call_command("loaddata", FIXTURE, verbosity=0)
        self.assertEqual((User.objects.count(), Cliente.objects.count()), antes)

    def test_cargarlo_sobre_usuarios_que_ya_existian_no_los_duplica(self):
        # Una base usada: el usuario ya entró y Django le dio otro id.
        User.objects.all().delete()
        User.objects.create_user(username="relleno")
        previo = User.objects.create_user(username="cliente.test", email="cliente.test@globalexchange.local")
        call_command("loaddata", FIXTURE, verbosity=0)
        self.assertEqual(User.objects.filter(username="cliente.test").count(), 1)
        self.assertEqual(
            list(Cliente.objects.get(nombre="Clara Cliente").usuarios.values_list("pk", flat=True)),
            [previo.pk],
        )
