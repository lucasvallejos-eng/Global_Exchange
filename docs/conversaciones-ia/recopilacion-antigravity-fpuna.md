# Recopilación de conversaciones con IA — Lucas Vallejos (Google Antigravity / Gemini) — Cuenta FPUNA

- **Proyecto:** Global Exchange
- **Repositorio:** `lucasvallejos-eng/Global_Exchange`
- **Integrante:** Lucas Vallejos (`lucasvallejos070@fpuna.edu.py`)
- **Asistente:** Google Antigravity (Gemini)
- **Período:** 29 de agosto al 19 de octubre de 2026

---

## Criterio de recopilación

Este documento reúne de manera íntegra, cronológica y exhaustiva todas las conversaciones técnicas
mantenidas exclusivamente entre **Lucas Vallejos** (`lucasvallejos070@fpuna.edu.py`) y el asistente
**Google Antigravity (Gemini)** en el marco del desarrollo del proyecto **Global Exchange**.

El propósito de este compendio es documentar formalmente la interacción de pair programming con IA
bajo esta cuenta de trabajo, cumpliendo rigurosamente las directrices del criterio **CHIA**
(Conversaciones con Herramientas de Inteligencia Artificial) de la cátedra de Ingeniería de Software II (FPUNA).
No se incluyen interacciones correspondientes a otros miembros del equipo ni sesiones mantenidas en
otras herramientas externas (como GitHub Copilot CLI o Claude Code), las cuales disponen de sus propios
registros documentados en este mismo directorio.

Cada una de las sesiones se encuentra documentada respetando la estructura estándar:

- **Contexto:** problema técnico, requerimiento de negocio o bloqueo inicial que originó la sesión.
- **Qué se le pidió a la IA:** preguntas, instrucciones y alcances solicitados explícitamente por Lucas.
- **Qué se hizo:** diagnóstico, comandos ejecutados, archivos modificados y soluciones concretas aplicadas.
- **Qué se descartó y por qué:** alternativas analizadas que se rechazaron por motivos de seguridad, arquitectura o buenas prácticas.
- **Verificación:** comprobaciones de funcionamiento, pruebas automáticas, compilación y comandos de validación.
- **Queda abierto:** deudas técnicas, mejoras pendientes o dependencias para fases posteriores.

Las credenciales reales, secretos de producción, firmas y tokens sensibles no se reproducen en este documento,
resguardando la seguridad del sistema y la privacidad de las cuentas utilizadas.

---

## Índice de sesiones

| # | Fecha | Rama | Sesión ID | Tema principal |
|---|---|---|---|---|
| 1 | 2026-08-29 | `develop` | `a759d684-2cc3-48fa-a237-1415df30c7c3` | Diagnóstico y configuración inicial del entorno local (Docker, Python 3.12, Node.js) |
| 2 | 2026-08-29 | `develop` | `b1685b65-4581-4c6e-bcf2-a0d9d2345d90` | Corrección de error de exportación TypeScript en `ClientesModule.tsx` |
| 3 | 2026-08-30 | `develop` | `6e552d7f-38c5-4128-a80e-532f71b080cb` | Puesta en marcha según Guía de Entorno y fix de base de datos de Keycloak |
| 4 | 2026-09-10 | `develop` | `ea91fada-a1b6-4e01-b402-7644591f70a2` | Depuración de autenticación OIDC (HTTP 401) y mapeo de URLs de redirección |
| 5 | 2026-09-10 | `develop` | `c6b53bc8-5884-4932-a9bc-2ab597736d21` | Limpieza visual de clientes, comisiones y categorización por tipo de cliente |
| 6 | 2026-10-09 | `feature/IS2GE-105` | `32a2a744-afa8-4fbe-a2d7-0ea525dfb7af` | Reset limpio de rama de trabajo y diseño de arquitectura Cloud |
| 7 | 2026-10-09 | `feature/IS2GE-105` | `4263130d-5125-406c-863e-0ea3abbcfeb6` | Landing de bienvenida institucional (`InicioModule`) y navegación post-login |
| 8 | 2026-10-10 | `feature/IS2GE-105` | `11006841-ceb1-49f3-b49c-07bd2ad246bd` | Filtro de roles de staff en Clientes y depuración en Denominaciones |
| 9 | 2026-10-10 | `feature/IS2GE-105` | `277c0317-6646-4170-a9ed-42b495bb49a0` | Refactorización de Denominaciones y corrección de sintaxis JSX |
| 10 | 2026-10-10 | `feature/IS2GE-105` | `c9e100e4-a70b-4564-b7ab-290d083fd4e5` | Eliminación de validación de medio de pago en Compra de Divisas |
| 11 | 10/10/2026 | `feature/IS2GE-105` | `b0567155-8ac3-4455-a9f8-248083d1b928` | Validación de denominaciones en Venta de Divisas y corrección de cierre de caja |
| 12 | 2026-10-10 | `develop` | `7abfd496-7cc0-4b32-b9ca-165f4625c38d` | Integración segura de la rama `feature/IS2GE-105` en `develop` |
| 13 | 2026-10-11 | `develop` | `db12da72-88e8-479b-863b-f678ff20fd28` | Configuración y automatización de dependencias de Stripe en `levantar_todo.py` |
| 14 | 2026-10-12 | `develop` | `cbc447e3-d28d-4e17-8817-dbc11e29d50c` | Diagnóstico y solución a fallo de túneles Cloudflare (DNS en Docker Windows) |
| 15 | 2026-10-13 | `develop` | `01f2ca92-c6f2-4a68-9d1d-c527adb1da02` | Consolidación inicial de documentación de interacciones técnicas con IA |
| 16 | 2026-10-16 | `develop` | `c55143db-f017-4b3a-bd9e-5e32f9211168` | Estandarización de recopilación bajo criterio CHIA para Google Antigravity |
| 17 | 2026-10-16 | `develop` | `1b7a5da0-5f77-4b1a-83ec-787e6ead2e80` | Auditoría integral de trazabilidad, ramas y commits desde el Tag v4.0 |
| 18 | 2026-10-19 | `develop` | `22edae2d-a21d-43e2-b5b3-98453edafb68` | Generación y homologación formal del registro de conversaciones para cuenta FPUNA |

