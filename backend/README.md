# Backend — Global Exchange

Backend en **Django** con la integración de **Keycloak** (login OIDC + roles).
Contiene **solo lo de autenticación**; el resto del sistema (clientes,
transacciones, etc.) lo agregan las demás historias del equipo.

> Sirve igual si el equipo termina en la opción **A** (Django con plantillas) o
> **C** (Django como BFF de React): la parte de Keycloak es la misma en ambas.
> Ver [`../docs/decision-arquitectura.md`](../docs/decision-arquitectura.md).

## Qué hace

- `Iniciar sesión` redirige a **Keycloak** (el form lo dibuja Keycloak, RN05).
- Al volver, crea la sesión y salta a la **página de inicio** (`/inicio/`).
- Lee los **roles** del token (claim `roles`) y los mapea a **grupos de Django**.
- `cuentas/decorators.py` → `@rol_requerido("administrador")` para proteger
  vistas por rol **del lado del servidor**.

## Requisitos

- **Python 3.12+** (hoy NO está instalado en la máquina — instalarlo primero:
  https://www.python.org/downloads/ , marcando "Add python.exe to PATH").
- Keycloak corriendo (ver [`../keycloak/README.md`](../keycloak/README.md)) con
  el client `global-exchange-web` y su **secret**.

## Cómo levantarlo

```bash
cd backend

# 1) Entorno virtual
python -m venv .venv
.venv\Scripts\activate        # Windows (PowerShell/CMD)
# source .venv/bin/activate   # Linux/Mac

# 2) Dependencias
pip install -r requirements.txt

# 3) Variables de entorno
copy .env.example .env         # Windows   (cp en Linux/Mac)
#   -> completá KEYCLOAK_WEB_CLIENT_SECRET con el secret del client
#      (Keycloak -> Clients -> global-exchange-web -> Credentials)

# 4) Base de datos local (crea las tablas de sesión/usuarios/grupos)
python manage.py migrate

# 5) Servidor
python manage.py runserver 8000
```

Abrí **http://localhost:8000** → "Iniciar sesión" → te lleva a Keycloak → volvés
a la página de inicio con tus roles.

> El puerto **8000** coincide con la Redirect URI del client
> (`http://localhost:8000/oidc/callback/`). Si cambiás el puerto, actualizá la
> Redirect URI y el Web Origin en Keycloak.

## Estado

Andamiaje **sin verificar en ejecución** todavía (falta instalar Python en la
máquina). Cuando Python esté, corré los pasos de arriba; si algo falla, avisá y
lo depuramos.
