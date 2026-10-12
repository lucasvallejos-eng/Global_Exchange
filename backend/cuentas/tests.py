from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser, Group
from django.contrib.sessions.backends.signed_cookies import SessionStore
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.test import RequestFactory, TestCase

from .decorators import rol_requerido


@rol_requerido("cajero")
def _vista_cajero(request):
    return HttpResponse("ok")


class RolRequeridoTests(TestCase):
    """El decorador decide solo con los grupos de Django (sincronizados en el login)."""

    def _request(self, usuario, roles_en_sesion=None):
        request = RequestFactory().get("/")
        request.user = usuario
        request.session = SessionStore()
        if roles_en_sesion is not None:
            request.session["keycloak_claims"] = {"realm_access": {"roles": roles_en_sesion}}
        return request

    def _usuario(self, *roles):
        usuario = get_user_model().objects.create_user("usuario")
        for rol in roles:
            usuario.groups.add(Group.objects.get_or_create(name=rol)[0])
        return usuario

    def test_permite_con_el_grupo(self):
        respuesta = _vista_cajero(self._request(self._usuario("cajero")))
        self.assertEqual(respuesta.status_code, 200)

    def test_rechaza_sin_el_grupo(self):
        with self.assertRaises(PermissionDenied):
            _vista_cajero(self._request(self._usuario("cliente")))

    def test_rechaza_anonimo(self):
        with self.assertRaises(PermissionDenied):
            _vista_cajero(self._request(AnonymousUser()))

    def test_ignora_roles_guardados_en_la_sesion(self):
        # Si el grupo se quitó en Django, un rol viejo en la sesión no habilita.
        request = self._request(self._usuario("cliente"), roles_en_sesion=["cajero"])
        with self.assertRaises(PermissionDenied):
            _vista_cajero(request)


class SincronizacionRolesTests(TestCase):
    """Los grupos de Django se reescriben con el claim plano "roles" de Keycloak."""

    def setUp(self):
        from .auth import BackendOIDCKeycloak

        self.backend = BackendOIDCKeycloak()
        self.backend.request = RequestFactory().get("/")
        self.backend.request.session = SessionStore()
        self.usuario = get_user_model().objects.create_user("usuario")

    def _grupos(self):
        return set(self.usuario.groups.values_list("name", flat=True))

    def test_roles_del_claim_plano_pasan_a_grupos(self):
        self.backend._sincronizar(self.usuario, {
            "sub": "abc", "roles": ["administrador", "cajero", "analista_cambiario"],
        })
        self.assertEqual(self._grupos(), {"administrador", "cajero", "analista_cambiario"})
        self.assertTrue(self.usuario.is_staff)
        self.assertEqual(self.backend.request.session["keycloak_claims"], {"sub": "abc"})

    def test_ignora_realm_access(self):
        self.backend._sincronizar(self.usuario, {
            "roles": ["cliente"],
            "realm_access": {"roles": ["offline_access", "uma_authorization"]},
        })
        self.assertEqual(self._grupos(), {"cliente"})

    def test_quitar_un_rol_en_keycloak_lo_quita_en_django(self):
        self.backend._sincronizar(self.usuario, {"roles": ["cajero"]})
        self.backend._sincronizar(self.usuario, {"roles": ["cliente"]})
        self.assertEqual(self._grupos(), {"cliente"})

    def test_userinfo_sin_roles_usa_los_del_id_token(self):
        from unittest.mock import patch

        from mozilla_django_oidc.auth import OIDCAuthenticationBackend

        with patch.object(OIDCAuthenticationBackend, "get_userinfo", return_value={"email": "a@b.c"}):
            claims = self.backend.get_userinfo("acceso", "id", {"sub": "abc", "roles": ["cajero"]})
        self.assertEqual(claims["roles"], ["cajero"])
        self.assertEqual(claims["sub"], "abc")
