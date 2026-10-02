"""
Configuración de Django para el backend de Global Exchange.

Contiene SOLO lo necesario para la integración con Keycloak (login OIDC y
lectura de roles). El resto del sistema (modelos de clientes, transacciones,
etc.) lo agregan las demás historias del equipo.
"""
from pathlib import Path
import os

from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

# Carga las variables desde backend/.env (ver .env.example).
load_dotenv(BASE_DIR / ".env")


def _bool(valor: str, por_defecto: bool = False) -> bool:
    if valor is None:
        return por_defecto
    return valor.strip().lower() in {"1", "true", "yes", "on", "si", "sí"}


# --- Básico ------------------------------------------------------------------
CLAVE_DE_DESARROLLO = "clave-insegura-solo-para-desarrollo"
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", CLAVE_DE_DESARROLLO)
DEBUG = _bool(os.environ.get("DJANGO_DEBUG"), True)

# En producción (DEBUG apagado) la clave de desarrollo no sirve: con ella
# cualquiera puede falsificar cookies de sesión. Mejor que no arranque a que
# arranque inseguro sin que nadie se entere.
if not DEBUG and SECRET_KEY == CLAVE_DE_DESARROLLO:
    raise ImproperlyConfigured(
        "Con DJANGO_DEBUG apagado hay que definir DJANGO_SECRET_KEY "
        "(ver .env.prod.example)."
    )

ALLOWED_HOSTS = [
    h.strip()
    for h in os.environ.get("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")
    if h.strip()
]

# --- Aplicaciones ------------------------------------------------------------
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Integración OIDC con Keycloak
    "mozilla_django_oidc",
    # App propia de autenticación / roles
    "cuentas",
    # Gestión de Clientes (empresas) y su relación con usuarios
    "clientes",
    "monedas",
    "cotizaciones",
    "medios_pago",
    # Configuración de porcentajes de comisión por segmento de cliente
    "comisiones",
    # Consulta de tasas y simulador de conversión (solo lectura)
    "tasas",
    "operaciones",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    # CORS para que la maqueta (localhost:8443) consuma /api/ con la cookie.
    "cuentas.middleware.CorsMaquetaMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    # Renueva el token de Keycloak durante la sesión.
    "mozilla_django_oidc.middleware.SessionRefresh",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

# En producción Django no sirve los archivos estáticos (los estilos del panel
# /admin/); WhiteNoise lo hace sin agregar otro servidor. Solo se activa con
# DEBUG apagado, así que en desarrollo no hace falta tenerlo instalado (está
# en requirements-produccion.txt, no en requirements.txt).
if not DEBUG:
    MIDDLEWARE.insert(1, "whitenoise.middleware.WhiteNoiseMiddleware")

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# --- Base de datos -----------------------------------------------------------
# SQLite para arrancar. El esquema relacional real (usuarios/clientes) lo define
# la historia de base de datos del equipo; se puede cambiar a PostgreSQL después.
# En producción el archivo va a un volumen de Docker (DJANGO_DB_PATH), para
# que los datos no se pierdan al reconstruir el contenedor.
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": os.environ.get("DJANGO_DB_PATH", BASE_DIR / "db.sqlite3"),
    }
}

# --- Autenticación: backends -------------------------------------------------
# Primero el de Keycloak; el ModelBackend queda para el superusuario de /admin.
AUTHENTICATION_BACKENDS = [
    "cuentas.auth.BackendOIDCKeycloak",
    "django.contrib.auth.backends.ModelBackend",
]

# --- Configuración OIDC (mozilla-django-oidc + Keycloak) ---------------------
KEYCLOAK_ISSUER = os.environ.get(
    "KEYCLOAK_ISSUER", "http://localhost:8080/realms/GlobalExchange"
)

OIDC_RP_CLIENT_ID = os.environ.get("KEYCLOAK_WEB_CLIENT_ID", "global-exchange-web")
OIDC_RP_CLIENT_SECRET = os.environ.get("KEYCLOAK_WEB_CLIENT_SECRET", "")

# RNF01 de la ERS: firma RS256.
OIDC_RP_SIGN_ALGO = "RS256"
OIDC_RP_SCOPES = "openid email profile"

