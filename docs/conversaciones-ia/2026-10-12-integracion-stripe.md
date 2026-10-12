# Revisión de IS2GE-105, correcciones de permisos e integración con Stripe

- **Fecha:** 12 de octubre de 2026
- **Herramienta:** Claude (Anthropic), a través de Claude Code
- **Integrante:** Juan Cruz Cordero
- **Rama de trabajo:** `feature/IS2GE-98-Integracion-Stripe`, creada desde
  `develop` en el commit `a5dfea0` (merge del PR #18)

---

## Contexto

La sesión empezó revisando la rama `feature/IS2GE-105` de Lucas (módulo de
caja, denominaciones y control de acceso por roles) para mergearla a
`develop`. La revisión encontró problemas de permisos que se corrigieron, y a
partir de ahí se trabajó el objetivo principal: integrar **Stripe** para los
medios de pago y la confirmación de pago de las compras y ventas, tanto en la
web como en la caja. Al probar la caja aparecieron además problemas con la
moneda local y con el cierre, que también se resolvieron.

## Qué se le pidió a la IA (y qué se hizo)

### 1. Revisar IS2GE-105 y mergearla

- **Pedido:** ver qué agregó la rama y si estaba mergeada, sin mergearla
  directamente.
- **Hallazgo:** no estaba mergeada; contenía todo `develop`, así que el merge
  era sin conflictos. Se recomendó hacerlo por Pull Request en GitHub (como el
  resto del equipo) en vez de un push directo.
- **Incidente:** el PR se mergeó por error a `main` (#17) en lugar de
  `develop`. Se analizó revertirlo (`git revert` o volver `main` atrás con push
  forzado), pero se comprobó que `main` y la rama tenían exactamente el mismo
  código y que `develop` ya estaba contenido en `main`. Bastó con mergear
  también a `develop` (#18): las dos ramas quedaron con el mismo código, sin
  reescribir historia.

### 2. Corregir los problemas de la revisión

- **Los endpoints de caja no exigían rol:** cualquier usuario logueado (un
  cliente, por ejemplo) podía abrir caja o registrar operaciones llamando a la
  API. Se agregó `rol_requerido("cajero")` a todos.
- **El administrador no veía los medios de pago inactivos** y no podía
  reactivarlos (el detalle daba 404). Corregido.
- **Dos fuentes de roles:** `rol_requerido` leía los roles guardados en la
  sesión y el resto del sistema los grupos de Django. Se dejó una sola fuente,
  los grupos, que se reescriben desde Keycloak en cada login. Keycloak sigue
  siendo quien administra los roles.
- **Los roles se leían de `realm_access.roles`**, donde solo llegan roles por
  defecto de Keycloak; funcionaba de casualidad. Se volvió al claim `roles`
  (roles del client `global-exchange-web`), que es el diseño documentado.
- **Rol compuesto:** `administrador` incluye `cajero` y `analista_cambiario`.
  Juan Cruz lo configuró en la consola de Keycloak y se agregó al
  `realm-export.json` para que lo tenga todo el equipo.
- **Acceso denegado:** en vez de un 403 sin explicación, la API responde un
  JSON con el rol necesario y la maqueta muestra un modal "Acceso denegado".

### 3. Integración con Stripe (modo test)

Decisiones que tomó Juan Cruz ante las preguntas de la IA:

- En la **venta**, el cliente recibe guaraníes y Stripe no permite pagarle a
  una tarjeta de forma simple: se decidió **cobrar la divisa** que entrega.
- En la **caja**, Stripe se usa **en compra y venta**.

Qué se implementó (detalle técnico en `docs/integracion-stripe.md`):

- **Tarjetas con Stripe Elements:** el número y el CVV van directo a Stripe.
  Antes la maqueta mandaba el número y el **CVV** al backend y se guardaban
  con una "tokenización" casera, lo que viola las normas de tarjetas (PCI).
  Ahora solo se guarda el `pm_...`, la marca, los últimos 4 y el vencimiento.
- **Compra y venta web:** cobro al confirmar; la operación queda pagada solo
  con el cobro aprobado; 3D Secure soportado; si la cotización cambió, se
  cancela sin cobrar.
- **Caja:** cobro con las tarjetas de los usuarios del cliente; el arqueo no
  cuenta lo cobrado con tarjeta.
- **Claves** en `backend/.env.stripe` (ignorado por git y que
  `levantar_todo.py` no borra), y opcionales en producción.

### 4. Moneda local (guaraní) y arqueo

- **Problema:** para abrir la caja hacía falta el guaraní como moneda, pero
  RN10 (venta mayor que compra) no dejaba cargarlo a 1/1.
- **Solución:** la IA propuso detectarlo por el código `PYG`; Juan Cruz
  propuso una **casilla "Moneda local"** en el formulario, que se adoptó por
  ser más clara. La moneda local no tiene cotización, no se compra ni se
  vende, y puede haber una sola.
- **Arqueo:** antes solo seguía las divisas. Ahora también los guaraníes: las
  ventas en efectivo suman, las compras restan. Se agregó "Efectivo" como forma
  de pago en la venta de caja (antes no existía).
- **Eliminar monedas:** se agregó el botón. Si la moneda tiene operaciones, no
  se borra y se explica que hay que desactivarla.

### 5. Ajustes después de probar

- **Operaciones pendientes** (3D Secure fallido): se pueden pagar o cancelar
  desde el Historial de Transacciones, sin riesgo de cobrar dos veces.
- **Historial de Caja:** pantalla nueva con cada caja ("Caja #N · abierta el
  ... · cerrada a las ...") y sus compras y ventas, con filtro por fecha.
- **Cierre de caja:** la diferencia muestra "—" hasta cargar el conteo; no
  deja cerrar con monedas sin contar; las compras con tarjeta se informan
  aparte; el total usa las cotizaciones reales en lugar de tasas fijas en el
  código.
- **Saldo real físico:** campo con puntos de miles automáticos y coma decimal
  (el campo numérico del navegador tomaba "987.367" como 987,367).
- **Modales propios** en lugar del cuadro de confirmación del navegador.

## Qué se descartó y por qué

- **Revertir el merge a `main`:** innecesario; el código era idéntico al que
  iba a llegar por `develop`. Un push forzado habría reescrito la historia de
  una rama compartida.
- **Agregar `administrador` al decorador de caja:** se prefirió el rol
  compuesto en Keycloak, para que quién opera la caja se decida en Keycloak y
  no en el código.
- **Selector "Ver como Administrador / Cajero":** a Juan Cruz no le gustó. La
  alternativa (menú del administrador con una sección "Caja") **quedó en
  pausa** a pedido suyo.
- **Webhooks de Stripe:** requieren el `stripe` CLI en cada máquina. El estado
  del pago se consulta a Stripe en el momento; se pueden sumar más adelante.
- **Cargar el guaraní en los datos de ejemplo (`demo.json`):** se hizo y se
  revirtió a pedido de Juan Cruz; la moneda local se carga a mano.
- **Excepción a RN10 para el guaraní:** habría hecho que apareciera como
  moneda para comprar y vender.

## Bugs encontrados en el camino

- **Las respuestas 204 llevaban cuerpo** (`{}`) en seis endpoints de borrado.
  Con conexiones keep-alive, esos bytes rompían la respuesta siguiente: la
  maqueta no podía recargar la lista después de eliminar. Se reprodujo con un
  servidor aparte y se corrigió en todos.
- **Eliminar un medio de pago usado en caja daba error 500** (referencias
  protegidas). Ahora se desactiva.
- **Eliminar una moneda con operaciones daba error 500.** Ahora responde con
  un mensaje claro.

## Verificación

- **Pruebas unitarias:** de 158 al empezar a **223**, todas en verde. Stripe se
  simula en las pruebas (no necesitan red ni claves).
- **Prueba de punta a punta contra Stripe real (modo test)**, por la API de
  Django y dentro de una transacción que se deshizo al final: carga de
  tarjeta, compra cobrada en PYG, venta cobrada en USD, 3D Secure, venta y
  compra de caja, arqueo y desvinculación de la tarjeta. Los datos de prueba
  se borraron también de Stripe.
- **El bug del 204** se reprodujo y se verificó el arreglo con el servidor de
  desarrollo real.
- **El cierre de caja** se verificó contra los movimientos reales de la base de
  Juan Cruz.
- Frontend: compila y pasa el chequeo de tipos de TypeScript sin errores.
- Sphinx compila sin advertencias, con los módulos nuevos (`pagos`, `caja`).
- **Prueba manual en el navegador:** a cargo de Juan Cruz, con el paso a paso
  de abajo.

## Paso a paso de prueba manual

Tarjetas de prueba: `4242 4242 4242 4242` (aprobada), `4000 0027 6000 3184`
(3D Secure), `4000 0000 0000 0002` (rechazada); vencimiento futuro, cualquier
CVC.

1. **Preparación:** `pip install -r requirements.txt`, `migrate`,
   `pnpm install`, crear `backend/.env.stripe` y reiniciar el backend.
2. **Datos (admin.test):** asociar `cliente.test` a "Clara Cliente"; crear
   PYG como moneda local; cargar billetes de PYG y USD.
3. **Tarjetas (cliente.test):** cargar la 4242 y la 3184 (completar el 3D
   Secure); la 0002 tiene que rechazarse.
4. **Compra web:** con la 4242 se cobra en PYG; con la 3184 y "Fail" queda
   pendiente.
5. **Pendientes:** desde el Historial de Transacciones, "Pagar ahora" y
   "Cancelar operación".
6. **Venta web** con tarjeta: se cobra la divisa.
7. **Cotización que cambia** antes de confirmar: se cancela sin cobrar.
8. **Caja (cajero.test):** apertura con USD y PYG; ventas en efectivo y con
   tarjeta; compras con tarjeta y en efectivo.
9. **Cierre:** revisar entradas, salidas, compras con tarjeta, el formato del
   conteo y que la diferencia dé 0.
10. **Historial de Caja** con cajero y con administrador.
11. **Eliminar una tarjeta** usada en caja: queda inactiva y se desvincula en
    Stripe.

## Queda abierto

- **Rotar la clave secreta de Stripe:** se compartió en la conversación.
  Dashboard de Stripe → Developers → API keys → Roll key.
- **Menú del administrador con la sección "Caja"** (en pausa).
- **Notificaciones:** la campanita de la barra superior es decorativa; no hay
  nada implementado en `develop` ni en otras ramas.
- **Producción:** si el Keycloak del ambiente público ya existe, el rol
  compuesto hay que configurarlo a mano (el realm se importa solo la primera
  vez).
- Aplicar el formato de montos (`MontoInput`) a otros campos, si el equipo lo
  quiere.
- Hacer el commit y el Pull Request de la rama.
