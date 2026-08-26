# Global Exchange

Casa de cambio digital — proyecto de **Ingeniería de Software 2**, FP-UNA, Equipo 04.

Autenticación y control de roles con **Keycloak**; backend en **Django**; la
interfaz (maqueta) en **React + Vite**.

## Estructura

```
Global_Exchange/
├── frontend/   Maqueta React + Vite (puerto 8443)
├── backend/    Django + integración Keycloak (puerto 8000)   → backend/README.md
├── keycloak/   Docker Compose + realm exportado (puerto 8080) → keycloak/README.md
└── docs/       Documentación (decisión de arquitectura, etc.)
```

## Cómo funciona el login (resumen)

1. Abrís **http://localhost:8000** → te manda **directo al login de Keycloak**.
2. Te logueás (o te registrás) en Keycloak.
3. Django crea la sesión y te **redirige a la maqueta** (http://localhost:8443).
4. La maqueta pregunta a `GET /api/me/` quién sos y entra al dashboard **según tu rol**.

> El token vive en Django, **nunca en el navegador** (patrón BFF / opción C — ver
> `docs/decision-arquitectura.md`).

---

## Requisitos (instalar una vez)

- **Docker Desktop** (para Keycloak)
- **Python 3.12+** (marcá "Add python.exe to PATH" al instalar)
- **Node.js 20+** (usamos `pnpm` vía `npx`, no hace falta instalarlo global)

## Puesta en marcha (primera vez)

Se levantan **3 piezas, en este orden**. Cada comando en su propia terminal.

### 1) Keycloak (identidad) — puerto 8080

```bash
cd keycloak
cp .env.example .env        # completá POSTGRES_PASSWORD y KC_BOOTSTRAP_ADMIN_PASSWORD
docker compose up -d        # importa el realm de ./realm-export automáticamente
```

Consola admin: http://localhost:8080 (usuario/clave los del `.env`).
**Copiá el secret** del client: Clients → `global-exchange-web` → Credentials →
*(si dice `**********`, dale Regenerate)*. Lo vas a necesitar en el paso 2.
Detalle completo en [`keycloak/README.md`](keycloak/README.md).

### 2) Backend Django — puerto 8000

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate                 # Windows  (source .venv/bin/activate en Linux/Mac)
pip install -r requirements.txt
copy .env.example .env                  # cp en Linux/Mac
#   -> pegá el secret de Keycloak en KEYCLOAK_WEB_CLIENT_SECRET
python manage.py migrate
python manage.py runserver 8000
```

Detalle en [`backend/README.md`](backend/README.md).

### 3) Frontend (maqueta) — puerto 8443

```bash
cd frontend
npx pnpm install
npx pnpm dev
```

### Listo

Abrí **http://localhost:8000** y seguí el flujo. También podés abrir la maqueta
directo en http://localhost:8443 (si no hay sesión, te manda al login).

---

## Notas para el equipo

- **Los `.env` no se commitean** (están en `.gitignore`). Cada uno crea el suyo
  desde el `.env.example` correspondiente. El **secret de Keycloak** se copia de
  la consola, no se sube al repo.
- **Roles** (nombres de la ERS): `administrador`, `analista_cambiario`, `cajero`,
  `cliente`, `cliente_general`. Keycloak es la fuente de verdad; el backend los
  valida (nunca se confía en el navegador).
- Para proteger una vista por rol en Django:
  `from cuentas.decorators import rol_requerido` → `@rol_requerido("administrador")`.
- La decisión de arquitectura (Django plantillas vs React) está en
  `docs/decision-arquitectura.md` y sigue pendiente de confirmar con la cátedra.
