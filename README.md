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

- **Docker Desktop** (para Keycloak y contenedores de producción)
- **Python 3.12+** (marcá "Add python.exe to PATH" al instalar)
- **Node.js 20+** (usamos `pnpm` vía `npx`, no hace falta instalarlo global)
- **Git**

---

## Puesta en marcha rápida (Scripts recomendados)

El proyecto cuenta con scripts en Python que automatizan todo el proceso: configuración de entornos virtuales, archivos `.env`, regeneración e inyección de secretos de Keycloak, credenciales externas (Stripe, Facturación Segura), migraciones, usuarios de prueba y levantado de servicios.

### 1) Levantar todo el entorno local — `levantar_todo.py`

Es la forma más rápida y recomendada para desarrollo diario. Con **Docker Desktop abierto**, ejecutá en la terminal desde la raíz del proyecto:

```bash
python levantar_todo.py
```

*(También podés presionar directamente el botón **Play / Run** en PyCharm o VS Code sobre `levantar_todo.py`).*

**¿Qué hace automáticamente?**
1. **Limpia contenedores previos:** Ejecuta `docker compose down -v` en `keycloak/` para garantizar un estado limpio.
2. **Genera archivos `.env`:** Reconstruye automáticamente los `.env` necesarios a partir de sus `.env.example`.
3. **Inyecta credenciales:** Si tenés el archivo `credenciales.text` (o `credenciales.txt`) en la raíz del proyecto, extrae e inyecta de forma transparente las credenciales de Stripe y Facturación Segura ESI en backend y frontend (`inyectar_credenciales.py`).
4. **Levanta infraestructura:** Inicia Keycloak, PostgreSQL y Mailpit con Docker Compose.
5. **Configura Keycloak:** Espera a que el realm `GlobalExchange` responda, regenera el Client Secret y lo inyecta automáticamente en `backend/.env`.
6. **Crea usuarios de prueba:** Registra los usuarios de prueba con sus roles (`admin.test`, `analista.test`, `cajero.test`, `cliente.test` con contraseña `Prueba2026!`).
7. **Prepara Backend Django:** Verifica/crea el entorno virtual `backend/.venv`, instala las dependencias (`requirements.txt`), ejecuta `python manage.py migrate` y carga los fixtures (`fixtures/demo.json`).
8. **Prepara Frontend:** Verifica e instala dependencias (`pnpm install`) si hiciera falta.
9. **Inicia los servidores en simultáneo:**
   - **Backend Django:** [http://localhost:8000](http://localhost:8000) (acceso principal con redirección al login de Keycloak)
   - **Frontend (Maqueta React):** [http://localhost:8443](http://localhost:8443)
   - **Consola Keycloak:** [http://localhost:8080](http://localhost:8080) (`admin` / `admin123`)
   - **Mailpit (bandeja de correo local):** [http://localhost:8025](http://localhost:8025)

Para detener todo, simplemente presioná `Ctrl+C` en la terminal (o botón Stop en tu IDE).

---

### 2) Publicar en Internet — `publicar.py`

Levanta el proyecto en **modo producción** (`docker-compose.prod.yml`) y genera **túneles Cloudflare** (`docker-compose.publico.yml`), permitiendo acceder al sistema desde cualquier dispositivo en internet mediante URLs HTTPS públicas seguras, sin necesidad de abrir puertos ni tener dominio o IP fija.

Con **Docker Desktop abierto**:

```bash
python publicar.py          # Levanta producción y publica los túneles Cloudflare
python publicar.py --demo   # Además carga datos de demo y usuarios de prueba listos
python publicar.py --apagar # Detiene y apaga los contenedores y los túneles
```

- Inyecta automáticamente credenciales desde `credenciales.text` en `.env.prod`.
- Al terminar, imprime en la consola la URL pública temporal `https://...trycloudflare.com` para ingresar.
- Para más información sobre arquitectura y resolución de problemas, ver [`docs/levantar-en-internet.md`](docs/levantar-en-internet.md).

---

### 3) Despliegue automático unificado — `desplegar.py`

`desplegar.py` permite gestionar el despliegue tanto para desarrollo como para producción en un único comando. Se encarga de:
1. **Código fuente:** Descargar o sincronizar el tag de release solicitado.
2. **Base de datos:** Correr migraciones o reconstruir desde cero (`--base-nueva`).
3. **Población:** Cargar datos de prueba y usuarios demo listos para operar.

Con **Docker Desktop abierto**:

```bash
# Entorno de desarrollo local (orquesta levantar_todo.py)
python desplegar.py --ambiente desarrollo

# Despliegue de un release específico en producción (orquesta publicar.py)
python desplegar.py --ambiente produccion --tag v5.0

# Desarrollo arrancando con base de datos limpia de cero
python desplegar.py --ambiente desarrollo --base-nueva
```

| Opción | Qué hace |
|---|---|
| `--ambiente` | `desarrollo` (usa `levantar_todo.py`) o `produccion` (usa `publicar.py`). **Obligatoria**. |
| `--tag` | Versión a desplegar (`v4.0`, `v5.0`...). Requiere no tener cambios sin commitear. |
| `--base-nueva` | Borra la base antes de desplegar. En producción borra también la de Keycloak. |
| `--sin-datos` | Producción: no carga los datos de ejemplo ni los usuarios de prueba. |

> **Tip:** También sirve en una máquina limpia sin el proyecto clonado: copiando únicamente `desplegar.py` a una carpeta vacía, clona el repositorio en `./Global_Exchange` y ejecuta el despliegue automáticamente.

---

### 4) Inyección automática de credenciales (`credenciales.text`)

Si disponés de credenciales para servicios externos (pasarela de pagos **Stripe** y facturación electrónica **Facturación Segura ESI**):
1. Colocá el archivo `credenciales.text` (o `credenciales.txt`) en la raíz del proyecto.
2. Al ejecutar `levantar_todo.py` o `publicar.py`, el script auxiliar `inyectar_credenciales.py` detectará los bloques correspondientes y distribuirá automáticamente las variables de entorno necesarias (`backend/.env`, `frontend/.env`, `backend/.env.stripe`, `backend/.env.facturasegura`, `.env.prod`). No es necesario copiar ni pegar claves manualmente.

---

## Puesta en marcha manual (Paso a paso alternativo)

Si preferís levantar cada pieza de forma individual en terminales separadas para depuración granular, podés seguir estos pasos:

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

---

## Notas para el equipo

- **Los `.env` y credenciales no se commitean** (están en `.gitignore`). Los scripts automatizados (`levantar_todo.py`, `publicar.py`) se encargan de generarlos e inyectar el secret de Keycloak y credenciales externas automáticamente. Si configurás manualmente, creá cada archivo desde su correspondiente `.env.example`.
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