---

## 1. Diagnóstico y configuración inicial del entorno local

- **Fecha:** 29 de agosto de 2026
- **Rama:** `develop`
- **Sesión ID:** `a759d684-2cc3-48fa-a237-1415df30c7c3`

### Contexto

Lucas clonó el repositorio en un equipo con Windows 11 y requería verificar que todas las herramientas de soporte (Docker Desktop con backend WSL2, Python 3.12, Node.js 22) estuvieran correctamente alineadas con los requerimientos del proyecto antes de levantar los servicios de backend, frontend y Keycloak.

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

- Configurar el cliente OIDC en Keycloak para obtener el `client_secret` definitivo.

---

## 2. Corrección de error de exportación TypeScript en `ClientesModule`

- **Fecha:** 29 de agosto de 2026
- **Rama:** `develop`
- **Sesión ID:** `b1685b65-4581-4c6e-bcf2-a0d9d2345d90`

### Contexto

Al compilar el frontend con `tsc`, TypeScript arrojaba un error de sintaxis TS2528: `No se puede volver a declarar la variable 'default' exportada` en el archivo `frontend/src/components/ClientesModule.tsx`.

### Qué se le pidió a la IA

- Explicar la causa técnica del error TS2528.
- Solucionar la duplicación de exportación sin perder las declaraciones de interfaces del componente.

### Qué se hizo

- Se inspeccionó el archivo y se detectó que coexistía una declaración en la firma de la función (`export default function ClientesModule`) con una cláusula de exportación final redundante (`export default ClientesModule;`).
- Se removió la exportación final duplicada y se preservó una única exportación por defecto en la función principal del componente.
- Se aseguraron los tipos de las interfaces TypeScript para las entidades de clientes y tipos de clientes.

### Qué se descartó y por qué

- No se relajó la comprobación estricta del compilador de TypeScript en `tsconfig.json`, garantizando la calidad del tipado.
- No se convirtió el archivo a JavaScript estándar (`.jsx`), manteniendo la base de código consistente en TypeScript.

### Verificación

- Se ejecutó `npm run build` en el directorio `frontend/`.
- El proceso de compilación de Vite y TypeScript finalizó limpiamente con código de salida `0` y sin advertencias.

---

## 3. Puesta en marcha según Guía de Entorno y fix de base de datos de Keycloak

- **Fecha:** 30 de agosto de 2026
- **Rama:** `develop`
- **Sesión ID:** `6e552d7f-38c5-4128-a80e-532f71b080cb`

### Contexto

Siguiendo la Guía de Entorno compartida por el equipo, al levantar el contenedor de PostgreSQL para Keycloak surgía un conflicto de autenticación (`FATAL: password authentication failed for user "keycloak"`). Esto ocurría porque existía un volumen persistente de Docker previo con credenciales distintas a las especificadas en el archivo `.env`.

### Qué se le pidió a la IA

- Levantar todo el stack siguiendo la guía técnica del proyecto.
- Diagnosticar y resolver el bloqueo de autenticación de PostgreSQL en Keycloak.
- Levantar backend, frontend y Keycloak sincronizados.

### Qué se hizo

- Se identificó la discrepancia entre el volumen existente `keycloak_postgres_data` y las nuevas variables de entorno.
- Se procedió a purgar el volumen persistente desactualizado mediante `docker compose down -v` en la carpeta `keycloak/`.
- Se recrearon los contenedores de Postgres y Keycloak con las credenciales limpias especificadas en `keycloak/.env`.
- Se verificó el arranque de Keycloak en el puerto `8080`.
- Se corrieron las migraciones de Django y se inició el backend en `http://localhost:8000` y el frontend en `http://localhost:5173`.

### Qué se descartó y por qué

- No se cambiaron las contraseñas del `.env` a valores arbitrarios antiguos para no romper la estandarización fijada en la Guía de Entorno.
- No se levantó Keycloak con base H2 embebida, preservando la compatibilidad con PostgreSQL.

### Verificación

- Keycloak inició satisfactoriamente y la consola de administración respondió en `http://localhost:8080/admin`.
- Django conectó sin errores y Vite sirvió la aplicación en el puerto correspondiente.

### Queda abierto

- Mapear los clientes OIDC y exportar el realm para que la configuración no se pierda al reiniciar contenedores.

---

