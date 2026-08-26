# Keycloak — Global Exchange

Configuración del servidor de identidad. Toda la autenticación está delegada a **Keycloak 26.7**,
corriendo local en Docker. Este documento es el runbook para dejarlo andando y exportar el realm
para el resto del equipo.

> **Fuente de verdad:** Keycloak. Los roles llegan en el token; el frontend nunca decide permisos
> (ver [`../docs/decision-arquitectura.md`](../docs/decision-arquitectura.md)).

---

## Levantar con Docker Compose (forma reproducible, recomendada para el equipo)

Es la manera de que **todos tengan la misma configuración**. Usa PostgreSQL (no el H2 embebido),
así el realm sobrevive a reinicios, y trae **Mailpit** como servidor SMTP de pruebas.

```bash
cd keycloak
cp .env.example .env      # completá POSTGRES_PASSWORD y KC_BOOTSTRAP_ADMIN_PASSWORD
docker compose up -d
```

Servicios que levanta:

| Servicio | Imagen | Puertos (host) | Para qué |
|---|---|---|---|
| `ge-keycloak` | `quay.io/keycloak/keycloak:26.7` | `8080` | Servidor de identidad |
| `ge-keycloak-db` | `postgres:16` | `5433` → 5432 | Base de datos de Keycloak (5433 para no chocar con un Postgres del sistema) |
| `ge-mailpit` | `axllent/mailpit` | `1025` (SMTP), `8025` (web) | Correos de prueba; se ven en http://localhost:8025 |

- Keycloak arranca con **`start-dev --import-realm`** y monta **`./realm-export`** en
  `/opt/keycloak/data/import`. Si ahí hay un `realm.json`, lo importa solo al arrancar. Si todavía no
  exportaste el realm, arranca vacío (sin error).
- Para que los correos (verificación, "olvidé mi contraseña") caigan en Mailpit: en la consola,
  **Realm settings → Email**, host `mailpit`, puerto `1025`, sin SSL/TLS.

> ⚠️ **Si ya tenés el contenedor `keycloak` del `docker run` manual**, sacalo antes para no chocar de
> nombres/puerto: `docker rm -f keycloak`. Ese contenedor usaba H2 (config en memoria del
> contenedor); Compose usa Postgres y toma la config del `realm.json` importado.

Bajar todo: `docker compose down` (agregá `-v` para borrar también la base de datos).

---

## Paso 1 — Levantar Keycloak (manual, ~30 min)

Esto son clicks en el navegador

1. Instalar **Docker Desktop** y abrirlo.
2. Levantar Keycloak:
   ```bash
   docker run -d --name keycloak -p 8080:8080 \
     -e KC_BOOTSTRAP_ADMIN_USERNAME=admin \
     -e KC_BOOTSTRAP_ADMIN_PASSWORD=admin \
     quay.io/keycloak/keycloak:26.7 start-dev
   ```
3. Entrar a http://localhost:8080 con `admin` / `admin`.
4. **Create realm → `GlobalExchange`**.
5. **Realm settings → Login →** prender **User registration** y **Forgot password**.
6. Probar en http://localhost:8080/realms/GlobalExchange/account : registrarse con un correo
   inventado y entrar.
7. **Realm settings → Localization →** Internationalization **ON**, español por defecto.

Con esto ya hay **registro y login funcionando: RF02 de la ERS cumplido sin código.**

---

## Los dos clients

**Clients → Create client**, dos veces. Se crean los dos aunque todavía no esté decidida la
arquitectura, así el trabajo de identidad no queda bloqueado (la decisión A/B/C solo cambia *cuál*
se usa, no cómo se arma el realm).

| | `global-exchange-web` | `global-exchange-spa` |
|---|---|---|
| Client authentication | **ON** (confidential) | **OFF** (public) |
| Valid redirect URIs | `http://localhost:8000/oidc/callback/` | `http://localhost:5173/*` |
| Web origins | `http://localhost:8000` | `http://localhost:5173` |
| PKCE (Advanced) | — | **S256** |

- `global-exchange-web` → lo usan las opciones **A** (Django plantillas) y **C** (Django BFF).
- `global-exchange-spa` → lo usa la opción **B** (React SPA con token en el navegador).
- El puerto **5173** es el de Vite; **8000** es el de Django.

Del `global-exchange-web`, pestaña **Credentials**, copiar el **secret** y guardarlo en `.env`
(ver [Secretos](#secretos)). **Nunca commitearlo.**

---

## Los roles

**Clients → `global-exchange-web` → Roles → Create role**, cinco veces (nombres de la ERS):

- `administrador`
- `analista_cambiario`
- `cajero`
- `cliente`
- `cliente_general`

Después: **Realm settings → User registration → Default roles →** agregar **`cliente`**.
(Así todo el que se registra queda como cliente por defecto.)

---

## El mapper de roles ⚠️

**Client scopes → `global-exchange-web-dedicated` → Add mapper → By configuration → User Client
Role**

- **Token Claim Name:** `roles`
- **Multivalued:** ON
- **Add to ID token / access token / userinfo:** los **tres** en ON

> **El paso que más se olvida:** sin **"Add to userinfo" en ON**, los roles nunca llegan y todos los
> usuarios entran sin permisos. Es un claim plano `roles`.

---

## Exportar el realm

```bash
docker exec keycloak /opt/keycloak/bin/kc.sh export --file /tmp/realm.json --realm GlobalExchange
docker cp keycloak:/tmp/realm.json ./keycloak/realm-export/realm.json
```

El `realm-export/realm.json` es lo que se le pasa al equipo para que tengan la misma configuración.
**Revisar el JSON antes de commitear** (ver abajo).

### Antes de commitear el JSON — sacar los secrets 🔒

El export **incluye datos sensibles**. Abrir `realm-export/realm.json` y, como mínimo:

- Vaciar el/los campos `"secret"` de los clients (el de `global-exchange-web` aparece ahí).
- Revisar que no hayan quedado credenciales de usuarios de prueba (`"credentials"`, hashes de
  contraseña) si registraste usuarios reales durante las pruebas.

El secret va en `.env` (que ya está en `.gitignore`), nunca en el export ni en el código.

### Si el export falla con error de base de datos

`start-dev` mantiene abierta la base H2 en archivo; lanzar `kc.sh export` como segundo proceso puede
chocar con un **lock de H2** ("Database may be already in use"). Dos alternativas:

- Usar el **Partial export** de la UI: **Realm settings → menú "⋮" → Partial export** (incluir
  clients y roles). Igual hay que revisar y sacar secrets del JSON resultante.
- O detener el contenedor, correr el export con el server parado, y volver a levantarlo.

---

## Secretos

- `.env` está en `.gitignore` (`.env*`). Ahí va el client secret de Keycloak y el de Google.
- Nunca en el código ni en el export del realm.

---

## Verificación

```bash
docker ps               # ¿está corriendo Keycloak?
docker logs keycloak    # errores del servidor de identidad
```

Login de prueba: http://localhost:8080/realms/GlobalExchange/account

---

## Qué automatiza Claude Code y qué no

- **No** (manual, browser/Docker): levantar el contenedor, crear realm/clients/roles/mapper, los
  clicks del admin.
- **Sí** (cuando traigas el `realm.json`): revisarlo y **redactar los secrets** antes del commit,
  armar el `.env.example`, y —cuando el equipo decida la arquitectura— escribir la integración OIDC
  (Django con `mozilla-django-oidc` si gana A/C).
