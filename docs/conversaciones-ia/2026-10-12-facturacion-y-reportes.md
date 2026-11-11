# Facturación electrónica con Factura Segura, reportes y tablero de ganancias

- **Fecha:** 12 de octubre de 2026
- **Herramienta:** Claude (Anthropic), a través de Claude Code
- **Integrante:** Milner Noguera
- **Ramas de trabajo:** `feature/facturacion-electronica` (creada desde
  `develop` en el commit `32c5e82`) y, una sobre la otra,
  `feature/reportes-ganancias`, `feature/tema-login-keycloak`,
  `feature/simulacion-completa` y `feature/transaccion-completa`

---

## Contexto

El Hito 7 (Sprint 5) pide la integración con la facturación electrónica de la
DNIT, con visualización y descarga de facturas, y el Hito 8 (Sprint 6) pide
reportes de transacciones y ganancias, un tablero de control de ganancias y
gráficos de evolución de tasas. La cátedra entregó dos documentos: la
especificación *API de Factura Segura para ESI v01* y una planilla con el
rango de números asignado a cada equipo. Al nuestro le tocaron **12 facturas**
(`001-003-0000382` a `0000393`) y 12 notas de crédito (`0000157` a `0000168`).

La condición del equipo desde el primer mensaje fue **no emitir ninguna
factura todavía**, porque los números son pocos.

## Qué se le pidió a la IA (y qué se hizo)

### 1. Cómo encarar la integración con la DNIT

- **Pedido:** leer los dos documentos y proponer cómo hacerlo, sin generar
  ninguna factura. Se avisó de un problema: en algún lado se mostraba el
  nombre del usuario en vez del nombre del cliente.
- **Qué se hizo:** la IA leyó los PDF y el código, y propuso copiar el esquema
  de la integración con Stripe: una app nueva con un único módulo que habla
  con el servicio externo. Señaló que la operación `calcular_de` no genera
  documentos, así que sirve para validar sin gastar números. También señaló
  qué faltaba para emitir de verdad (el token del usuario ESI y los datos del
  emisor y del timbrado, que no están en ninguno de los dos documentos).

### 2. Integración con Factura Segura

- **Pedido:** avanzar con todo lo que no dependiera de los datos que faltan,
  usando el rango asignado al equipo.
- **Qué se hizo:**
  - App `facturacion`: modelo `Factura` (operación, número, CDC, estado,
    receptor y total copiados) y `servicio.py` con `calcular_de`,
    `generar_de`, `get_estado_sifen`, `dwn_kude` y `dwn_xml`.
  - **Tres modos**, para cuidar los números: sin token la factura queda
    simulada; con token se valida con `calcular_de`; recién con
    `FACTURA_SEGURA_EMITIR=1` se emite.
  - El receptor sale siempre del **cliente** de la operación (RN02), nunca del
    usuario. Para eso se agregó `Cliente.ruc`, con validación del dígito
    verificador.
  - Una señal factura la operación cuando queda pagada, después del `commit`:
    cubre todos los caminos por los que una operación se paga, y un problema
    con la factura no deshace el pago.
  - Numeración: se toma el primer número libre del rango. Un rechazo claro de
    Factura Segura lo libera; si se corta la conexión al emitir, se conserva y
    el reintento manda el mismo, como indica la especificación.
  - Pantallas de Django (`/facturas/`), API (`/api/facturas/`) y el módulo
    Facturas de la maqueta, que era solo un prototipo con datos fijos.
  - Configuración en `backend/.env.facturasegura` (ignorado por git), que
    también lee producción. Guía en `docs/integracion-factura-segura.md`.

### 3. Reportes y tablero de ganancias

- **Pedido:** ir haciendo todo lo que se pudiera de los Hitos 7 y 8.
- **Qué se hizo:**
  - App `reportes`, sin modelos: calcula sobre las operaciones pagadas.
  - API para el reporte de transacciones (con exportación a CSV) y para el
    tablero (totales y desgloses por tipo, moneda y día). Solo para
    administrador y analista cambiario.
  - Maqueta: módulos **Reportes** y **Tablero de Ganancias**, y la pantalla de
    evolución de tasas, que ya existía para el cliente, se agregó al menú del
    analista y del administrador.

### 4. Aspecto del inicio de sesión