## 4. Depuración de autenticación OIDC (HTTP 401) y mapeo de URLs

- **Fecha:** 10 de septiembre de 2026
- **Rama:** `develop`
- **Sesión ID:** `ea91fada-a1b6-4e01-b402-7644591f70a2`

### Contexto

Tras completar el `client_secret` en el `.env` del backend, los intentos de login y registro en la aplicación devolvían errores HTTP 401 (Unauthorized) o fallos de redirección inválida en el flujo OpenID Connect (OIDC).

### Qué se le pidió a la IA

- Diagnosticar y solucionar los errores de autenticación OIDC.
- Proveer la lista exacta de URLs de redirección válidas que deben configurarse en la consola de Keycloak.
- Reiniciar el backend y verificar la comunicación interna.

### Qué se hizo

- Se auditó el archivo `backend/.env` y se verificó que el `client_secret` no tuviera espacios ni saltos de línea residuales.
- Se identificó que las URLs de retorno permitidas (*Valid Redirect URIs*) en Keycloak no coincidían con los endpoints de callback de Django:
  - Se configuró `http://localhost:8000/oidc/callback/`.
  - Se configuraron los orígenes web permitidos: `http://localhost:8000` y `http://localhost:5173`.
- Se reinició el servicio de Django para forzar la recarga de las variables de entorno.
- Se ajustó la configuración de sesiones de Django (`SESSION_COOKIE_SAMESITE = 'Lax'`) para evitar el rechazo de cookies de sesión post-redirección de Keycloak.

### Qué se descartó y por qué

- No se deshabilitó la verificación de firma de tokens ni se utilizó autenticación simulada (mock), manteniendo la seguridad OIDC real.
- No se modificó la configuración interna del realm en producción, respetando los estándares de la cátedra.

### Verificación

- Se completó el ciclo completo de autenticación: el navegador redirigió a Keycloak, se ingresaron credenciales, Keycloak emitió el código de autorización y Django intercambió el código por los tokens, estableciendo la sesión del usuario.

### Queda abierto

- Suprimir los identificadores alfanuméricos técnicos en las listas de usuarios del frontend.

---

## 5. Limpieza visual de clientes, comisiones y categorización de tipos

- **Fecha:** 10 de septiembre de 2026
- **Rama:** `develop`
- **Sesión ID:** `c6b53bc8-5884-4932-a9bc-2ab597736d21`

### Contexto

En el frontend, los selectores de usuarios mostraban nombres acompañados de hashes alfanuméricos entre paréntesis (ej. `Usuario de Ejemplo (VW0...)`). Adicionalmente, el desplegable de clientes asociados no consumía dinámicamente los registros de Django, y se requería formalizar la escala de comisiones comerciales según la categoría de cliente.

### Qué se le pidió a la IA

- Eliminar los hashes de los nombres de usuario en todos los desplegables y tablas de la interfaz gráfica.
- Conectar el selector de clientes con la base de datos de Django (`/api/clientes/`).
- Definir la lógica de comisiones diferenciadas por tipo de cliente (Minorista, Mayorista, VIP).
- Brindar comandos para inspeccionar directamente la base de datos SQLite de Django.

### Qué se hizo

- Se refactorizaron los componentes del frontend para formatear las etiquetas de usuario eliminando expresiones regulares que capturaban hashes técnicos.
- Se conectó el selector de cliente activo al endpoint `/api/clientes/`, cargando los clientes asociados al usuario autenticado.
- Se establecieron los márgenes de comisión en la lógica de negocio:
  - **Minorista:** Comisión estándar (5%).
  - **Mayorista:** Comisión preferencial (10%).
  - **VIP:** Comisión de volumen (15%).
- Se incorporaron badges de colores en la tabla de clientes para reflejar visualmente el segmento.
- Se explicó el uso del comando `python manage.py dbshell` y extensiones SQLite para consultar las tablas del backend.

### Qué se descartó y por qué

- No se eliminaron los IDs técnicos del estado interno de React; solo se ocultaron en la capa visual de presentación, preservando la integridad de las peticiones a la API.
- No se hardcodearon las listas de clientes en el frontend.

### Verificación

- La interfaz mostró únicamente nombres legibles.
- Los clientes se cargaron dinámicamente desde el backend y reflejaron sus comisiones correspondientes.

---

## 6. Reset limpio de rama de trabajo y diseño de arquitectura Cloud

- **Fecha:** 9 de octubre de 2026
- **Rama:** `feature/IS2GE-105`
- **Sesión ID:** `32a2a744-afa8-4fbe-a2d7-0ea525dfb7af`

### Contexto

Al iniciar el desarrollo del Hito 5 (módulo de caja e historia IS2GE-105), la rama local contenía modificaciones experimentales previas. Lucas necesitaba limpiar la rama de trabajo sin perder su origen en `develop`, detener procesos en segundo plano y planificar el esquema de despliegue en la nube para las entregas finales.

### Qué se le pidió a la IA

- Limpiar todos los cambios locales en la rama `feature/IS2GE-105` sin eliminar la rama.
- Detener de forma segura los procesos de Django, Node y Docker en Windows.
- Evaluar arquitecturas de despliegue Cloud (Render, Supabase, Vercel) y compararlas con ejecución local.
- Adaptar `levantar_todo.py` para la generación guiada de variables de entorno.

