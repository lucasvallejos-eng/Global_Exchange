# Recopilación de conversaciones con IA — Lucas Vallejos (Google Antigravity / Gemini)

- **Proyecto:** Global Exchange
- **Repositorio:** `lucasvallejos-eng/Global_Exchange`
- **Integrante:** Lucas Vallejos
- **Asistente:** Google Antigravity (Gemini)
- **Período:** 29 de agosto al 12 de octubre de 2026

---

## Criterio de recopilación

Este documento reúne de manera íntegra y cronológica las conversaciones técnicas
mantenidas exclusivamente entre **Lucas Vallejos** y **Google Antigravity (Gemini)** en
el marco del proyecto **Global Exchange**. No incluye interacciones de otros miembros del
equipo ni sesiones de otras herramientas externas (como Claude Code o Copilot CLI),
centrándose estrictamente en el historial bilateral de desarrollo, depuración, refactorización,
arquitectura y despliegue del sistema.

Cada sesión se encuentra documentada siguiendo las directrices del criterio CHIA
(Conversaciones con Herramientas de Inteligencia Artificial) de la cátedra:

- **Contexto:** problema técnico, necesidad de negocio o bloqueo inicial.
- **Qué se le pidió a la IA:** requerimientos, preguntas y alcances solicitados por Lucas.
- **Qué se hizo:** diagnóstico, comandos ejecutados, archivos modificados y soluciones concretas.
- **Qué se descartó y por qué:** alternativas analizadas que se rechazaron por motivos de seguridad, arquitectura o buenas prácticas.
- **Verificación:** pruebas funcionales, compilación, tests y comandos para validar la solución.
- **Queda abierto:** deudas técnicas, mejoras pendientes o dependencias para fases posteriores.

Las credenciales reales, secretos de producción y tokens sensibles no se reproducen en este
documento, resguardando la seguridad del proyecto.

---

## Índice de sesiones

| # | Fecha | Rama | Tema principal |
|---|---|---|---|
| 1 | 2026-08-29 | `develop` | Diagnóstico y configuración inicial del entorno local |
| 2 | 2026-08-29 | `develop` | Corrección de error de exportación TypeScript en `ClientesModule` |
| 3 | 2026-08-30 | `develop` | Puesta en marcha según Guía de Entorno y fix de base de datos de Keycloak |
| 4 | 2026-09-10 | `develop` | Depuración de autenticación OIDC (HTTP 401) y mapeo de URLs |
| 5 | 2026-09-10 | `develop` | Limpieza visual de clientes, comisiones y categorización de tipos |
| 6 | 2026-10-09 | `feature/IS2GE-105` | Reset limpio de rama de trabajo y diseño de arquitectura Cloud |
| 7 | 2026-10-09 | `feature/IS2GE-105` | Landing de bienvenida (`InicioModule`) y ajuste de navegación post-login |
| 8 | 2026-10-10 | `feature/IS2GE-105` | Filtro de roles de staff en Clientes y depuración en Denominaciones |
| 9 | 2026-10-10 | `feature/IS2GE-105` | Refactorización de Denominaciones y corrección de sintaxis JSX |
| 10 | 2026-10-10 | `feature/IS2GE-105` | Eliminación de validación de medio de pago en Compra de Divisas |
| 11 | 2026-10-10 | `feature/IS2GE-105` | Validación de denominaciones en Venta de Divisas y fix de cierre de caja |
| 12 | 2026-10-10 | `develop` | Integración segura de la rama `feature/IS2GE-105` en `develop` |
| 13 | 2026-10-11 | `develop` | Configuración y automatización de dependencias de Stripe |
| 14 | 2026-10-12 | `develop` | Diagnóstico y solución a fallo de túneles Cloudflare (DNS en Docker) |

---

## 1. Diagnóstico y configuración inicial del entorno local

- **Fecha:** 29 de agosto de 2026
- **Rama:** `develop`
- **Sesión ID:** `a759d684-2cc3-48fa-a237-1415df30c7c3`

### Contexto

Lucas clonó el repositorio en un equipo con Windows 11 y requería verificar que todas las
herramientas de soporte (Docker Desktop con WSL2, Python 3.12, Node.js 22) estuvieran
correctamente alineadas con los requerimientos del proyecto antes de levantar los servicios
de backend, frontend y Keycloak.

### Qué se le pidió a la IA

- Revisar la estructura del repositorio y diagnosticar qué dependencias faltaban en Windows.
- Verificar las versiones instaladas en el sistema anfitrión.
- Generar y configurar los archivos `.env` a partir de las plantillas de ejemplo.
- Guiar en la instalación de dependencias y ejecución de las migraciones de Django.

### Qué se hizo

- Se validaron las herramientas de la máquina anfitriona:
  - Python 3.12.5 en entorno virtual (`backend/venv`).
  - Node.js v22.4.1 y npm v10.8.2.
  - Docker v27.0.3 con motor Docker Compose v2.28.
