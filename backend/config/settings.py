"""
Configuración de Django para el backend de Global Exchange.

Contiene SOLO lo necesario para la integración con Keycloak (login OIDC y
lectura de roles). El resto del sistema (modelos de clientes, transacciones,
etc.) lo agregan las demás historias del equipo.
"""
from pathlib import Path
import os

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

# Carga las variables desde backend/.env (ver .env.example).
load_dotenv(BASE_DIR / ".env")


def _bool(valor: str, por_defecto: bool = False) -> bool:
    if valor is None:
        return por_defecto
    return valor.strip().lower() in {"1", "true", "yes", "on", "si", "sí"}


# --- Básico ------------------------------------------------------------------
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "clave-insegura-solo-para-desarrollo")
DEBUG = _bool(os.environ.get("DJANGO_DEBUG"), True)
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
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
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

# Endpoints estándar de Keycloak, derivados del issuer.
OIDC_OP_AUTHORIZATION_ENDPOINT = f"{KEYCLOAK_ISSUER}/protocol/openid-connect/auth"
OIDC_OP_TOKEN_ENDPOINT = f"{KEYCLOAK_ISSUER}/protocol/openid-connect/token"
OIDC_OP_USER_ENDPOINT = f"{KEYCLOAK_ISSUER}/protocol/openid-connect/userinfo"
OIDC_OP_JWKS_ENDPOINT = f"{KEYCLOAK_ISSUER}/protocol/openid-connect/certs"

# URL de la maqueta (frontend React). Tras el login, el usuario aterriza ahí.
MAQUETA_URL = os.environ.get("MAQUETA_URL", "http://localhost:8443/")

# A dónde va el usuario después de entrar / salir.
LOGIN_REDIRECT_URL = MAQUETA_URL          # tras loguear -> maqueta
LOGOUT_REDIRECT_URL = "sesion_cerrada"    # tras salir -> página de "sesión cerrada"
LOGIN_URL = "oidc_authentication_init"

# --- Internacionalización ----------------------------------------------------
LANGUAGE_CODE = "es"
TIME_ZONE = "America/Asuncion"
USE_I18N = True
USE_TZ = True

# --- Estáticos ---------------------------------------------------------------
STATIC_URL = "static/"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