### Qué se hizo

- Se ejecutó limpieza con `git checkout -- .` y `git clean -fd`, restableciendo la rama al estado limpio de `origin/feature/IS2GE-105`.
- Se identificaron y terminaron los procesos en puertos ocupados (`8000`, `8443`, `8080`) en Windows mediante PowerShell.
- Se diseñó el esquema de arquitectura Cloud:
  - Base de datos relacional PostgreSQL en **Supabase**.
  - Backend Django y servidor Keycloak en **Render**.
  - Frontend SPA en **Vercel** o **Cloudflare Pages**.
- Se consensuó priorizar la opción de ejecución local optimizada para las demostraciones intermedias y avanzar en paralelo con la infraestructura.

### Qué se descartó y por qué

- No se borró la rama `feature/IS2GE-105`, preservando su vinculación en Git.
- No se adoptaron servicios Cloud de pago innecesarios para esta fase.

### Verificación

- `git status` reportó árbol de trabajo completamente limpio.
- Puertos de red liberados sin procesos residuales.

---

## 7. Landing de bienvenida (`InicioModule`) y ajuste de navegación post-login

- **Fecha:** 9 de octubre de 2026
- **Rama:** `feature/IS2GE-105`
- **Sesión ID:** `4263130d-5125-406c-863e-0ea3abbcfeb6`

### Contexto

El sistema redirigía inmediatamente tras el inicio de sesión a formularios de operación específicos, lo cual generaba desorientación a usuarios con roles administrativos o de cajero. Se requería una pantalla neutra institucional que diese la bienvenida y guiase al usuario al menú lateral.

### Qué se le pidió a la IA

- Modificar el flujo de redirección post-login en React Router.
- Diseñar la pantalla principal de bienvenida (`InicioModule.tsx`) con un diseño institucional limpio.
- El usuario solicitó explícitamente descartar maquetas complejas con tarjetas y optar por un mensaje minimalista y centrado.

### Qué se hizo

- Se descartó una propuesta intermedia que incluía múltiples tarjetas de resumen.
- Se implementó `InicioModule.tsx` con un contenedor centrado:
  - Título principal: *"Bienvenido a Global Exchange"*.
  - Subtítulo guía: *"Selecciona una opción del menú lateral para comenzar a operar."*
- Se configuró la ruta por defecto `/` en `App.tsx` para renderizar `InicioModule` tras la autenticación exitosa.

### Qué se descartó y por qué

- Se descartó mostrar métricas financieras o tablas en la pantalla de bienvenida para no recargar la vista ni anticipar operaciones antes de la selección del menú.

### Verificación

- Inicio de sesión con diferentes perfiles: todos aterrizaron en la pantalla de bienvenida limpia con el menú lateral plenamente funcional.

---

## 8. Filtro de roles de staff en Clientes y depuración en Denominaciones

- **Fecha:** 10 de octubre de 2026
- **Rama:** `feature/IS2GE-105`
- **Sesión ID:** `11006841-ceb1-49f3-b49c-07bd2ad246bd`

### Contexto

En el panel de administración de Clientes, el selector desplegable de usuarios incluía cuentas del personal operativo (`admin`, `cajero`, `analista`), permitiendo asociar indebidamente a empleados como clientes comerciales. Asimismo, en el módulo de Denominaciones existía un botón "Modificar" que permitía alterar el valor facial de billetes ya emitidos.

### Qué se le pidió a la IA

- Filtrar el selector de usuarios al crear o asociar clientes para excluir cuentas con roles de staff.
- Eliminar la acción "Modificar" de la tabla de Denominaciones en el panel administrativo.

### Qué se hizo

- En el backend/frontend de clientes se introdujo una condición de filtrado basada en roles de Keycloak, excluyendo del listado a aquellos usuarios que contengan los roles `admin`, `cajero` o `analista`.
- En `DenominacionesModule.tsx` se removió la columna de acción de edición y el botón "Modificar", restringiendo las acciones a alta y consulta.

### Qué se descartó y por qué

- No se permitió la mutabilidad de denominaciones de moneda registradas, ya que cambiar el valor nominal de un billete provocaría descuadres irreparables en los arqueos históricos de caja.

### Verificación

- El desplegable de usuarios en Clientes listó únicamente usuarios comunes.
- La tabla de denominaciones ya no presentó el botón "Modificar".

---

## 9. Refactorización de Denominaciones y corrección de sintaxis JSX

- **Fecha:** 10 de octubre de 2026
- **Rama:** `feature/IS2GE-105`
- **Sesión ID:** `277c0317-6646-4170-a9ed-42b495bb49a0`

### Contexto

El botón "Agregar Denominación" no abría el modal correspondiente debido a un error de propagación de eventos en React y cierre incorrecto de etiquetas JSX. Además, el campo de búsqueda de denominaciones operaba sobre texto plano no estructurado.

### Qué se le pidió a la IA

- Reparar el botón "Agregar Denominación" y corregir los errores de JSX en `DenominacionesModule.tsx`.
- Reemplazar el campo de búsqueda de texto por un selector desplegable de filtro por moneda.

### Qué se hizo

