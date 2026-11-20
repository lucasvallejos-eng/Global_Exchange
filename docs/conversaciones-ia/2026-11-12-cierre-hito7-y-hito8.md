# Cierre del Hito 7 y avance del Hito 8: emisión, despliegue, reportes con caja y terminal de autoservicio

- **Fechas:** del 12 de octubre al 12 de noviembre de 2026 (varias sesiones)
- **Herramienta:** Claude (Anthropic), a través de Claude Code
- **Integrante:** Milner Noguera
- **Ramas de trabajo:** `feature/proteger-emision-facturas`,
  `feature/despliegue-automatico`, `feature/recrear-tuneles-caidos`,
  `feature/detalles-caja-y-facturas`, `feature/emitir-solo-a-pedido`,
  `feature/actividad-economica-emisor`, `feature/reportes-con-caja` y
  `feature/terminal-autoservicio`. Release `v5.0` (Hito 7).

---

## Contexto

Al cierre del Sprint 4 la facturación electrónica ya estaba integrada pero sin
emitir (el equipo tiene solo 12 números de factura), y faltaban el script de
despliegue automático (criterio SCR del Hito 7), la factura real y el tag. En
el Sprint 6 (Hito 8, la entrega final) la guía pide además reportes y tablero
de ganancias, el script de producción funcionando y, en QA, el manejo completo
de transacciones **incluyendo la terminal de autoservicio**, que no existía.

## Qué se le pidió a la IA (y qué se hizo)

### 1. Proteger los números de factura

- **Pedido:** revisar el trabajo hecho en otra sesión sobre facturación y
  corregir lo que estuviera mal.
- **Qué se hizo:** una factura "sin confirmar" (se cortó la conexión al
  emitir) ya no suelta su número ni se vuelve simulada; con la emisión
  prendida, solo el administrador puede emitir. Después, a pedido del equipo,
  se fue un paso más lejos: **un pago nunca emite solo**; la factura queda
  validada y el administrador la emite con el botón "Emitir".

### 2. Script de despliegue automático (SCR)

- **Pedido:** un comando para levantar desarrollo y producción con código,
  base y datos.
- **Qué se hizo:** `desplegar.py --ambiente desarrollo|produccion`, que clona
  el repo si hace falta, elige un tag, puede empezar con base nueva y delega en
  los scripts que ya existían. Los datos de ejemplo pasaron a usar claves
  naturales (usuarios, monedas, billetes) para cargarse sobre una base usada,
  y se agregó el guaraní con sus billetes. También se corrigió `publicar.py`
  para recrear los túneles que Cloudflare da de baja.

### 3. Validar contra Factura Segura con el token real

- **Pedido:** probar el token del equipo sin gastar números.
- **Qué se hizo:** se validaron compras y ventas, con y sin comisión, con
  `calcular_de`; los totales y el IVA coincidieron con lo cobrado. Se detectó
  que faltaba la actividad económica del emisor, y más tarde que dos formatos
  de esa configuración (uno viejo y uno en lista) se pisaban: el arranque y las
  facturas fallaban. Se aceptaron los dos formatos.

### 4. Release del Hito 7

- **Pedido:** dejar todo listo para la entrega, con el tag que faltaba.
- **Qué se hizo:** merge `develop → main` y tag `v5.0`.

### 5. Reportes con las operaciones de caja (Hito 8)

- **Pedido:** revisar qué le faltaba al Hito 8.
- **Qué se hizo:** los reportes y el tablero solo contaban las operaciones de
  la web. Se juntaron con las de la caja en un formato común (con el tipo
  siempre desde el cliente), y el reporte muestra el origen y permite filtrar
  por web o caja.

### 6. Terminal de autoservicio (Hito 8, QA)

- **Pedido:** construir lo que faltara para terminar el proyecto.
- **Qué se hizo:** una app `terminal` con una pantalla de quiosco. El cliente
  reserva la operación y recibe un código; en la terminal deposita los billetes
  y recibe la divisa o los guaraníes (o se le acreditan en la cuenta) con su
  vuelto. Si la cotización cambió, la operación se cancela y se devuelven los
  billetes. Se agregó el stock de billetes por terminal, una pantalla de
  estado para administrador y cajero, la API y un menú en la maqueta.
  Detalle en `docs/terminal-autoservicio.md`.

## Qué se descartó y por qué

- **Emitir facturas automáticamente al pagar:** se descartó porque con 12
  números cualquier prueba o demo podía gastarlos sin querer.
- **Reescribir los scripts de arranque para el despliegue:** se prefirió un
  envoltorio (`desplegar.py`) sobre los que ya funcionaban.
- **Que la terminal ofrezca aceptar la cotización nueva:** se mantuvo la misma
  regla que la web (si cambió, se cancela), porque es la que pide la ERS para
  las operaciones pendientes. Queda anotado como supuesto a confirmar.
- **Una pantalla de terminal con inicio de sesión:** una terminal de
  autoservicio la usa cualquier cliente con su código, como un cajero
  automático; el código de 8 caracteres al azar identifica la operación.

## Verificación

- 385 pruebas unitarias en verde (`manage.py test`), documentación Sphinx y
  build de la maqueta sin errores.
- Prueba en pantalla con un navegador real: reserva desde la maqueta como
  cliente, compra en la terminal con vuelto, venta con acreditación en cuenta,
  lista de reservas actualizada, estado de la terminal y reportes.
- La versión de producción se levantó en una copia local aislada (otro
  proyecto de Docker, sin túneles): migró, cargó los datos de ejemplo y
  completó una operación en la terminal.
- Facturas: validadas contra Factura Segura sin gastar números.
