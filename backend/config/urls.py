"""Rutas del backend Global Exchange."""
from django.contrib import admin
from django.urls import path, include

from cuentas import views

urlpatterns = [
    # Panel de administración de Django (superusuario).
    path("admin/", admin.site.urls),
    # Rutas de mozilla-django-oidc: authenticate/, callback/, logout/.
    # El callback queda en /oidc/callback/ → coincide con la Redirect URI
    # configurada en el client global-exchange-web.
    path("oidc/", include("mozilla_django_oidc.urls")),
    # Entrada: manda directo a Keycloak (o a la maqueta si ya hay sesión).
    path("", views.portada, name="portada"),
    # API que consume la maqueta para saber quién está logueado.
    path("api/me/", views.api_me, name="api_me"),
    # API de Clientes (empresas) y usuarios asociables.
    path("api/", include("clientes.urls")),
    # API JSON de monedas: la consume la maqueta (las pantallas de Django
    # siguen en /monedas/, ver monedas/urls.py).
    path("api/", include("monedas.api_urls")),
    path("api/", include("comisiones.api_urls")),
    path("api/", include("medios_pago.api_urls")),
    path("api/", include("cotizaciones.api_urls")),
    # Cerrar sesión (acepta GET) y página tras cerrar sesión.
    path("logout/", views.cerrar_sesion, name="cerrar_sesion"),
    path("sesion-cerrada/", views.sesion_cerrada, name="sesion_cerrada"),
    # Página de inicio del backend (para depurar sin la maqueta).
    path("inicio/", views.inicio, name="inicio"),
    path('monedas/', include('monedas.urls')),
    path('cotizaciones/', include('cotizaciones.urls')),
    path('medios-pago/', include('medios_pago.urls')),
    path('comisiones/', include('comisiones.urls')),
    path('tasas/', include('tasas.urls')),
    path('operaciones/', include('operaciones.urls')),
]
