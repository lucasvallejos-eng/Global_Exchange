"""Vistas de autenticación de Global Exchange."""
from urllib.parse import urlencode

from django.conf import settings
from django.contrib.auth import logout as cerrar_sesion_django
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.middleware.csrf import get_token
from django.shortcuts import redirect, render
from django.urls import reverse


def portada(request):
    """
    Punto de entrada del backend (http://localhost:8000/).

    Para alivianar el flujo NO mostramos una pantalla intermedia:
    - Si no estás autenticado, va directo al login de Keycloak.
    - Si ya lo estás, te manda a la maqueta.
    """
    if request.user.is_authenticated:
        return redirect(settings.MAQUETA_URL)
    return redirect("oidc_authentication_init")


def api_me(request):
    """
    Devuelve quién es el usuario actual y sus roles (leídos de la sesión, que a
    su vez viene del token de Keycloak). La maqueta llama a esto para saber si
    mostrar el dashboard o mandar al login.
    """
    if not request.user.is_authenticated:
        return JsonResponse({"authenticated": False}, status=401)

    # Garantiza que la cookie csrftoken quede seteada desde el primer chequeo
    # de sesión, para que la maqueta la pueda leer y mandarla en las
    # mutaciones (POST/PATCH/DELETE) de /api/clientes/.
    get_token(request)

    roles = list(request.user.groups.values_list("name", flat=True))
    return JsonResponse(
        {
            "authenticated": True,
            "username": request.user.username,
            "nombre": request.user.get_full_name() or request.user.username,
            "email": request.user.email,
            "roles": roles,
        }
    )


def cerrar_sesion(request):
    """
    Cierra la sesión de Django y, además, la sesión SSO de Keycloak
    (RP-Initiated Logout) para que un login posterior vuelva a pedir
    usuario/contraseña en vez de reautenticar en silencio.

    Usamos una vista propia (acepta GET) en vez de la de mozilla-django-oidc,
    que solo acepta POST.
    """
    id_token = request.session.get("oidc_id_token")
    cerrar_sesion_django(request)

    if not id_token:
        # No había id_token guardado (p.ej. login vía ModelBackend) -> solo
        # queda cerrar la sesión de Django.
        return redirect("sesion_cerrada")

    post_logout_redirect_uri = request.build_absolute_uri(reverse("sesion_cerrada"))
    query = urlencode(
        {
            "id_token_hint": id_token,
            "post_logout_redirect_uri": post_logout_redirect_uri,
        }
    )
    return redirect(f"{settings.OIDC_OP_LOGOUT_ENDPOINT}?{query}")


def sesion_cerrada(request):
    """Página simple tras cerrar sesión (evita un bucle de re-login)."""
    return render(request, "sesion_cerrada.html")


@login_required
def inicio(request):
    """Página de inicio del backend (útil para depurar sin la maqueta)."""
    roles = list(request.user.groups.values_list("name", flat=True))
    return render(request, "inicio.html", {"roles": roles})
