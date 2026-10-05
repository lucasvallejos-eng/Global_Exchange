# Global Exchange — guía para Claude Code

Casa de cambio digital (compra/venta de divisas). Proyecto de **Ingeniería de
Software 2**, FP-UNA, Equipo 04. Repo: https://github.com/lucasvallejos-eng/Global_Exchange

Responder al usuario en español (rioplatense/paraguayo, informal).

## Estructura

```
backend/    Django 5.2 + mozilla-django-oidc (Keycloak). SQLite. Puerto 8000
frontend/   Maqueta React 19 + Vite 8 (pnpm). Puerto 8443
keycloak/   docker-compose de desarrollo (Keycloak 26.7 + Postgres + Mailpit) y realm-export
docs/       Sphinx, decisión de arquitectura, despliegue, conversaciones-ia/ (criterio CHIA)
publico/    nginx de entrada del ambiente público
levantar_todo.py            levanta el ambiente de DESARROLLO completo
publicar.py                 levanta PRODUCCIÓN y la publica en internet (túneles Cloudflare)
docker-compose.prod.yml     producción (gunicorn + WhiteNoise, Keycloak "start", maqueta en nginx)
docker-compose.publico.yml  override de prod para publicar.py
```

Apps de Django: `cuentas` (login OIDC, `/api/me/`, roles), `clientes`, `monedas`,
`cotizaciones`, `medios_pago`, `comisiones`, `tasas`, `operaciones`.

## Arquitectura en un minuto

- **Login 100 % Keycloak (OIDC), patrón BFF:** el token vive en la sesión de
  Django, nunca en el navegador. `GET /` → Keycloak → `/oidc/callback/` →
  redirige a la maqueta (`MAQUETA_URL`), que pregunta `GET /api/me/`.
- **Roles = client roles** de `global-exchange-web`, llegan en el claim plano
  `roles` y se copian a grupos de Django (`cuentas/auth.py`). Roles:
  `administrador`, `analista_cambiario`, `cajero`, `cliente`, `cliente_general`.
  Proteger vistas con `from cuentas.decorators import rol_requerido` →
  `@rol_requerido("administrador")`.
- **Las pantallas de Django (`backend/templates/`) son el entregable** de cada
  sprint; la maqueta React consume `/api/`.
- **Maqueta y backend deben compartir dominio:** la maqueta llama a `/api/` con
  la cookie de sesión (`SameSite=Lax`). En desarrollo funciona porque ambos son
  `localhost`; en el ambiente público lo resuelve `publico/nginx.conf`
  (Django en `/`, maqueta en `/app/`).
- Para operar (RN02) el usuario tiene que estar asociado a un cliente
  (`PATCH /api/clientes/<id>/` con `usuarios: [id]`, o desde la pantalla de
  clientes). Django crea el usuario recién en su primer login.

## Levantar en una máquina nueva (desarrollo)

Requisitos: **Docker Desktop**, **Python 3.12+**, **Node 20+** (`.mise.toml`
fija Node 22 y pnpm 10.34.3; pnpm se usa vía `npx`), **Git**.

```bash
git clone https://github.com/lucasvallejos-eng/Global_Exchange.git
cd Global_Exchange

# 1. Variables (los .env NO se commitean; se crean desde los .example)
cp keycloak/.env.example keycloak/.env   # completar POSTGRES_PASSWORD y KC_BOOTSTRAP_ADMIN_PASSWORD (cualquiera, es local)
cp backend/.env.example backend/.env     # el secret se completa en el paso 4

# 2. Entorno de Python
python -m venv backend/.venv
backend/.venv/Scripts/pip install -r backend/requirements.txt     # Windows (bin/ en Linux/Mac)

# 3. Keycloak (importa el realm de keycloak/realm-export la primera vez)
cd keycloak && docker compose up -d && cd ..
```

4. **Secret del client** (el realm-export lo trae enmascarado como
   `**********`): consola http://localhost:8080 → realm `GlobalExchange` →
   Clients → `global-exchange-web` → Credentials → **Regenerate** → copiarlo en
   `KEYCLOAK_WEB_CLIENT_SECRET` de `backend/.env`. Para verificarlo sin navegador:
   `POST /realms/GlobalExchange/protocol/openid-connect/token` con
   `grant_type=client_credentials`: si responde `unauthorized_client` el secret
   está bien (solo faltan service accounts); `invalid_client` = secret mal.

```bash
# 5. Base, datos de demo y usuarios de prueba
cd backend
.venv/Scripts/python manage.py migrate
.venv/Scripts/python manage.py loaddata fixtures/demo.json      # falla con IntegrityError si la base ya tiene datos: es esperable
cd ../keycloak
../backend/.venv/Scripts/python crear_usuarios_prueba.py --admin-password <KC_BOOTSTRAP_ADMIN_PASSWORD>
cd ..

# 6. Levantar todo (Keycloak + migrate + runserver 8000 + vite 8443)
backend/.venv/Scripts/python levantar_todo.py
```

