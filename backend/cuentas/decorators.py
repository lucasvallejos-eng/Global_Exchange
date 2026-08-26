"""
Helper para proteger vistas según el rol de Keycloak.

Uso:

    from cuentas.decorators import rol_requerido

    @rol_requerido("administrador")
    def alta_de_monedas(request):
        ...

    @rol_requerido("cajero", "administrador")
    def apertura_de_caja(request):
        ...

El control de acceso vive en el servidor (nunca se confía en el navegador).
"""
from functools import wraps

from django.core.exceptions import PermissionDenied


def rol_requerido(*roles_permitidos):
    def decorador(vista):
        @wraps(vista)
        def envoltura(request, *args, **kwargs):
            if not request.user.is_authenticated:
                raise PermissionDenied
            roles_usuario = set(
                request.user.groups.values_list("name", flat=True)
            )
            if roles_usuario.intersection(roles_permitidos):
                return vista(request, *args, **kwargs)
            raise PermissionDenied

        return envoltura

    return decorador