# Dos direcciones para el mismo Keycloak. El navegador entra por la pública
# (login y logout). Django le habla directo para canjear el código por el
# token, y dentro de Docker "localhost" es el propio contenedor: por eso puede
# usar otra dirección (KEYCLOAK_ISSUER_INTERNO, p. ej. http://keycloak:8080).
# Si no se define, es la misma: así funciona hoy en desarrollo.
KEYCLOAK_ISSUER_INTERNO = os.environ.get("KEYCLOAK_ISSUER_INTERNO", KEYCLOAK_ISSUER)

# Endpoints estándar de Keycloak, derivados del issuer.
OIDC_OP_AUTHORIZATION_ENDPOINT = f"{KEYCLOAK_ISSUER}/protocol/openid-connect/auth"
OIDC_OP_LOGOUT_ENDPOINT = f"{KEYCLOAK_ISSUER}/protocol/openid-connect/logout"
OIDC_OP_TOKEN_ENDPOINT = f"{KEYCLOAK_ISSUER_INTERNO}/protocol/openid-connect/token"
OIDC_OP_USER_ENDPOINT = f"{KEYCLOAK_ISSUER_INTERNO}/protocol/openid-connect/userinfo"
OIDC_OP_JWKS_ENDPOINT = f"{KEYCLOAK_ISSUER_INTERNO}/protocol/openid-connect/certs"

# Guarda el id_token en la sesión para poder mandarlo como id_token_hint al
# cerrar sesión en Keycloak (RP-Initiated Logout) y que no quede la sesión SSO
# viva (ver cuentas.views.cerrar_sesion).
OIDC_STORE_ID_TOKEN = True

# URL de la maqueta (frontend React). Tras el login, el usuario aterriza ahí.
MAQUETA_URL = os.environ.get("MAQUETA_URL", "http://localhost:8443/")

# A dónde va el usuario después de entrar / salir.
LOGIN_REDIRECT_URL = MAQUETA_URL          # tras loguear -> maqueta
LOGOUT_REDIRECT_URL = "portada"           # tras salir -> "portada" manda derecho al login
LOGIN_URL = "oidc_authentication_init"

# --- CORS / CSRF para la maqueta (React en otro puerto) ----------------------
# La maqueta necesita poder hacer POST/PATCH/DELETE a /api/clientes/ con la
# cookie de sesión, y Django exige CSRF en esas mutaciones aunque la sesión
# venga de OIDC. Maqueta y backend comparten host (localhost), solo cambia el
# puerto, así que son "same site" y SameSite=Lax alcanza.
# Sin la barra final: Django compara estas entradas tal cual contra la cabecera
# `Origin` que manda el navegador, y esa cabecera nunca la lleva. Como
# MAQUETA_URL sí termina en "/", sin el rstrip la comparación nunca coincidía y
# guardar un cliente desde la maqueta devolvía 403 (los GET no se veían
# afectados porque no pasan por la validación CSRF).
CSRF_TRUSTED_ORIGINS = [
    origen.strip().rstrip("/")
    for origen in os.environ.get("DJANGO_CSRF_TRUSTED_ORIGINS", MAQUETA_URL).split(",")
    if origen.strip()
]
CSRF_COOKIE_HTTPONLY = False  # la maqueta necesita leer la cookie csrftoken por JS
CSRF_COOKIE_SAMESITE = "Lax"

# Si el servidor de producción tiene HTTPS (normalmente un proxy adelante que
# termina el TLS), las cookies viajan solo cifradas. No se activa por defecto:
# servido por HTTP plano, las cookies "seguras" no se mandarían y nadie podría
# iniciar sesión.
if _bool(os.environ.get("DJANGO_HTTPS")):
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# --- Internacionalización ----------------------------------------------------
LANGUAGE_CODE = "es"
TIME_ZONE = "America/Asuncion"
USE_I18N = True
USE_TZ = True

# --- Estáticos ---------------------------------------------------------------
STATIC_URL = "static/"
# Adonde junta los estáticos "collectstatic" para que WhiteNoise los sirva.
STATIC_ROOT = os.environ.get("DJANGO_STATIC_ROOT", BASE_DIR / "staticfiles")

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
