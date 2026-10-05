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

> **Atajo:** una vez hecha la configuración de abajo (los `.env`, el `.venv` y
> Docker), `levantar_todo.py` levanta las tres piezas con un solo comando o con
> el Play de PyCharm / VS Code. Ver la guía en
> [`docs/conversaciones-ia/2026-10-02-fixes-pre-tag.md`](docs/conversaciones-ia/2026-10-02-fixes-pre-tag.md#guía-levantar_todopy-en-cada-sistema-e-ide).

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

### 4) Datos de demo y usuarios de prueba (opcional)

Un backend recién migrado arranca con las tablas vacías, y un Keycloak recién
levantado arranca sin usuarios (el realm-export no los trae: las contraseñas
no se exportan). Para no cargar todo a mano antes de una demo:

```bash
cd backend
.venv\Scripts\python manage.py loaddata fixtures/demo.json
cd ..\keycloak
..\backend\.venv\Scripts\python crear_usuarios_prueba.py
```

Esto deja 3 monedas con cotización y 2 clientes de ejemplo, y los usuarios
`admin.test` / `analista.test` / `cajero.test` / `cliente.test` (contraseña
`Prueba2026!` para los cuatro), uno por rol. Los segmentos de comisión
(Minorista, Mayorista, VIP) no vienen en el fixture: los crea solos la
migración de `comisiones`.

Para **operar** (RN02), el usuario tiene que estar asociado a un cliente: se
asocia desde la pantalla de clientes, después de que inició sesión al menos una
vez (Django crea su usuario en el primer login).

> **Si la base ya tiene datos cargados**, `loaddata` va a fallar con un
> `IntegrityError` (el fixture fija los mismos IDs de siempre, por ejemplo
> `pk=1` para USD, y van a chocar con lo que ya tengas). No es que el fixture
> esté mal: vaciá las tablas antes de cargarlo, o usá una base nueva.

### Listo

Abrí **http://localhost:8000** y seguí el flujo. También podés abrir la maqueta
directo en http://localhost:8443 (si no hay sesión, te manda al login).

### Producción

Todo el sistema se levanta junto con `docker-compose.prod.yml` (Keycloak en
modo producción, Django con gunicorn, la maqueta con nginx). Paso a paso en
[`docs/despliegue-produccion.md`](docs/despliegue-produccion.md).

Para ponerlo **en internet desde esta misma PC**, sin servidor (Docker Desktop
abierto):

```bash
backend\.venv\Scripts\python publicar.py --demo
```

Imprime una dirección `https://...trycloudflare.com` que abre desde cualquier
lado. Para apagarlo: `backend\.venv\Scripts\python publicar.py --apagar`.
Paso a paso, usuarios y problemas comunes en
[`docs/levantar-en-internet.md`](docs/levantar-en-internet.md).

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
- **Decisión de arquitectura: Django.** El alcance de cada sprint se demuestra
  por las pantallas de Django (`backend/templates/`), no por la maqueta React.
  Detalle e histórico en `docs/decision-arquitectura.md`.
- **Los roles de la maqueta ya coinciden con los de Keycloak.** `src/types.ts`
  y `elegirRol()` en `App.tsx` esperaban `cliente_minorista` /
  `cliente_mayorista` / `cliente_VIP` como si fueran roles de Keycloak, pero
  Keycloak solo tiene `cliente` y `cliente_general` — el segmento comercial
  (Minorista/VIP/Corporativo) es un dato del `Cliente` en el backend
  (`comisiones.SegmentoCliente`), no un rol de autenticación. Se corrigió para
  que la maqueta use los roles reales; avisale a Lucas si volvés a tocar estos
  archivos, siguen siendo su territorio.
