# Cómo levantar Global Exchange en internet

Guía paso a paso para poner el sistema completo (Keycloak, Django y la maqueta)
en una dirección pública `https://...trycloudflare.com`, accesible desde
cualquier celular o computadora, **sin servidor**: corre en tu PC con Docker.

Es el ambiente de producción del proyecto (`docker-compose.prod.yml`: Django
con gunicorn, Keycloak en modo producción, la maqueta con nginx) publicado a
través de túneles de Cloudflare.

---

## 1. Requisitos (una sola vez)

- **Docker Desktop**, abierto.
- **Python 3.12 o más nuevo.** En Windows, al instalarlo marcá *"Add python.exe
  to PATH"*.
- **Git.**

No hace falta cuenta de Cloudflare ni abrir puertos del router.

## 2. Preparar el proyecto (una sola vez)

```bash
git clone https://github.com/lucasvallejos-eng/Global_Exchange.git
cd Global_Exchange
python -m venv backend/.venv
```

Instalar las dependencias:

```bash
backend\.venv\Scripts\pip install -r backend\requirements.txt    # Windows
backend/.venv/bin/pip install -r backend/requirements.txt        # Linux/Mac
```

> Si ya levantabas el proyecto en desarrollo, este entorno ya lo tenés: pasá
> directo al paso 3.

## 3. Levantar

Con Docker Desktop abierto, desde la raíz del repositorio.

**La primera vez**, con `--demo` (crea los usuarios de prueba y carga datos de
ejemplo):

```bash
backend\.venv\Scripts\python publicar.py --demo     # Windows
backend/.venv/bin/python publicar.py --demo         # Linux/Mac
```

**Las veces siguientes**, sin `--demo` (los datos ya quedaron guardados):

```bash
backend\.venv\Scripts\python publicar.py
```

La primera vez tarda unos 5 minutos (descarga y construye las imágenes); las
siguientes, menos de un minuto. Al terminar muestra:

```
==============================================================
  Global Exchange está en internet. Entrá (y compartí):

      https://palabras-al-azar.trycloudflare.com

  Maqueta:   https://palabras-al-azar.trycloudflare.com/app/
  Keycloak:  https://otras-palabras.trycloudflare.com   (admin: los datos están en .env.prod)
==============================================================
```

> Si al final dice *"Cloudflare todavía no publicó las direcciones"*, no es un
> error: la dirección nueva tarda uno o dos minutos en abrir. Esperá y entrá.

## 4. Entrar

Abrí la primera dirección. Te lleva al login de Keycloak y, después, a la
maqueta con el menú de tu rol.

| Usuario | Rol | Contraseña |
|---|---|---|
| `admin.test` | administrador | `Prueba2026!` |
| `analista.test` | analista_cambiario | `Prueba2026!` |
| `cajero.test` | cajero | `Prueba2026!` |
| `cliente.test` | cliente | `Prueba2026!` |

Las pantallas de Django están en la misma dirección: `/operaciones/`,
`/tasas/`, `/monedas/`, etc. La maqueta, en `/app/`.

**Para operar** (comprar o vender, RN02), el usuario tiene que estar asociado a
un cliente: entrá como `admin.test` y asocialo desde la pantalla de clientes.
El usuario tiene que haber iniciado sesión al menos una vez antes, porque
Django lo crea en su primer login.

## 5. Apagar

```bash
backend\.venv\Scripts\python publicar.py --apagar
```

Los datos (usuarios, monedas, operaciones) quedan guardados para la próxima.

---

## Lo que hay que saber

- **La dirección cambia cada vez que se apaga y se vuelve a levantar.** Hay
  que pasar la nueva. Mientras siga prendido, volver a correr `publicar.py`
  no la cambia.
- **Funciona mientras tu PC esté prendida** con Docker Desktop abierto.
- **Cada PC tiene su propio ambiente.** Si otro integrante lo levanta en su
  máquina, tiene su propia dirección y sus propios datos.
- **`.env.prod` guarda las claves** (se crea solo la primera vez, con claves
  aleatorias). No se sube a git. Si lo borrás, el script crea uno nuevo, pero
  la base de Keycloak ya guardada no va a aceptar la clave nueva: ver
  [Empezar de cero](#empezar-de-cero).
- **No choca con el ambiente de desarrollo**: se pueden tener los dos
  levantados al mismo tiempo.

## Problemas comunes

**"Docker no responde. Abrí Docker Desktop"**
Abrí Docker Desktop, esperá a que diga *Engine running* y volvé a correr el
script.

**El link no abre ("no se puede acceder a este sitio")**
Si la dirección es nueva, esperá uno o dos minutos. Si sigue sin abrir,
fijate que el sistema siga prendido (paso 3: correr el script de nuevo no
cambia la dirección si los túneles siguen arriba).

**"Invalid redirect uri" en el login**
La dirección cambió y Keycloak no se enteró. Corré `publicar.py` de nuevo:
vuelve a configurarlo.

**Ver qué está pasando adentro**

```bash
docker compose -f docker-compose.prod.yml -f docker-compose.publico.yml --env-file .env.prod ps
docker compose -f docker-compose.prod.yml -f docker-compose.publico.yml --env-file .env.prod logs backend
```

(Cambiando `backend` por `keycloak`, `gateway`, `tunel-app`, etc.)

### Empezar de cero

**Borra todos los datos del ambiente público** (usuarios de Keycloak, monedas,
operaciones). El de desarrollo no se toca.

```bash
docker compose -f docker-compose.prod.yml -f docker-compose.publico.yml --env-file .env.prod down -v
del .env.prod                                          # Windows (rm .env.prod en Linux/Mac)
backend\.venv\Scripts\python publicar.py --demo
```

---

## Cómo funciona por dentro

`publicar.py` levanta `docker-compose.prod.yml` junto con
`docker-compose.publico.yml`, que agrega:

- **Dos túneles de Cloudflare** (`tunel-app` y `tunel-keycloak`): salen desde
  tu PC hacia Cloudflare y dan direcciones públicas con HTTPS, que Keycloak
  exige para entrar desde afuera.
- **Una puerta de entrada** (`gateway`, configurada en `publico/nginx.conf`)
  que deja todo bajo un mismo dominio: Django en `/` y la maqueta en `/app/`.
  Es necesario porque la maqueta usa la cookie de sesión de Django, y el
  navegador no la manda a otro dominio.

El script lee las direcciones que tocaron, las escribe en `.env.prod`, levanta
todo y configura Keycloak con `keycloak/configurar_produccion.py`.

Para montarlo en un servidor propio en vez de en tu PC, ver
[`despliegue-produccion.md`](despliegue-produccion.md).