- Se corrigieron las etiquetas mal cerradas en el componente React y se normalizaron los manejadores `onClick` del modal de alta.
- Se integró el catálogo de monedas activas (`/api/monedas/`) en un elemento `<select>`, permitiendo filtrar las denominaciones de billetes según la divisa seleccionada (USD, EUR, PYG, BRL, ARS).

### Qué se descartó y por qué

- No se mantuvo la búsqueda por texto libre, pues permitía ingresar caracteres inválidos o monedas inexistentes.

### Verificación

- Apertura fluida del modal al presionar "Agregar Denominación".
- Filtrado instantáneo de la tabla al seleccionar una moneda del desplegable.
- Compilación de Vite sin errores sintácticos.

---

## 10. Eliminación de validación de medio de pago en Compra de Divisas

- **Fecha:** 10 de octubre de 2026
- **Rama:** `feature/IS2GE-105`
- **Sesión ID:** `c9e100e4-a70b-4564-b7ab-290d083fd4e5`

### Contexto

El formulario de Compra de Divisas para el cajero exigía seleccionar un medio de pago bancario y bloqueaba la operación si el cliente no tenía cuentas bancarias asociadas. En una casa de cambio, la compra de divisas de ventanilla es en efectivo: el cliente entrega divisa extranjera y el cajero entrega guaraníes físicos.

### Qué se le pidió a la IA

- Remover el selector de medio de pago en la pantalla de Compra de Divisas.
- Eliminar la validación que bloqueaba el botón "Registrar compra" ante la falta de medio de pago o cuenta bancaria.

### Qué se hizo

- Se removió el selector de medio de pago del formulario de Compra en el frontend.
- Se modificó la validación del backend en la app `caja`: si el medio de pago no es provisto, la transacción se imputa automáticamente al libro de caja física en efectivo del operador de turno.

### Qué se descartó y por qué

- No se obligó a los clientes de paso o de ventanilla a registrar cuentas bancarias para operaciones presenciales al contado.

### Verificación

- Se registró una compra de 200 USD seleccionando un cliente sin cuentas bancarias; la operación fue procesada y asentada en el libro de caja con código HTTP 201.

---

## 11. Validación de denominaciones en Venta de Divisas y fix de cierre de caja

- **Fecha:** 10 de octubre de 2026
- **Rama:** `feature/IS2GE-105`
- **Sesión ID:** `b0567155-8ac3-4455-a9f8-248083d1b928`

### Contexto

En el módulo de Venta de Divisas para cajeros, se podían seleccionar monedas que no tenían stock de billetes/denominaciones cargadas, impidiendo desglosar la entrega física. Además, al efectuar el cierre de caja, el backend lanzaba una excepción `AttributeError` al intentar calcular totales consolidados.

### Qué se le pidió a la IA

- Consumir los métodos de pago activos desde la API.
- Deshabilitar en el selector de monedas aquellas que no tengan denominaciones registradas.
- Solucionar la excepción en el endpoint de cierre de caja (`/api/caja/cierre/`).

### Qué se hizo

- Se conectó el selector de métodos de pago con el catálogo de medios activos de la base de datos.
- Se implementó la validación dinámica de monedas: las divisas sin billetes asociados se marcan como `Moneda (Sin Denominaciones)` y quedan deshabilitadas para la venta.
- En `backend/caja`, se corrigió el cálculo de subtotales por moneda durante el cierre y se resolvió la referencia a los claims del token OIDC del cajero.

### Qué se descartó y por qué

- No se omitió el arqueo de billetes al cierre; se garantizó el registro de montos esperados vs. montos declarados.

### Verificación

- Monedas sin denominaciones quedaron bloqueadas visualmente en el selector.
- El cierre de caja generó el arqueo completo sin excepciones y emitió el resumen con estado cerrado.

---

## 12. Integración segura de la rama `feature/IS2GE-105` en `develop`

- **Fecha:** 10 de octubre de 2026
- **Rama:** `develop`
- **Sesión ID:** `7abfd496-7cc0-4b32-b9ca-165f4625c38d`

### Contexto

Finalizadas y validadas todas las funcionalidades de caja, apertura, arqueo, compras de ventanilla y cierres en `feature/IS2GE-105`, correspondía integrar estos cambios a la rama principal de desarrollo (`develop`) sin romper el trabajo de los demás integrantes.

### Qué se le pidió a la IA

- Realizar el merge de la rama `feature/IS2GE-105` en `develop`.
- Garantizar que no se generen conflictos ni regresiones en los módulos preexistentes.

### Qué se hizo

- Se sincronizó la rama local `develop` con `origin/develop`.
- Se ejecutó `git merge feature/IS2GE-105`.
- Se verificó la integración limpia en las apps de Django (`caja`, `clientes`) y en los componentes de React.
- Se publicó la rama en el repositorio remoto con `git push origin develop`.

### Qué se descartó y por qué

- No se utilizó push forzado (`--force`) ni rebase destructivo para proteger el historial de commits del equipo.

### Verificación

- Integración exitosa sin conflictos.
- Ejecución de `manage.py check` y suite de pruebas unitarias con resultado satisfactorio.

---

## 13. Configuración y automatización de dependencias de Stripe

- **Fecha:** 11 de octubre de 2026
- **Rama:** `develop`
- **Sesión ID:** `db12da72-88e8-479b-863b-f678ff20fd28`

### Contexto