- Se configuraron los archivos de entorno no versionados a partir de los ejemplos:
  - Creación de `keycloak/.env` con credenciales de administración (`KEYCLOAK_ADMIN`, `KEYCLOAK_ADMIN_PASSWORD`, `KC_DB_PASSWORD`).
  - Creación de `backend/.env` con `DJANGO_SECRET_KEY`, `DEBUG=True`, `KEYCLOAK_SERVER_URL=http://localhost:8080`, `OIDC_RP_CLIENT_ID` y `OIDC_RP_CLIENT_SECRET`.
- Se instalaron las dependencias del backend con `pip install -r requirements.txt`.
- Se instalaron las dependencias del frontend con `npm install` dentro de `frontend/`.
- Se levantó la base de datos PostgreSQL de Keycloak mediante Docker Compose.
- Se ejecutaron las migraciones iniciales de Django con `python manage.py migrate`.

### Qué se descartó y por qué

- No se utilizó SQLite para Keycloak porque la arquitectura del proyecto estipula PostgreSQL dedicado para el servidor de identidades.
- No se instalaron paquetes globales en Windows para no contaminar el sistema operativo fuera del entorno virtual.
- No se versionaron contraseñas en Git; se mantuvieron estrictamente en los `.env` locales ignorados por `.gitignore`.

### Verificación

- Las migraciones de Django finalizaron con estado `OK` en todas las apps (`auth`, `contenttypes`, `sessions`, `clientes`, `caja`).
- El contenedor de Postgres para Keycloak quedó en estado `Up` y escuchando conexiones.
- El servidor de desarrollo de Vite levantó sin advertencias en `http://localhost:5173`.

### Queda abierto

- Alta inicial del realm `global-exchange` y de los clientes OIDC dentro de Keycloak.

---

## 2. Corrección de error de exportación TypeScript en ClientesModule

- **Fecha:** 29 de agosto de 2026
- **Rama:** `develop`
- **Sesión ID:** `b1685b65-4581-4c6e-bcf2-a0d9d2345d90`

### Contexto

Al iniciar el servidor de desarrollo del frontend o intentar una compilación preliminar
con TypeScript, el proceso se interrumpía con un error de sintaxis en
`frontend/src/components/ClientesModule.tsx`:
`TS2323: Cannot redeclare exported variable 'default'`.

### Qué se le pidió a la IA

- Identificar la causa exacta del error de compilación en `ClientesModule.tsx`.
- Corregir la doble exportación sin romper las importaciones existentes en `App.tsx` o `DashboardLayout.tsx`.
- Validar el tipado de las interfaces asociadas.

### Qué se hizo

- Se inspeccionó el archivo `frontend/src/components/ClientesModule.tsx`.
- Se encontró que el componente estaba declarado como `export default function ClientesModule() { ... }` y, adicionalmente, al final del archivo existía una segunda cláusula `export default ClientesModule;`.
- Se eliminó la línea redundante final, dejando una única exportación por defecto limpia y estándar.
- Se verificó la consistencia de las interfaces TypeScript `ICliente` y `ClienteTipo`.

### Qué se descartó y por qué

- No se cambió a exportación nombrada (`export { ClientesModule }`) porque los módulos consumidores ya utilizaban importaciones por defecto (`import ClientesModule from './components/ClientesModule'`), lo que habría forzado refactorizaciones innecesarias.

### Verificación

- Se ejecutó `npx tsc --noEmit` en la carpeta `frontend/`, finalizando con código de salida 0.
- El módulo cargó correctamente en el navegador con Hot Module Replacement (HMR).

### Queda abierto

- Reemplazar los datos estáticos de clientes por la llamada a la API REST de Django.

---

## 3. Puesta en marcha según Guía de Entorno y fix de base de datos de Keycloak

- **Fecha:** 30 de agosto de 2026
- **Rama:** `develop`
- **Sesión ID:** `6e552d7f-38c5-4128-a80e-532f71b080cb`

### Contexto

Al intentar arrancar los contenedores de Keycloak siguiendo `docs/guia_entorno.md`, Keycloak
no lograba iniciar y quedaba reiniciándose continuamente. Los logs indicaban:
`FATAL: password authentication failed for user "keycloak"`. El volumen de Docker conservaba
la contraseña antigua creada en un inicio previo, incompatible con el `.env` actual.

### Qué se le pidió a la IA

- Diagnosticar el motivo por el cual Keycloak no podía conectarse a su PostgreSQL.
- Restablecer la base de datos de Keycloak sin comprometer la configuración de Django.
- Lograr que Keycloak quede accesible en el puerto 8080 y Django en el 8000.

### Qué se hizo

- Se revisaron los logs del contenedor con `docker compose -f keycloak/docker-compose.yml logs postgres`.
- Se constató que PostgreSQL inicializa las credenciales del superusuario únicamente en la primera creación del volumen de datos (`keycloak_postgres_data`). Al cambiar la contraseña en `.env`, el volumen persistente conservaba la clave vieja.
- Se ejecutó un derribo completo con limpieza de volúmenes:
  `docker compose -f keycloak/docker-compose.yml down -v`.
