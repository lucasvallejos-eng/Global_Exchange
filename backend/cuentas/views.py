"""Vistas de autenticación de Global Exchange."""
from django.conf import settings
from django.contrib.auth import logout as cerrar_sesion_django
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import redirect, render


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
    Cierra la sesión de Django y manda a la página de "sesión cerrada".

    Usamos una vista propia (acepta GET) en vez de la de mozilla-django-oidc,
    que solo acepta POST. Nota: cierra la sesión del backend; la sesión SSO de
    Keycloak sigue viva (para cerrarla también haría falta el logout OIDC).
    """
    cerrar_sesion_django(request)
    return redirect("sesion_cerrada")


def sesion_cerrada(request):
    """Página simple tras cerrar sesión (evita un bucle de re-login)."""
    return render(request, "sesion_cerrada.html")


@login_required
def inicio(request):
    """Página de inicio del backend (útil para depurar sin la maqueta)."""
    roles = list(request.user.groups.values_list("name", flat=True))
    return render(request, "inicio.html", {"roles": roles})