Para la integración de cobros con tarjeta mediante Stripe, se requería incorporar las bibliotecas oficiales (`@stripe/stripe-js`, `@stripe/react-stripe-js`) y asegurar que los scripts de arranque no fallaran en equipos donde las dependencias aún no hubieran sido descargadas.

### Qué se le pidió a la IA

- Actualizar los archivos `.env.example` en backend y frontend para incluir las claves de Stripe.
- Modificar `levantar_todo.py` para solicitar interactivamente y enmascarar la `STRIPE_SECRET_KEY`.
- Automatizar la detección e instalación de dependencias de Stripe en `node_modules`.

### Qué se hizo

- Se incluyeron `STRIPE_PUBLISHABLE_KEY` y `STRIPE_SECRET_KEY` en las plantillas de entorno.
- En `levantar_todo.py` se implementó la captura segura mediante `getpass` con validación de prefijos `pk_` y `sk_`.
- Se añadió una rutina que comprueba la presencia de `@stripe/stripe-js` en `frontend/package.json` y ejecuta `pnpm install` automáticamente si faltan módulos.
- Se garantizó que la clave secreta nunca sea transferida al frontend.

### Qué se descartó y por qué

- No se commitearon claves reales de Stripe en el repositorio.
- No se expuso la clave secreta en el navegador del cliente.

### Verificación

- Ejecución de `levantar_todo.py`: detectó la configuración, solicitó credenciales enmascaradas y levantó el stack con la pasarela lista.

---

## 14. Diagnóstico y solución a fallo de túneles Cloudflare (DNS en Docker)

- **Fecha:** 12 de octubre de 2026
- **Rama:** `develop`
- **Sesión ID:** `cbc447e3-d28d-4e17-8817-dbc11e29d50c`

### Contexto

Al exponer la plataforma a internet con `publicar.py --demo` y `docker-compose.publico.yml` usando Cloudflare Quick Tunnels, los contenedores arrojaban el error: `lookup api.trycloudflare.com on 127.0.0.11:53: no such host`.

### Qué se le pidió a la IA

- Diagnosticar el motivo por el cual los contenedores Docker no lograban resolver el dominio de Cloudflare.
- Resolver la falla de DNS sin alterar la red interna entre contenedores.
- Obtener las URLs públicas HTTPS operativas.

### Qué se hizo

- Se determinó que el DNS interno de Docker Desktop en Windows con WSL2 presentaba problemas de resolución hacia el anfitrión.
- Se editaron los servicios de túnel en `docker-compose.publico.yml`, agregando DNS públicos explícitos:
  ```yaml
  dns:
    - 1.1.1.1
    - 8.8.8.8
  ```
- Se reejecutó `python publicar.py --demo`.
- Cloudflare asignó de inmediato dominios temporales seguros para Keycloak, backend y frontend.

### Qué se descartó y por qué

- No se reemplazó Cloudflare por herramientas de pago o con límites restrictivos (como ngrok gratuito).
- No se modificaron los adaptadores de red físicos de Windows.

### Verificación

- Los tres túneles conectaron en menos de 3 segundos.
- Se verificó el acceso y la navegación fluida desde un dispositivo móvil fuera de la red local.

---

## 15. Consolidación inicial de documentación de interacciones técnicas con IA

- **Fecha:** 13 de octubre de 2026
- **Rama:** `develop`
- **Sesión ID:** `01f2ca92-c6f2-4a68-9d1d-c527adb1da02`

### Contexto

En cumplimiento de las pautas de evaluación del criterio CHIA de la cátedra de Ingeniería de Software II, resultaba necesario consolidar un registro formal de todas las interacciones de desarrollo asistido con IA mantenidas en el repositorio.

### Qué se le pidió a la IA

- Generar un documento estructurado (en formato Markdown) que recopile todas las conversaciones y sesiones técnicas del proyecto.
- Revisar los documentos previos en `docs/conversaciones-ia/` para mantener homogeneidad de estilo.

### Qué se hizo

- Se realizó un relevamiento completo de los archivos existentes en la carpeta de documentación (`README.md`, minutas de Hito 4 y Hito 5 de otros integrantes).
- Se mapearon los temas principales cubiertos: puesta a punto de entornos, flujo OIDC, arquitectura de caja, pasarela de pagos y despliegue público.
- Se sentaron las bases del índice cronológico de trabajo.

### Qué se descartó y por qué

- No se generó un volcado plano de logs o transcripciones brutas sin editar; se acordó respetar estrictamente el formato de minutas CHIA de la cátedra.

### Verificación

- Estructura y directorios mapeados correctamente para la posterior generación de los compendios individuales y de equipo.

---

## 16. Estandarización de recopilación bajo criterio CHIA para Google Antigravity

- **Fecha:** 16 de octubre de 2026
- **Rama:** `develop`
- **Sesión ID:** `c55143db-f017-4b3a-bd9e-5e32f9211168`

### Contexto

El repositorio disponía del archivo `recopilacion-completa.md` con las interacciones de Lucas con GitHub Copilot CLI, pero faltaba el compendio específico de las sesiones técnicas trabajadas en Google Antigravity (Gemini), separando estrictamente lo realizado con esta herramienta de las tareas de los demás integrantes.

### Qué se le pidió a la IA