- Se recreó el servicio desde cero con `docker compose -f keycloak/docker-compose.yml up -d`.
- Se verificó la inicialización de tablas de Keycloak hasta que el log confirmó: `Keycloak 24.x started on http://0.0.0.0:8080`.
- Se levantó el backend de Django en otra terminal: `python manage.py runserver 8000`.

### Qué se descartó y por qué

- No se modificaron los archivos de Docker Compose para omitir contraseñas o permitir autenticación `trust`, ya que configuraciones inseguras impiden la homologación posterior.
- No se borraron imágenes Docker, ahorrando tiempo de descarga innecesario.

### Verificación

- El panel administrativo de Keycloak respondió con código HTTP 200 en `http://localhost:8080/admin`.
- Django inició sin excepciones de base de datos ni caídas de servicio.

### Queda abierto

- Creación del realm de la aplicación y configuración de proveedores de identidad.

---

## 4. Depuración de autenticación OIDC (HTTP 401) y mapeo de URLs

- **Fecha:** 10 de septiembre de 2026
- **Rama:** `develop`
- **Sesión ID:** `ea91fada-a1b6-4e01-b402-7644591f70a2`

### Contexto

Durante la integración de inicio de sesión único con Keycloak, el backend de Django
rechazaba la respuesta de autenticación en la URL `/oidc/callback/` arrojando un error
HTTP 401 (`Invalid client or client credentials` en `mozilla-django-oidc`). Además, se
necesitaba un mapa completo de todas las rutas habilitadas en el sistema para probar
las APIs.

### Qué se le pidió a la IA

- Diagnosticar por qué fallaba el intercambio del código de autorización por el token JWT.
- Proveer la lista integral de endpoints registrados en el proyecto Django.
- Resolver el error 401 y dejar el login funcional.

### Qué se hizo

- Se examinó `backend/settings.py` verificando `OIDC_RP_CLIENT_ID`, `OIDC_RP_CLIENT_SECRET` y los endpoints del proveedor OpenID.
- Se inspeccionó la configuración del cliente en Keycloak y se detectó que el cliente estaba configurado como público (sin credenciales de cliente) mientras que Django enviaba autenticación confidencial, o bien el secret generado en Keycloak no coincidía con `backend/.env`.
- Se configuró el cliente en Keycloak con Client Authentication activado (`Confidential`), se generó un nuevo Secret y se actualizó en `backend/.env`.
- Se generó el catálogo completo de rutas del backend mediante inspección de los módulos `urls.py`:
  - `/admin/`: consola administrativa de Django.
  - `/oidc/`: rutas de autenticación (`login/`, `callback/`, `logout/`).
  - `/api/caja/`: endpoints de apertura, transacciones, arqueo y cierre.
  - `/api/clientes/`: endpoints de consulta y gestión de clientes.
  - `/api/tasas/`: cotizaciones de divisas.
- Se reinició el proceso de Django.

### Qué se descartó y por qué

- No se sustituyó el flujo OIDC por autenticación básica de Django basada en cookies de sesión estándar, ya que el requerimiento de la cátedra exige Keycloak centralizado.

### Verificación

- Se realizó un flujo completo en el navegador: redirección al formulario de login de Keycloak, ingreso de credenciales de usuario de prueba y redirección exitosa a `/oidc/callback/` terminando en el frontend autenticado.

### Queda abierto

- Mapeo automático de roles de Keycloak (`admin`, `cajero`, `analista`) a los permisos del modelo de usuario en Django.

---

## 5. Limpieza visual de clientes, comisiones y categorización de tipos

- **Fecha:** 10 de septiembre de 2026
- **Rama:** `develop`
- **Sesión ID:** `c6b53bc8-5884-4932-a9bc-2ab597736d21`

### Contexto

