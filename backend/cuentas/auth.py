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
    """Sincroniza el usuario local de Django y sus permisos a partir de los claims de Keycloak."""

    def create_user(self, claims):
        """Crea un nuevo usuario en Django y asigna sus datos iniciales desde Keycloak.

        Args:
            claims (dict): Diccionario con las notificaciones/claims retornadas por el IdP.

        Returns:
            User: Objeto de usuario creado y actualizado.
        """
        usuario = super().create_user(claims)
        self._sincronizar(usuario, claims)
        return usuario

    def update_user(self, usuario, claims):
        """Actualiza la información de un usuario existente tras cada inicio de sesión.

        Args:
            usuario (User): Instancia actual del usuario en la base de datos de Django.
            claims (dict): Diccionario con las notificaciones/claims retornadas por el IdP.

        Returns:
            User: Objeto de usuario con la información de sesión sincronizada.
        """
        usuario = super().update_user(usuario, claims)
        self._sincronizar(usuario, claims)
        return usuario

    def _sincronizar(self, usuario, claims):
        """Actualiza el perfil del usuario (nombre, apellido, is_staff) y sus grupos.

        Sobrescribe los grupos asignados en Django según la lista de roles que provee
        Keycloak en la clave 'roles'.

        Args:
            usuario (User): Instancia del usuario que se va a modificar.
            claims (dict): Claim plano enviado por Keycloak con los atributos y roles del usuario.
        """
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
