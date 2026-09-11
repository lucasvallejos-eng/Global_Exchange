"""
Helper para proteger vistas según el rol de Keycloak.

Uso (los dos puntos dobles marcan un bloque de código para Sphinx)::

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
    """Decorador para restringir el acceso a vistas según los roles del usuario.

    Verifica que el usuario esté autenticado y posea al menos uno de los roles
    especificados en la firma. Los roles se consultan directamente desde los
    grupos de Django mapeados durante el login.

    Args:
        *roles_permitidos (str): Nombres de los roles autorizados para acceder a la vista.

    Returns:
        function: Función decoradora que envuelve a la vista objetivo.

    Raises:
        PermissionDenied: Si el usuario no está autenticado o no posee
            ninguno de los roles requeridos.
    """
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