En el frontend, los selectores y tarjetas de clientes mostraban cadenas antiestéticas con
identificadores UUID entre paréntesis junto al nombre (ej. `"Carlos Gómez (d4e1-98ab-...)`").
Asimismo, las comisiones y márgenes comerciales según la categoría del cliente
(Minorista, Mayorista, VIP) no estaban calculadas ni aplicadas en la interfaz de operaciones.

### Qué se le pidió a la IA

- Ocultar los identificadores técnicos o hashes del renderizado de nombres de clientes.
- Implementar la lógica de comisiones por tipo de cliente: Minorista (5%), Mayorista (10%), VIP (15%).
- Actualizar de forma reactiva la tasa y el total de la operación al cambiar el cliente seleccionado.

### Qué se hizo

- En `frontend/src/components/ClientesModule.tsx`:
  - Se modificó la función de formateo para renderizar únicamente `nombre` y `apellido` (o `razon_social`).
  - Se incorporaron badges de color diferenciados según el tipo de cliente (`VIP` dorado, `Mayorista` azul, `Minorista` gris).
- En `frontend/src/lib/clientRates.ts`:
  - Se definieron los márgenes comerciales oficiales:
    - Minorista: 5% de spread sobre cotización base.
    - Mayorista: 10% de beneficio de escala.
    - VIP: 15% de descuento/beneficio preferencial.
  - Se implementó la función `calculateClientRate` para ajustar dinámicamente el precio de compra y venta.
- Se vinculó el cliente seleccionado con el estado global de la cotización en pantalla.

### Qué se descartó y por qué

- No se eliminó el ID de los objetos en memoria; el ID se preservó como clave primaria interna (`value` del `<select>`) para persistir transacciones sin ambigüedades.
- No se calcularon márgenes fijos en el frontend sin considerar la divisa transaccionada.

### Verificación

- La interfaz mostró los nombres limpios en la lista y en los desplegables.
- Al alternar entre un cliente Minorista y uno VIP, el desglose de cotización ajustó la tasa inmediatamente reflejando el 15% de beneficio.

### Queda abierto

- Sincronización de los márgenes comerciales desde una tabla administrable en la base de datos de Django.

---

## 6. Reset limpio de rama feature/IS2GE-105 y diseño de arquitectura Cloud

- **Fecha:** 9 de octubre de 2026
- **Rama:** `feature/IS2GE-105`
- **Sesión ID:** `32a2a744-afa8-4fbe-a2d7-0ea525dfb7af`

### Contexto

La rama de trabajo `feature/IS2GE-105` presentaba múltiples archivos temporales, logs y
modificaciones no commiteadas generadas durante pruebas de caja. Lucas necesitaba volver
a un estado limpio antes de continuar el desarrollo y, además, solicitó una propuesta de
arquitectura para desplegar toda la solución en la nube sin incurrir en costos elevados.

### Qué se le pidió a la IA

- Limpiar por completo el árbol de trabajo de Git descartando cambios basura.
- Detener todos los contenedores Docker en ejecución para liberar memoria RAM.
- Elaborar un plan técnico detallado para desplegar PostgreSQL, Keycloak, Django y Vite en servicios Cloud gratuitos o accesibles.

### Qué se hizo

- Se limpió el repositorio local con:
  `git reset --hard HEAD` y `git clean -fd`.
- Se detuvieron los contenedores con `docker compose down`.
- Se diseñó un plan de despliegue Cloud desacoplado:
  - **Base de datos:** Supabase o Neon (PostgreSQL gestionado con SSL).
  - **Identidad (Keycloak):** Render Web Service con Dockerfile oficial, configurando las variables de base de datos de Supabase.
  - **Backend (Django):** Render o Railway ejecutado con `gunicorn`, configurando `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS` y variables seguras.
  - **Frontend (React/Vite):** Vercel o Cloudflare Pages con compilación estática conectada al dominio del backend.
  - Esquema de certificados HTTPS y configuración de CORS.

### Qué se descartó y por qué

- Se descartaron arquitecturas basadas en Kubernetes (AWS EKS / GKE) por su alta sobrecarga de configuración y costos incompatibles con el alcance de la materia.
- No se ejecutó el despliegue de inmediato para no desviar el foco antes de terminar las pantallas operativas del Hito.

### Verificación

- `git status` confirmó que el árbol de trabajo quedó completamente limpio (`nothing to commit, working tree clean`).
- Los puertos de red ocupados por Docker quedaron liberados en el sistema anfitrión.

### Queda abierto

- Puesta en producción real una vez integradas las funcionalidades de caja y facturación.

---

## 7. Landing de bienvenida (InicioModule) y ajuste de navegación post-login

- **Fecha:** 9 de octubre de 2026
- **Rama:** `feature/IS2GE-105`
- **Sesión ID:** `4263130d-5125-406c-863e-0ea3abbcfeb6`

### Contexto

Al iniciar sesión exitosamente, la aplicación dirigía al usuario directamente al módulo de
caja o a formularios de operaciones sin una vista principal de bienvenida que situara
al usuario en su contexto de trabajo (nombre del operador, sucursal, rol y accesos rápidos
según sus privilegios).

### Qué se le pidió a la IA

- Diseñar e implementar un nuevo componente de bienvenida (`InicioModule.tsx`).
- Incluir un hero banner moderno con saludo personalizado, fecha en tiempo real y rol activo.
- Añadir tarjetas de acceso rápido para Cajero, Administrador y Analista.
- Ajustar la navegación principal para que la vista por defecto tras el login sea "Inicio".

### Qué se hizo

- Se creó el componente `frontend/src/components/InicioModule.tsx`:
  - Hero banner con gradiente oscuro, saludo dinámico ("Buenos días" / "Buenas tardes"), nombre del usuario y badge del rol.
  - Grid de accesos rápidos con iconos ilustrativos:
    - *Módulo de Caja:* Apertura, arqueo y cierre.
    - *Operaciones:* Compra y venta de divisas.
    - *Clientes:* Consulta y alta de clientes comerciales.
    - *Tasas y Denominaciones:* Administración cambiaria.
  - Panel informativo con estado de la caja del día y atajos a la documentación.
- Se actualizó `frontend/src/components/DashboardLayout.tsx`:
  - Se estableció el tab `'inicio'` como estado inicial de la aplicación.
  - Se añadió la pestaña "Inicio" a la barra de navegación superior/lateral.

### Qué se descartó y por qué

- No se eliminaron los menús de navegación directa del layout; la landing complementa la barra de navegación permitiendo una experiencia más intuitiva para usuarios nuevos.

### Verificación

- Se navegó en el frontend: tras recargar la aplicación, el usuario aterriza en la vista de bienvenida con sus tarjetas operativas funcionando como disparadores de cambio de módulo.

### Queda abierto

- Conectar las tarjetas de resumen de caja con el endpoint de métricas reales del día.

---

## 8. Filtro de roles de staff en Clientes y depuración en Denominaciones

- **Fecha:** 10 de octubre de 2026
- **Rama:** `feature/IS2GE-105`
- **Sesión ID:** `11006841-ceb1-49f3-b49c-07bd2ad246bd`

### Contexto

En la pantalla de gestión de Clientes aparecían listadas cuentas internas del sistema
(usuarios con rol `admin`, `cajero` o `analista`), mezclando empleados con clientes
comerciales. Paralelamente, en la tabla de Denominaciones existía una columna llamada
"Representación" que mostraba texto redundante y generaba confusión visual.

### Qué se le pidió a la IA

- Excluir a los usuarios con roles internos (`admin`, `cajero`, `analista`) del módulo y selectores de clientes.
- Eliminar la columna "Representación" de la tabla de Denominaciones en el frontend.
- Modificar el backend para serializar o filtrar adecuadamente las cuentas internas.

### Qué se hizo

- En `backend/clientes/views.py`:
  - Se ajustó el queryset del endpoint de clientes para no incluir usuarios vinculados a roles de staff cuando se consultan clientes para operaciones cambiarias.
- En `frontend/src/components/ClientesModule.tsx`:
  - Se reforzó el filtrado en cliente: descarte explícito de cualquier registro cuyo rol coincida con roles de personal operativo interno.
- En `frontend/src/components/DenominacionesModule.tsx`:
  - Se removió la columna `<th>Representación</th>` y su celda `<td>` correspondiente.
  - Se redistribuyó el ancho de las columnas (Moneda, Valor Nominal, Tipo de Billete/Moneda, Acciones).

### Qué se descartó y por qué

- No se borraron los usuarios administradores de la base de datos; simplemente se los excluyó de la lógica comercial de clientes de divisas.
- No se alteró el modelo de base de datos de Denominaciones; únicamente se limpió la capa visual innecesaria.

### Verificación

- La lista de clientes reflejó únicamente a los clientes finales y empresas.
- La tabla de denominaciones quedó limpia y sin columnas sobrantes.

### Queda abierto

- Impedir que se creen clientes comerciales con el mismo correo electrónico de un usuario del staff.

---

## 9. Refactorización de Denominaciones y corrección de sintaxis JSX

- **Fecha:** 10 de octubre de 2026
- **Rama:** `feature/IS2GE-105`
- **Sesión ID:** `277c0317-6646-4170-a9ed-42b495bb49a0`

### Contexto

El componente `DenominacionesModule.tsx` presentaba dos problemas graves: fallaba al
compilar en Vite debido a un comentario con formato HTML estándar (`<!-- comentario -->`)
empotrado dentro del render de React JSX, y contaba con un flujo de "Modificar" que
permitía cambiar el valor nominal de billetes existentes, generando riesgos de desbalanceo
en arqueos de caja previos.

### Qué se le pidió a la IA

- Corregir el error de sintaxis que bloqueaba la compilación de Vite.
- Eliminar el botón y modal de "Modificar" denominaciones, dejando exclusivamente la creación y eliminación.
- Cambiar el campo de texto libre para buscar monedas por un `<select>` desplegable con las monedas disponibles en el sistema.

### Qué se hizo

- Se corrigió el error sintáctico reemplazando los comentarios HTML por la convención de JSX `{/* ... */}` y limpiando marcadores obsoletos.
- Se refactorizó `DenominacionesModule.tsx`:
  - Se removió el botón "Modificar", el modal de edición y los estados asociados (`editingDenominacion`).
  - Las denominaciones quedaron conceptualizadas como registros inmutables: si un valor facial no es válido, se da de baja y se crea uno nuevo.
- Se reemplazó el input de búsqueda de moneda por un selector desplegable `<select>` que lista las divisas activas (`USD`, `EUR`, `BRL`, `ARS`), facilitando la carga sin errores tipográficos.

### Qué se descartó y por qué

- No se permitió la edición en caliente del valor numérico de una denominación ya que billetes con arqueos anteriores perderían consistencia contable histórica.

### Verificación

- Vite compiló sin errores en tiempo real.
- El selector desplegable filtró las denominaciones de forma inmediata sin permitir strings inválidos.

### Queda abierto

- Agregar una advertencia de confirmación antes de eliminar una denominación si hay cajas con saldo existente en esa moneda.

---

## 10. Eliminación de validación de medio de pago en Compra de Divisas

- **Fecha:** 10 de octubre de 2026
- **Rama:** `feature/IS2GE-105`
- **Sesión ID:** `c9e100e4-a70b-4564-b7ab-290d083fd4e5`

### Contexto

En el flujo de Compra de Divisas (`CompraDivisasModule.tsx`), un banner bloqueaba la
operación indicando que el cliente no tenía medios de pago registrados ("Debe registrar al
menos un medio de pago"). Esto impedía realizar compras en efectivo en ventanilla,
que constituye el caso de uso central de una casa de cambio.

### Qué se le pidió a la IA

- Quitar la exigencia obligatoria de registrar medios de pago bancarios para la compra de divisas.
- Eliminar el banner de alerta bloqueante en el frontend.
- Permitir que el botón de confirmación se habilite seleccionando únicamente cliente, moneda y monto.
- Adaptar el endpoint de caja en Django para aceptar operaciones directas de contado.

### Qué se hizo

- En `frontend/src/components/CompraDivisasModule.tsx`:
  - Se eliminó el renderizado condicional del banner de advertencia.
  - Se flexibilizó la condición de deshabilitación del botón: ahora sólo exige `clienteSeleccionado && monto > 0 && moneda`.
  - Se limpió el prop huérfano `onAddPaymentMethod`.
- En `backend/caja/api.py`:
  - Se ajustó la validación del payload: si el medio de pago viene nulo o no especificado, se imputa automáticamente a la cuenta de efectivo de la caja abierta del operador.

### Qué se descartó y por qué

- No se eliminó el soporte de pagos por transferencia o tarjeta en la base de datos; únicamente se eliminó su carácter mandatorio para operaciones de ventanilla.

### Verificación

- Se registró una compra de 200 USD seleccionando a un cliente sin cuentas bancarias asociadas; la transacción fue aceptada y asentada en el libro de caja con código HTTP 201.

### Queda abierto

- Integrar la impresión del recibo de compra en formato PDF.

---

## 11. Validación de denominaciones en Venta de Divisas y fix de cierre de caja

- **Fecha:** 10 de octubre de 2026
- **Rama:** `feature/IS2GE-105`
- **Sesión ID:** `b0567155-8ac3-4455-a9f8-248083d1b928`

### Contexto

En la pantalla de Venta de Divisas (`OperacionCajaForm.tsx`), el operador podía elegir
monedas que no tenían denominaciones cargadas en el catálogo, lo que provocaba un crash al
llegar al desglose de billetes entregados. Al mismo tiempo, al procesar el cierre de caja,
el backend disparaba una excepción no capturada:
`AttributeError: 'NoneType' object has no attribute 'id'` al evaluar `apertura_obj.id`.

### Qué se le pidió a la IA

- Corregir la excepción `AttributeError` en el backend al intentar cerrar una caja ya cerrada o sin apertura activa.
- Deshabilitar en el selector de Venta de Divisas aquellas monedas sin denominaciones activas, agregando la leyenda explícita `(Sin Denominaciones)`.

### Qué se hizo

- En `backend/caja/api.py`:
  - Se corrigió la consulta de la apertura activa de caja:
    ```python
    apertura_obj = AperturaCaja.objects.filter(cajero=user, estado='ABIERTA').first()
    if not apertura_obj:
        return Response({'detail': 'No hay una apertura de caja activa para este cajero.'}, status=status.HTTP_400_BAD_REQUEST)
    ```
  - Se garantizó que el ID sólo se acceda tras comprobar que la instancia no es nula.
- En `frontend/src/components/OperacionCajaForm.tsx`:
  - Se cruzó el estado de monedas con el mapa de denominaciones cargadas.
  - Se aplicó el atributo `disabled={!tieneDenominaciones}` a las opciones del `<select>` de monedas, agregando el sufijo `(Sin Denominaciones)` para las divisas no operables.

### Qué se descartó y por qué

- No se ocultaron las monedas sin denominaciones para no confundir al cajero respecto a si la divisa estaba registrada en el sistema; mantenerlas visibles pero deshabilitadas comunica claramente la causa del bloqueo.

### Verificación

- El cierre de caja ejecutó limpiamente retornando HTTP 200 y mensaje de confirmación.
- En el formulario de venta, divisas sin stock de billetes cargados no pudieron ser seleccionadas.

### Queda abierto

- Notificación automática al rol de Analista para que cargue denominaciones de divisas nuevas.

---

## 12. Integración de rama de trabajo feature/IS2GE-105 a develop

- **Fecha:** 10 de octubre de 2026
- **Rama:** `develop` (desde `feature/IS2GE-105`)
- **Sesión ID:** `7abfd496-7cc0-4b32-b9ca-165f4625c38d`

### Contexto

Habiéndose completado y probado todas las modificaciones y correcciones en la rama
`feature/IS2GE-105` (bienvenida, denominaciones, compra en efectivo, cierre de caja y filtros),
era necesario integrar todo el trabajo en la rama principal de desarrollo `develop`
manteniendo la trazabilidad del historial.

### Qué se le pidió a la IA

- Revisar los commits y archivos modificados entre ambas ramas.
- Conducir el merge de `origin/feature/IS2GE-105` sobre `develop`.
- Resolver cualquier conflicto potencial y verificar el estado final del repositorio.

### Qué se hizo

- Se comprobó la limpieza del árbol de trabajo local con `git status`.
- Se cambió a la rama de desarrollo: `git checkout develop`.
- Se actualizaron los cambios remotos con `git pull origin develop`.
- Se ejecutó el merge: `git merge origin/feature/IS2GE-105`.
- Git resolvió la integración automáticamente usando la estrategia `ort`, generando el commit de merge `9af565a`.
- Se confirmó que no quedaron marcadores de conflicto (`<<<<<<<`) ni archivos desalineados.

### Qué se descartó y por qué

- No se realizó un rebase interactivo ni force push sobre `develop` para preservar los commits y la cronología original del equipo de desarrollo.

### Verificación

- `git log --graph --oneline -n 6` mostró la convergencia de `feature/IS2GE-105` en `develop`.
- Tanto el backend como el frontend levantaron y compilaron sin errores tras el merge.

### Queda abierto

- Etiquetado (tag) formal del hito en Git.

---

## 13. Configuración y automatización de dependencias de Stripe

- **Fecha:** 11 de octubre de 2026
- **Rama:** `develop`
- **Sesión ID:** `db12da72-88e8-479b-863b-f678ff20fd28`

### Contexto

Para la integración de cobros digitales y transferencias en línea, se incorporó el SDK de
Stripe tanto en el backend como en el frontend. Se requería estandarizar las dependencias,
documentar las claves de prueba y automatizar su instalación en el script unificado de
arranque `levantar_todo.py`.

### Qué se le pidió a la IA

- Añadir la biblioteca `stripe` a los requerimientos de Python y `@stripe/stripe-js` al frontend.
- Documentar las variables de entorno en `.env.example`, `backend/.env.example` y `.env.prod.example`.
- Modificar `levantar_todo.py` para que verifique si los paquetes de Stripe están instalados y, de faltar, los instale automáticamente sin intervención manual.

### Qué se hizo

- En `backend/requirements.txt`: se agregó `stripe>=8.0.0`.
- En `frontend/package.json`: se incorporó `@stripe/stripe-js`.
- Se incluyeron las variables en los archivos `.env.example`:
  - `STRIPE_PUBLIC_KEY=pk_test_...`
  - `STRIPE_SECRET_KEY=sk_test_...`
  - `STRIPE_WEBHOOK_SECRET=whsec_...`
- En `levantar_todo.py`:
  - Se agregó una rutina de comprobación que ejecuta `python -c "import stripe"` y lanza `pip install stripe` en el venv si arroja `ModuleNotFoundError`.
  - Se añadió comprobación en frontend verificando la presencia de `@stripe/stripe-js` en `node_modules` e invocando `npm install` si no se detecta.

### Qué se descartó y por qué

- No se incluyeron claves reales de la cuenta de Stripe en los archivos versionados.
- No se fuerza la reinstalación indiscriminada de dependencias en cada arranque; se diseñó una verificación condicional rápida para no demorar el inicio habitual.

### Verificación

- Se ejecutó `python levantar_todo.py` en un entorno donde no estaba instalado Stripe: el script detectó la ausencia, realizó la instalación y levantó los servicios sin fallas.

### Queda abierto

- Configurar el webhook de Stripe en producción con endpoints accesibles desde internet.

---

## 14. Diagnóstico y solución a fallo de túneles Cloudflare (DNS en Docker)

- **Fecha:** 12 de octubre de 2026
- **Rama:** `develop`
- **Sesión ID:** `cbc447e3-d28d-4e17-8817-dbc11e29d50c`

### Contexto

Al intentar exponer la aplicación a internet mediante el script `publicar.py` y el archivo
`docker-compose.publico.yml` (utilizando Cloudflare Quick Tunnels para Keycloak, backend y
frontend), los contenedores de `cloudflared` fallaban al iniciar con el siguiente error:
`failed to request quick Tunnel: Post "https://api.trycloudflare.com/...": dial tcp: lookup api.trycloudflare.com on 127.0.0.11:53: no such host`.

### Qué se le pidió a la IA

- Determinar la causa por la cual los contenedores no podían resolver el dominio de Cloudflare.
- Resolver el fallo de resolución DNS sin romper la red interna de Docker.
- Conseguir que se generen las tres URLs públicas accesibles desde internet.

### Qué se hizo

- Se identificó que Docker Desktop en Windows con backend WSL2 presenta intermitencias en su servidor DNS embebido (`127.0.0.11:53`), no reenviando las peticiones a los DNS del anfitrión.
- Se editó `docker-compose.publico.yml`:
  - Se configuraron servidores DNS públicos explícitos (`1.1.1.1` y `8.8.8.8`) en los servicios de túnel y en el backend:
    ```yaml
    dns:
      - 1.1.1.1
      - 8.8.8.8
    ```
- Se reejecutó `python publicar.py --demo`.
- Los túneles resolvieron `api.trycloudflare.com` inmediatamente y generaron las URLs `https://*.trycloudflare.com` para cada servicio.

### Qué se descartó y por qué

- No se reemplazó Cloudflare por servicios de túnel de pago ni se recurrió a ngrok (que requiere registrarse y tiene límites estrictos de conexiones gratuitas).
- No se modificaron los adaptadores de red de Windows de forma manual, garantizando que el proyecto sea portable a cualquier otra máquina clonada.

### Verificación

- Los tres contenedores de túnel se conectaron en menos de 2 segundos.
- Se accedió desde un teléfono móvil fuera de la red local a la URL pública del frontend y se comprobó la carga del sistema.

### Queda abierto

- Actualizar dinámicamente los Redirect URIs en Keycloak cuando los túneles temporales generen nuevos nombres de dominio aleatorios al reiniciar.

---

## 15. Estado consolidado de nuestro trabajo

### Cambios principales realizados en conjunto

- **Configuración y Estabilidad de Entornos:**
  - Diagnóstico inicial completo de dependencias en Windows (Docker, Python 3.12, Node.js 22).
  - Normalización de plantillas de entorno (`keycloak/.env.example`, `backend/.env.example`).
  - Reseteo limpio de bases de datos inconsistentes de Keycloak mediante volúmenes Docker.
- **Autenticación y Seguridad:**
  - Puesta a punto del flujo OpenID Connect (OIDC) entre Django y Keycloak con resolución de errores HTTP 401.
  - Saneamiento y protección de credenciales sensibles sin subirlas al control de versiones.
- **Experiencia de Usuario e Interfaz (Frontend):**
  - Corrección de bugs de TypeScript y sintaxis JSX en `ClientesModule.tsx` y `DenominacionesModule.tsx`.
  - Construcción del nuevo módulo de bienvenida institucional `InicioModule.tsx` con accesos rápidos.
  - Limpieza de IDs técnicos en listas de clientes e incorporación de badges por nivel comercial.
  - Definición de comisiones y márgenes comerciales diferenciados (Minorista 5%, Mayorista 10%, VIP 15%).
  - Refactorización de Denominaciones: eliminación de la edición insegura in situ y agregado de filtros por divisa.
- **Lógica de Negocio y Operaciones de Caja:**
  - Habilitación de compra directa de divisas de ventanilla en efectivo, eliminando bloqueos innecesarios por medios de pago bancarios.
  - Deshabilitación preventiva en venta de divisas de aquellas monedas que no posean stock de denominaciones.
  - Corrección de excepción `AttributeError` en el cierre de caja de Django.
- **Integración y Despliegue:**
  - Merge exitoso y limpio de la rama `feature/IS2GE-105` en `develop`.
  - Automatización de la instalación de dependencias de Stripe en `levantar_todo.py`.
  - Corrección de resolución DNS en túneles Cloudflare para publicación a internet en Docker Windows.
  - Diseño de la arquitectura de despliegue en la nube (Render, Supabase, Vercel).

### Reglas técnicas y metodológicas aplicadas

- **No destrucción de código funcional:** Toda refactorización preservó las funciones operativas previas.
- **Aislamiento de credenciales:** Ningún secreto, token o clave privada de Stripe/Keycloak se persistió en Git.
- **Prioridad a la experiencia del usuario:** Errores confusos o datos crudos de base de datos fueron reemplazados por mensajes claros y badges visuales.
- **Inmutabilidad contable:** Los registros que impactan en arqueos de dinero (como valores de billetes de denominaciones) no admiten mutación arbitraria.
- **Automatización continua:** Los scripts de asistencia (`levantar_todo.py`, `publicar.py`) resuelven de forma desatendida las dependencias faltantes para facilitar el trabajo del equipo.

### Pendientes finales identificados

- Configuración de webhooks de producción para la conciliación asíncrona de pagos de Stripe.
- Automatización del refresco de Redirect URIs en Keycloak cuando se generan túneles Cloudflare efímeros.
- Implementación de la impresión y exportación en formato PDF de comprobantes de compra/venta de divisas.
- Ejecución del plan de despliegue Cloud en Supabase y Render para la entrega final del proyecto.