- Crear un documento análogo a `recopilacion-completa.md`, abarcando exclusivamente las conversaciones bilaterales entre Lucas y Google Antigravity (Gemini) sobre Global Exchange.
- No incluir conversaciones de otras herramientas ni de otros compañeros de equipo.
- Respetar el formato CHIA: Contexto, Qué se pidió, Qué se hizo, Qué se descartó, Verificación y Queda abierto.

### Qué se hizo

- Se redactó y publicó `docs/conversaciones-ia/recopilacion-antigravity.md` documentando 14 sesiones técnicas realizadas entre el 29 de agosto y el 12 de octubre de 2026.
- Se incorporaron las tablas de índice de sesiones con UUIDs, fechas y temas centrales.
- Se sintetizó el estado consolidado de la arquitectura de software desarrollada en común.
- Se actualizó el archivo `docs/conversaciones-ia/README.md` y se preparó el commit `2ed3f6f`.

### Qué se descartó y por qué

- No se incluyeron interacciones de Claude Code correspondientes a Milner o Juan Cruz.
- No se divulgaron credenciales reales de Stripe, Keycloak ni tokens de API.

### Verificación

- Archivo de más de 740 líneas verificado sintácticamente en Markdown y confirmado en la rama `develop`.

---

## 17. Auditoría integral de trazabilidad, ramas y commits desde el Tag v4.0

- **Fecha:** 16 de octubre de 2026
- **Rama:** `develop`
- **Sesión ID:** `1b7a5da0-5f77-4b1a-83ec-787e6ead2e80`

### Contexto

Tras la entrega del Hito 6 / Sprint 4 (congelada en el tag `v4.0` el 12 de octubre de 2026), se introdujo un volumen significativo de cambios para los Hitos 7 y 8 (Facturación electrónica SIFEN / Factura Segura, Reportes y Tablero de Ganancias, Simulación completa de transacciones, resiliencia de túneles y despliegue automático). Lucas necesitaba una auditoría profunda de la historia de Git para verificar ramas creadas, merges y autores antes del cierre.

### Qué se le pidió a la IA

- Analizar la historia del repositorio de Git a partir del tag `v4.0` hasta el commit/estado actual (`HEAD`).
- Mapear la evolución del árbol de Git (`git log v4.0..HEAD --graph --oneline --decorate`).
- Identificar todas las ramas de feature desarrolladas e integradas (*merged*), detallando el alcance de cada una y los autores participantes.

### Qué se hizo

- Se ejecutó la inspección exhaustiva de Git sobre los 26 commits del período (6.415 líneas agregadas en 63 archivos):
  - **Facturación electrónica (Hito 7):** Rama `feature/facturacion-electronica` y `feature/proteger-emision-facturas` (integración con Factura Segura, emisión de comprobantes SIFEN, resguardo de numeración correlativa reservada al Administrador).
  - **Reportes y Tablero de Ganancias (Hito 8):** Rama `feature/reportes-ganancias` (aplicación Django `reportes`, módulos React `ReportesModule.tsx` y `TableroGananciasModule.tsx`, exportación CSV).
  - **Simulación y Transacción Completa:** Ramas `feature/simulacion-completa` y `feature/transaccion-completa` (facturación de operaciones de caja, soporte de RUC en clientes, simulación conectada al backend).
  - **Personalización y Branding:** Rama `feature/tema-login-keycloak` (tema visual `global-exchange` para la pantalla de inicio de sesión de Keycloak).
  - **DevOps y Resiliencia:** Ramas `feature/despliegue-automatico`, `feature/recrear-tuneles-caidos` y `feature/detalles-caja-y-facturas` (script `desplegar.py`, usuarios fixture preconfigurados, recreación automática de túneles caídos de Cloudflare, distinción de compra/venta en facturas).
- Se elaboró un informe pormenorizado de trazabilidad técnica validando el cumplimiento de los requerimientos de la cátedra.

### Qué se descartó y por qué

- No se alteró ni se reescribió la historia de Git; la auditoría fue de carácter analítico y de control de calidad.

### Verificación

- Todos los merges fueron verificados en el grafo de Git sin inconsistencias ni conflictos abiertos en `develop`.

---

## 18. Generación y homologación formal del registro para cuenta FPUNA

- **Fecha:** 19 de octubre de 2026
- **Rama:** `develop`
- **Sesión ID:** `22edae2d-a21d-43e2-b5b3-98453edafb68`

### Contexto

Lucas requería contar con una versión íntegra, unificada y formalmente atribuida a su cuenta de correo institucional de la facultad (`lucasvallejos070@fpuna.edu.py`) que consolidase la totalidad de las 18 sesiones técnicas trabajadas en Google Antigravity (Gemini) a lo largo de todo el semestre, siguiendo la plantilla de `recopilacion-completa.md` y complementando los registros preexistentes.

### Qué se le pidió a la IA

- Generar el documento `docs/conversaciones-ia/recopilacion-antigravity-fpuna.md` respetando la estructura del criterio CHIA.
- Unificar todas las conversaciones registradas en este entorno desde el 29 de agosto hasta el 19 de octubre de 2026.
- Actualizar el índice general de conversaciones en `docs/conversaciones-ia/README.md`.

### Qué se hizo

