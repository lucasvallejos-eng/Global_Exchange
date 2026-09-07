"""
Tests del flujo básico: crear usuario, iniciar sesión, crear cliente y
asociar un usuario a ese cliente.

El login real pasa por Keycloak (OIDC): no hay vista de usuario/contraseña
local. Por eso "iniciar sesión" se simula con `force_login`, dejando la
sesión tal como quedaría después de que `cuentas.auth.BackendOIDCKeycloak`
sincronizara el usuario y sus roles (grupos de Django).
"""
import json
import time

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse

from clientes.models import Cliente

User = get_user_model()


class FlujoBasicoTests(TestCase):
    def setUp(self):
        self.grupo_admin, _ = Group.objects.get_or_create(name="administrador")

    def _crear_admin(self, username="admin1"):
        admin = User.objects.create_user(username=username, email=f"{username}@example.com")
        admin.groups.add(self.grupo_admin)
        return admin

    def _iniciar_sesion(self, usuario):
        """force_login + token OIDC "vigente" para que SessionRefresh no redirija."""
        self.client.force_login(usuario)
        session = self.client.session
        session["oidc_id_token_expiration"] = time.time() + 3600
        session.save()

    def _datos_cliente(self, **overrides):
        datos = {
            "nombre": "ACME S.A.",
            "tipo": Cliente.Tipo.JURIDICA,
            "direccion": "Av. Siempre Viva 123",
            "cuentaAcreditar": "1234567890",
            "correo": "contacto@acme.com",
        }
        datos.update(overrides)
        return datos

    def test_crear_usuario(self):
        usuario = User.objects.create_user(
            username="jperez",
            email="jperez@example.com",
            first_name="Juan",
            last_name="Perez",
        )
        self.assertTrue(User.objects.filter(username="jperez").exists())
        self.assertEqual(usuario.get_full_name(), "Juan Perez")

    def test_iniciar_sesion(self):
        usuario = self._crear_admin("jperez")

        self._iniciar_sesion(usuario)
        respuesta = self.client.get(reverse("api_me"))

        self.assertEqual(respuesta.status_code, 200)
        datos = respuesta.json()
        self.assertTrue(datos["authenticated"])
        self.assertEqual(datos["username"], "jperez")
        self.assertIn("administrador", datos["roles"])

    def test_iniciar_sesion_sin_autenticar(self):
        respuesta = self.client.get(reverse("api_me"))
        self.assertEqual(respuesta.status_code, 401)

    def test_crear_cliente(self):
        self._iniciar_sesion(self._crear_admin())

        respuesta = self.client.post(
            reverse("clientes_lista"),
            data=json.dumps(self._datos_cliente()),
            content_type="application/json",
        )

        self.assertEqual(respuesta.status_code, 201)
        self.assertTrue(Cliente.objects.filter(nombre="ACME S.A.").exists())

    def test_agregar_usuario_a_cliente(self):
        self._iniciar_sesion(self._crear_admin())
        usuario = User.objects.create_user(username="jperez", email="jperez@example.com")
        cliente = Cliente.objects.create(**{
            "nombre": self._datos_cliente()["nombre"],
            "tipo": self._datos_cliente()["tipo"],
            "direccion": self._datos_cliente()["direccion"],
            "cuenta_acreditar": self._datos_cliente()["cuentaAcreditar"],
            "correo": self._datos_cliente()["correo"],
        })

        respuesta = self.client.patch(
            reverse("clientes_detalle", args=[cliente.id]),
            data=json.dumps({"usuarios": [usuario.id]}),
            content_type="application/json",
        )

        self.assertEqual(respuesta.status_code, 200)
        cliente.refresh_from_db()
        self.assertIn(usuario, cliente.usuarios.all())

    def test_flujo_completo(self):
        """Crear usuario -> iniciar sesión -> crear cliente -> agregar usuario al cliente."""
        usuario = User.objects.create_user(username="jperez", email="jperez@example.com")
        admin = self._crear_admin("admin1")

        self._iniciar_sesion(admin)
        self.assertTrue(self.client.get(reverse("api_me")).json()["authenticated"])

        respuesta = self.client.post(
            reverse("clientes_lista"),
            data=json.dumps(self._datos_cliente()),
            content_type="application/json",
        )
        cliente_id = respuesta.json()["id"]

        respuesta = self.client.patch(
            reverse("clientes_detalle", args=[cliente_id]),
            data=json.dumps({"usuarios": [usuario.id]}),
            content_type="application/json",
        )

        self.assertEqual(respuesta.status_code, 200)
        self.assertIn(usuario.id, respuesta.json()["usuarios"])
