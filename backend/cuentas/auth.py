"""
Backend de autenticación OIDC para Keycloak.

Extiende el backend de mozilla-django-oidc para, cada vez que un usuario entra,
sincronizar sus datos y sus **roles** de Keycloak con Django.

Los roles llegan en el claim plano `roles` del token (lo produce el mapper
"User Client Role" del client global-exchange-web). Acá los mapeamos a **grupos
de Django**, así el control de acceso del lado del servidor usa el sistema de
permisos estándar de Django.
"""
from django.contrib.auth.models import Group
from mozilla_django_oidc.auth import OIDCAuthenticationBackend


class BackendOIDCKeycloak(OIDCAuthenticationBackend):
    """Crea/actualiza el usuario local a partir de los claims de Keycloak."""

    def create_user(self, claims):
        usuario = super().create_user(claims)
        self._sincronizar(usuario, claims)
        return usuario

    def update_user(self, usuario, claims):
        usuario = super().update_user(usuario, claims)
        self._sincronizar(usuario, claims)
        return usuario

    def _sincronizar(self, usuario, claims):
        # Datos básicos del perfil.
        usuario.first_name = claims.get("given_name", "") or ""
        usuario.last_name = claims.get("family_name", "") or ""

        # Roles de Keycloak (claim plano "roles").
        roles = claims.get("roles", []) or []

        # El administrador de Keycloak puede entrar al /admin de Django.
        usuario.is_staff = "administrador" in roles

        usuario.save()

        # Roles -> grupos de Django (se reescriben en cada login: Keycloak manda).
        usuario.groups.clear()
        for nombre_rol in roles:
            grupo, _ = Group.objects.get_or_create(name=nombre_rol)
            usuario.groups.add(grupo)