- **Pedido:** si se podía mejorar la pantalla de login de Keycloak.
- **Qué se hizo:** un tema propio (`keycloak/themes/global-exchange`) que
  hereda del tema de Keycloak y solo cambia el aspecto con una hoja de
  estilos, con los colores y las formas de la maqueta. El login lo sigue
  dibujando Keycloak (RN05). Se monta en los dos `docker-compose`, viene en
  el `realm-export.json` y `configurar_produccion.py` lo aplica en un Keycloak
  que ya tenía el realm.

### 5. Completar el alcance del Hito 7

- **Pedido:** dejar el Hito 7 lo más completo posible.
- **Qué se hizo:**
  - El **RUC del cliente** se carga desde el formulario de Clientes de la
    maqueta (se agregó `ruc` como campo opcional en `types.ts`).
  - La **simulación** ahora es completa: con un cliente activo la calcula el
    backend con la misma cuenta de una operación real (tasa base, descuento
    del segmento, tasa aplicada, comisión y total), sin registrar nada. Antes
    la hacía el navegador y no incluía la comisión.

### 6. Simulación completa de transacciones

- **Pedido:** el equipo aclaró, con la lista de hitos, que "simulación
  completa de transacciones" es poder recorrer una transacción entera con todo
  lo de los sprints anteriores funcionando junto, no el simulador de
  conversión del Hito 4.
- **Qué se hizo:** la IA revisó el recorrido y encontró un hueco: las
  operaciones de la **caja** no generaban factura. Se generalizó la
  facturación (la factura puede ser de una transacción web, una compra o una
  venta de caja, y guarda su cliente) y se agregó una prueba de punta a punta
  por la API (`backend/tests/test_transaccion_completa.py`): alta del cliente,
  operación, pago o cancelación, notificación, factura, descarga y reporte,
  por la web y por la caja.

## Decisiones que tomó la IA y quedaron a confirmar

Se dejaron escritas como supuestos, en el código y en la guía, para que el
equipo las revise con la cátedra:

- **Qué se factura.** Compra del cliente: un ítem exento de IVA más la comisión
  gravada al 10 %. Venta del cliente: un ítem exento con la comisión como
  descuento. Los ítems van en guaraníes y con cantidad 1 para que el total
  coincida con lo cobrado.
- **Qué es la ganancia.** La comisión más el margen de cambio sobre el precio
  medio de la cotización. Puede dar negativo cuando el descuento del segmento
  es más grande que el spread, y el reporte lo muestra tal cual.

## Qué se descartó y por qué

- **Emitir una factura de prueba.** No se hizo: no hay token ni datos del
  emisor, y el equipo pidió no gastar números.
- **Emitir solas las facturas simuladas al prender la emisión.** Se descartó
  para que nadie gaste números sin darse cuenta: se emiten una por una, a
  pedido.
- **Rehacer las pantallas de Keycloak con plantillas propias.** Se descartó:
  con un tema que solo trae estilos, el registro, la recuperación de
  contraseña y las pantallas futuras siguen funcionando sin mantenerlas.
- **Copiar la configuración de Factura Segura a `.env.prod`**, como se hizo
  con Stripe. Son más de veinte variables: se prefirió que producción lea el
  mismo archivo con `env_file`, sin tocar `publicar.py`.
- **Notas de crédito y cancelación de facturas.** Quedaron fuera de esta
  sesión.

## Verificación

- **Pruebas unitarias:** 327 en total, todas en verde; 48 nuevas de
  facturación, 18 de reportes y 12 del recorrido completo. Ninguna sale a la red: se reemplaza el único
  punto que habla con Factura Segura, y `settings.py` apaga el token y la
  emisión al correr los tests.
- **En el navegador, con login real por Keycloak** (usuarios de prueba)
  contra la base local: el tablero, el reporte y la lista de facturas muestran
  las operaciones cargadas; una factura de un cliente sin RUC quedó en error y
  pasó a simulada al reintentarla después de cargarle el RUC; el RUC se guardó
  desde el formulario de Clientes; la simulación mostró el desglose completo;
  el tema nuevo se vio en el login, en el error de contraseña y en el
  registro; y una compra hecha desde la maqueta como cliente generó su
  factura. El recorrido de la caja se probó por la API, no a mano.
- **Maqueta:** chequeo de tipos y `vite build` sin errores.
- **Sin verificar:** nada se probó contra Factura Segura. La emisión real, la
  consulta al SIFEN y las descargas del KuDE y del XML solo están cubiertas
  por las pruebas con el servicio simulado.