Entrar por **http://localhost:8000**. Usuarios de prueba (contraseña
`Prueba2026!`): `admin.test`, `analista.test`, `cajero.test`, `cliente.test`,
uno por rol.

Puertos de desarrollo: Keycloak 8080, Postgres de Keycloak 5433, Mailpit 8025
(SMTP 1025), backend 8000, maqueta 8443. Apagar: Ctrl+C en `levantar_todo.py`
y `cd keycloak && docker compose stop`.

## Tests y documentación

```bash
cd backend && .venv/Scripts/python manage.py test          # 142 tests, ~5 s, no necesitan Keycloak
cd docs && ../backend/.venv/Scripts/python -m sphinx -b html . _build/html
```

Los tests simulan el login con `force_login` + `oidc_id_token_expiration` en la
sesión (ver `backend/tests/README.md`).

## Producción en internet (ambiente público)

Con Docker Desktop abierto, desde la raíz:

```bash
backend/.venv/Scripts/python publicar.py --demo   # primera vez (usuarios + datos de demo)
backend/.venv/Scripts/python publicar.py          # las siguientes
backend/.venv/Scripts/python publicar.py --apagar
```

Abre dos túneles de Cloudflare (sin cuenta), escribe las direcciones en
`.env.prod` (lo crea con claves aleatorias la primera vez), levanta
`docker-compose.prod.yml` + `docker-compose.publico.yml` y configura Keycloak
con `keycloak/configurar_produccion.py`. Imprime `https://<algo>.trycloudflare.com`.
La dirección cambia cada vez que los túneles se recrean; mientras sigan
arriba, volver a correrlo no la cambia. Keycloak de prod queda en
`127.0.0.1:18080` para administrarlo localmente; no choca con el de desarrollo.
Guía para humanos: `docs/levantar-en-internet.md`. Servidor propio:
`docs/despliegue-produccion.md`.

## Convenciones del equipo

- **Git Flow:** ramas `feature/IS2GE-<id>` (id de la historia en Jira) desde
  `develop`; se integran a `develop`. `develop` pasa a `main` con
  `git merge --no-ff develop -m "Merge develop (Sprint N / Hito M) en main"`.
  Al cerrar cada sprint, **tag anotado** sobre `main` (`v1.0`, `v2.0`, `v3.0`…).
- **Commits en español, en infinitivo y sin tildes:** "Agregar …", "Corregir …".
- **Nunca firmar como Claude:** sin `Co-Authored-By: Claude` en commits y sin
  "Generated with Claude Code" en PRs. El repo es entregable del equipo.
- Nunca commitear `.env*` (solo `.env.example` y `.env.prod.example`), ni
  secrets dentro de `keycloak/realm-export/` (vaciar los `"secret"` antes de
  exportar).
- No tocar `frontend/src/types.ts` ni `elegirRol()` de `App.tsx` sin avisar a
  Lucas (son su territorio).

## Trampas conocidas (Windows)

- `python` a secas suele abrir la Microsoft Store: usar siempre
  `backend/.venv/Scripts/python`.
- Docker Desktop puede estar instalado en `%LOCALAPPDATA%\Programs\DockerDesktop\`
  (no en Program Files). Si `docker ps` falla con *dockerDesktopLinuxEngine*,
  está cerrado.
- Desde Git Bash, los argumentos tipo `/app/` que se pasan a `docker` se
  convierten en rutas de Windows (`/Program Files/Git/app/`): anteponer
  `MSYS_NO_PATHCONV=1`.
- Keycloak marca sus cookies `Secure`. El navegador las manda igual a
  `localhost`, pero `requests`/`curl` no: para probar el login OIDC por script
  contra http://localhost, desmarcar `cookie.secure` antes de cada pedido.
- `--import-realm` se saltea si el realm ya existe en el volumen de Postgres:
  cambios a `realm-export.json` no se aplican sobre un Keycloak ya creado.
- En `.env.prod`, `POSTGRES_PASSWORD` no se puede cambiar después de creado el
  volumen `global-exchange-prod_keycloak-db` (la base no aceptaría la nueva).

## Pendientes conocidos

- El realm no tiene SMTP configurado y `verifyEmail` está apagado (el Hito 3
  pide verificación por correo; el equipo lo resuelve desde Keycloak).
- Los clientes del fixture no tienen segmento, así que la comisión calculada
  da 0 hasta asignarles Minorista/Mayorista/VIP.
- Todos los usuarios reciben además el rol `cliente` (default roles del realm).
