# Tests del flujo básico (login, cliente, usuario)

## Contexto

El login real de la aplicación es **100% vía Keycloak (OIDC)**. No existe autenticación con usuario y contraseña locales: es `cuentas.auth.BackendOIDCKeycloak` quien, tras el intercambio OIDC con Keycloak, sincroniza el usuario y sus roles en la base de datos.

Para poder testear el resto del flujo (crear cliente, asociar usuario a un cliente, etc.) sin depender de un servidor Keycloak levantado, se simula el "inicio de sesión" usando `force_login` de Django. Esto deja la sesión exactamente como quedaría **después** de que `BackendOIDCKeycloak` sincronizó al usuario, y permite testear el resto del flujo contra los endpoints reales de `/api/`.

Son tests estándar de Django (`TestCase`): **no se usa pytest ni ninguna dependencia nueva**.

## Qué cubre `backend/tests/test_flujo_basico.py`

1. **Crear usuario** — `User.objects.create_user(...)`
2. **Iniciar sesión** — vía `force_login`, seteando además `oidc_id_token_expiration` en la sesión. Esto es necesario porque, si no se setea, el middleware `SessionRefresh` de `mozilla-django-oidc` redirige pensando que el token OIDC expiró.
3. **Crear cliente** — `POST /api/clientes/`, autenticado como usuario con rol administrador.
4. **Agregar usuario al cliente** — `PATCH /api/clientes/<id>/` con `usuarios: [id]`.

Además incluye:

- Un test de **flujo completo** que encadena los 4 pasos anteriores.
- Un test **negativo**: `api_me` sin sesión iniciada debe devolver `401`.

## Cómo correrlos

```bash
cd backend
.venv/bin/python manage.py test tests
```

Resultado esperado: **6/6 OK**.

## Aclaración importante

Estos tests **no** prueban el login real contra Keycloak — eso requeriría levantar un servidor Keycloak y mockear el intercambio OIDC (authorization code, tokens, etc.).

Lo que sí prueban es el comportamiento del backend **asumiendo que la sincronización de usuario/roles ya ocurrió**, que es exactamente lo que hace `cuentas.auth.BackendOIDCKeycloak` en producción.
