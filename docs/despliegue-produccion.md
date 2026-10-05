# Despliegue en producción

Cómo montar Global Exchange en un servidor (criterio **AMB** del Hito 5:
"Ambiente de producción, montado y funcionando").

Todo está preparado y **probado de punta a punta en una máquina local** (ver
[Qué se verificó](#qué-se-verificó)). Hay dos formas de montarlo:

- **[En internet sin servidor](#en-internet-sin-servidor-un-solo-comando)**:
  desde cualquier PC con Docker, un solo comando. Es la forma recomendada
  para las demos. Guía paso a paso en
  [`levantar-en-internet.md`](levantar-en-internet.md).
- **[En un servidor propio](#qué-se-levanta)**: los pasos del resto de esta
  guía.

---

## En internet sin servidor (un solo comando)

Con Docker Desktop abierto, desde la raíz del repositorio:

```bash
backend\.venv\Scripts\python publicar.py --demo    # Windows
backend/.venv/bin/python publicar.py --demo        # Linux/Mac
```

Al terminar imprime la dirección pública, por ejemplo
`https://palabras-al-azar.trycloudflare.com`, que abre desde cualquier
celular o computadora. `--demo` crea un usuario por rol (contraseña
`Prueba2026!`) y carga datos de ejemplo; las próximas veces no hace falta.

Para apagar: `backend\.venv\Scripts\python publicar.py --apagar` (los datos
quedan guardados).

### Cómo funciona

Levanta el mismo `docker-compose.prod.yml` de abajo, más
`docker-compose.publico.yml`, que agrega:

- **Dos túneles de Cloudflare** (gratis, sin cuenta, sin abrir puertos del
  router): uno para la aplicación y otro para Keycloak. Dan HTTPS, que
  Keycloak exige para entrar desde afuera.
- **Una puerta de entrada** (`publico/nginx.conf`) que deja todo en un solo
  dominio: Django en `/` y la maqueta en `/app/`. Es necesario porque la
  maqueta usa la cookie de sesión de Django, y el navegador no la manda a otro
  dominio (en desarrollo funciona porque los dos son `localhost`).

`publicar.py` lee las direcciones que tocaron, las escribe en `.env.prod`
(lo crea con claves nuevas la primera vez), levanta todo y configura Keycloak
con `keycloak/configurar_produccion.py`.

### Límites

- **La dirección cambia** cada vez que se apaga y se vuelve a levantar
  (mientras siga prendido, volver a correr el script no la cambia). Para una
  dirección fija hace falta un dominio propio y una cuenta de Cloudflare.
- **Funciona mientras la PC esté prendida** con Docker abierto.
- Recién creada, la dirección puede tardar uno o dos minutos en abrir.

### Qué se verificó

El 4 de octubre de 2026, por la dirección pública con HTTPS real: login por
Keycloak con los cuatro roles (cada uno aterriza en la maqueta con su rol),
cookie de sesión marcada `Secure`, las nueve pantallas de Django y las APIs,
los estáticos de `/admin/`, asociar un usuario a un cliente y una compra
(cotizar y confirmar) con CSRF, y el logout de vuelta al login de Keycloak.

---

## Qué se levanta

`docker-compose.prod.yml`, en la raíz del repositorio, levanta cuatro
contenedores:

| Contenedor | Qué es | Puerto |
|---|---|---|
| `keycloak` | Keycloak en **modo producción** (`start`, no `start-dev`) | 8080 |
| `keycloak-db` | PostgreSQL de Keycloak (solo lo usa Keycloak) | interno |
| `backend` | Django servido por **gunicorn** (no `runserver`) | 8000 |
| `frontend` | La maqueta ya construida, servida por **nginx** | 8443 |

Diferencias con desarrollo, y por qué:

- **gunicorn en vez de `runserver`**: la documentación de Django dice que
  `runserver` no se use en producción (no está pensado para seguridad ni
  rendimiento).
- **`DEBUG` apagado**: con `DEBUG` prendido, un error muestra código, rutas y
  configuración a cualquiera. Si falta `DJANGO_SECRET_KEY`, el backend **no
  arranca** en vez de arrancar inseguro.
- **WhiteNoise** sirve los archivos estáticos (los estilos de `/admin/`), que
  Django deja de servir con `DEBUG` apagado.
- **La base SQLite vive en un volumen** de Docker: sobrevive a reconstruir la
  imagen.
- **Las migraciones se aplican solas** al arrancar el backend.

Las dependencias de producción (gunicorn, WhiteNoise) están en
`backend/requirements-produccion.txt`, aparte: para desarrollar no hace falta
instalarlas.

---

## Requisitos del servidor

- Linux con **Docker** y **Docker Compose**.
- Puertos **8000, 8443 y 8080** abiertos (se pueden cambiar en `.env.prod`).
- Si el servidor tiene **IP pública**, HTTPS: ver [HTTPS](#https).

---

## Pasos

### 1. Configurar

```bash
git clone https://github.com/lucasvallejos-eng/Global_Exchange.git
cd Global_Exchange
cp .env.prod.example .env.prod
```

Editar `.env.prod`: reemplazar `servidor` por la IP o el dominio de la
máquina, y cambiar todas las claves (el archivo explica cómo generar una).
`.env.prod` **no se commitea** (está en `.gitignore`).

### 2. Levantar

```bash
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d --build
```

La primera vez tarda unos minutos (construye las imágenes). Keycloak tarda
alrededor de un minuto más en estar listo.

### 3. Configurar Keycloak (solo la primera vez)

El realm se importa pensado para desarrollo: solo acepta volver a
`localhost:8000` y el secreto del client viene enmascarado. Este script le
carga las direcciones reales y el secreto de `.env.prod`:

```bash
python keycloak/configurar_produccion.py --env-file .env.prod
```

Necesita Python con `requests` (por ejemplo, el entorno virtual del backend).
Sin este paso, el login falla con **"Invalid redirect uri"**.

### 4. Usuarios y datos de demo (opcional)

```bash
# Un usuario por rol (contraseña Prueba2026!)
python keycloak/crear_usuarios_prueba.py --url http://servidor:8080 --admin-password <KC_BOOTSTRAP_ADMIN_PASSWORD>

# Monedas, cotizaciones y clientes de ejemplo
docker compose -f docker-compose.prod.yml --env-file .env.prod exec backend python manage.py loaddata fixtures/demo.json
```

Para que un usuario pueda **operar** (RN02) hay que asociarlo a un cliente
desde la pantalla de clientes, después de que haya iniciado sesión una vez
(Django crea su usuario recién en el primer login).

### 5. Entrar

`http://servidor:8000` → login de Keycloak → la maqueta en
`http://servidor:8443`. Las pantallas de Django siguen en el 8000
(`/operaciones/`, `/tasas/`, etc.).

---

## Actualizar a una versión nueva

```bash
git pull
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d --build
```

Las migraciones nuevas se aplican solas al arrancar. Los datos no se tocan:
viven en los volúmenes.

## Respaldos

Los datos están en dos volúmenes de Docker:

- `global-exchange-prod_datos-django`: la base del sistema (`db.sqlite3`).
- `global-exchange-prod_keycloak-db`: usuarios y configuración de Keycloak.

---

## HTTPS

- **Servidor en una red privada** (la de la facultad, una LAN): funciona por
  HTTP tal como está.
- **Servidor con IP pública:** Keycloak exige HTTPS para conexiones externas
  (el realm tiene *Require SSL: external requests*, y es lo correcto en un
  sistema financiero). Hay que poner adelante un proxy que maneje HTTPS
  —por ejemplo Caddy, que saca el certificado solo—, usar `https://` en las
  tres URL de `.env.prod` y poner `DJANGO_HTTPS=1` (las cookies pasan a viajar
  solo cifradas).

## Límites conocidos

- **SQLite** admite un solo escritor a la vez. Para el uso del proyecto
  alcanza (por eso gunicorn corre con pocos procesos); si creciera, el paso
  natural es pasar la base del sistema a PostgreSQL.

---

## Qué se verificó

El 2 de octubre de 2026 se levantó este mismo `docker-compose.prod.yml` en una
máquina local (con otros puertos), se siguieron los pasos de arriba, y se
comprobó:

- Keycloak en modo producción publica la dirección pública configurada.
- El backend aplica las migraciones al arrancar y corre con gunicorn.
- `configurar_produccion.py` y `crear_usuarios_prueba.py` funcionan contra un
  Keycloak recién instalado; `fixtures/demo.json` carga en una base vacía.
- Login real: Django canjea el código contra Keycloak por la red interna de
  Docker, mientras el navegador lo ve por la dirección pública.
- Comprar y pagar desde la API, como la maqueta, con CSRF y CORS reales.
- El historial de Django muestra la operación.
- Con `DEBUG` apagado, los estáticos se sirven y un 404 no muestra la página
  técnica de Django.
- nginx sirve la maqueta, su JavaScript apunta al backend de producción, y
  las rutas internas devuelven la página.
- El logout vuelve al backend sin "Invalid redirect uri".

Después se bajó todo: no quedó ningún ambiente montado.