- Se auditaron las 18 sesiones almacenadas en el entorno local de Antigravity IDE, correlacionando fechas, identificadores UUID, prompts y entregables.
- Se redactó el documento completo abarcando:
  - Fases iniciales de diagnóstico y entorno local (agosto).
  - Integración de Keycloak, OpenID Connect y clientes (septiembre).
  - Módulo integral de caja, compras/ventas de ventanilla y Stripe (octubre).
  - Publicación segura con Cloudflare Tunnels (octubre).
  - Auditoría de ramas y trazabilidad desde el Tag v4.0 (octubre).
  - Homologación formal bajo la cuenta institucional `lucasvallejos070@fpuna.edu.py`.
- Se incorporó la referencia en `docs/conversaciones-ia/README.md`.

### Qué se descartó y por qué

- No se sobrescribió ni modificó el archivo `recopilacion-antigravity.md` previo para mantener disponible el registro histórico tal como fue presentado en su corte original.
- No se alteraron los documentos de Copilot CLI ni los de otros miembros del equipo.

### Verificación

- Generación exitosa de `docs/conversaciones-ia/recopilacion-antigravity-fpuna.md`.
- Verificación de enlaces, formato Markdown y correspondencia unívoca de sesiones con el historial local.

---

## 19. Estado consolidado de nuestro trabajo

### Cambios principales realizados en conjunto

- **Configuración, Contenedores y Estabilidad de Entornos:**
  - Diagnóstico integral y normalización de dependencias en Windows 11 (Docker Desktop con WSL2, Python 3.12, Node.js 22).
  - Plantillas de entorno seguras (`keycloak/.env.example`, `backend/.env.example`, `.env.facturasegura.example`).
  - Reseteo limpio de inconsistencias en volúmenes persistentes de PostgreSQL para Keycloak.
- **Seguridad, Identidades y Flujo OIDC:**
  - Puesta a punto de la autenticación OpenID Connect entre Django y Keycloak, resolviendo excepciones HTTP 401 y discrepancias de Redirect URIs.
  - Saneamiento y protección de claves secretas de API y de pasarelas de pago, impidiendo su exposición en Git o en el frontend.
- **Frontend y Experiencia de Usuario (UI/UX):**
  - Corrección de errores de compilación TypeScript y sintaxis JSX en `ClientesModule.tsx` y `DenominacionesModule.tsx`.
  - Construcción del módulo de bienvenida institucional `InicioModule.tsx` con navegación orientada por menú lateral.
  - Supresión de hashes técnicos en listas de usuarios y agregado de badges visuales por categoría de cliente.
  - Estructuración de comisiones y márgenes comerciales diferenciados (Minorista 5%, Mayorista 10%, VIP 15%).
  - Refactorización de Denominaciones: eliminación de la edición in situ insegura y agregado de filtros dinámicos por divisa.
- **Lógica de Negocio y Módulo de Caja (IS2GE-105):**
  - Habilitación de compra directa de ventanilla en efectivo, eliminando bloqueos indebidos por medios de pago bancarios en clientes presenciales.
  - Bloqueo preventivo en venta de divisas de aquellas monedas que no cuenten con denominaciones físicas en stock.
  - Resolución de excepción `AttributeError` en el cálculo de diferencias de arqueo al cierre de turno de caja.
  - Integración fluida y limpia de la rama `feature/IS2GE-105` en `develop`.
- **Pasarelas de Pago e Infraestructura de Publicación:**
  - Automatización de la verificación e instalación de librerías de Stripe en `levantar_todo.py`.
  - Solución al fallo de resolución DNS en Docker Windows para túneles Cloudflare Quick Tunnels en `publicar.py`.
  - Diseño de la topología de despliegue en la nube (Supabase, Render, Vercel).
- **Trazabilidad y Auditoría de Software:**
  - Auditoría del historial de 26 commits y 9 ramas integradas desde el tag `v4.0` (Facturación Electrónica SIFEN, Reportes y Tablero de Ganancias, Simulación, tema de Keycloak).
  - Compilación exhaustiva de las conversaciones con IA cumpliendo el criterio CHIA de la cátedra para la cuenta institucional.

### Reglas técnicas y metodológicas aplicadas

- **Preservación de funcionalidad comprobada:** Toda refactorización conservó intactas las funciones operativas previas.
- **Aislamiento estricto de secretos:** Ninguna clave privada de Stripe, token de Keycloak o credencial de base de datos se versionó en Git.
- **Inmutabilidad de datos contables:** Los valores nominales de billetes y los registros que impactan en arqueos no admiten mutación arbitraria.
- **Centralidad en el usuario:** Mensajes de error confusos e identificadores crudos fueron reemplazados por textos claros y badges intuitivos.
- **Automatización de entorno:** Los scripts de asistencia técnica resuelven dependencias faltantes para garantizar que cualquier miembro del equipo pueda levantar el proyecto de forma desatendida.

### Pendientes finales identificados

- Configurar webhooks de producción para la conciliación asíncrona de cobros de Stripe.
- Automatizar la actualización de Redirect URIs en Keycloak cuando se generan túneles temporales efímeros de Cloudflare.
- Implementar la exportación e impresión en formato PDF de los comprobantes de compra/venta de divisas.
- Ejecutar el despliegue final en la nube (Supabase y Render) para la entrega definitiva del proyecto.
