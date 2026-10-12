# Integración con Stripe (pagos con tarjeta)

Global Exchange cobra con tarjeta a través de **Stripe en modo test**: no se
mueve dinero real. Esta guía explica cómo configurarlo, cómo funciona cada
flujo y cómo probarlo. La referencia del código está en la documentación de
Sphinx (sección "Pagos con tarjeta").

## Configuración

Las claves salen del dashboard de Stripe, con *Test mode* encendido:
**Developers → API keys** (`pk_test_...` y `sk_test_...`).

**Desarrollo.** Van en `backend/.env.stripe`, un archivo aparte del `.env`.
Se crea copiando `backend/.env.stripe.example`, que explica paso a paso cómo
crear la cuenta de Stripe (gratis, modo test) y dónde encontrar las claves:

```
STRIPE_PUBLISHABLE_KEY=pk_test_...
STRIPE_SECRET_KEY=sk_test_...
```

- Está ignorado por git (regla `.env*`). **Nunca** se commitea.
- `levantar_todo.py` no lo borra: solo borra los archivos llamados `.env`.
- Cada integrante crea el suyo. Sin claves, el sistema funciona igual y los
  pagos con tarjeta quedan deshabilitados (se avisa con un mensaje).

**Producción.** `STRIPE_PUBLISHABLE_KEY` y `STRIPE_SECRET_KEY` en `.env.prod`
(opcionales; ver `.env.prod.example` y `docker-compose.prod.yml`).

**Dependencias.** `stripe` en `backend/requirements.txt`;
`@stripe/stripe-js` y `@stripe/react-stripe-js` en el frontend.

La clave publicable no se configura en el frontend: la maqueta la pide a
`GET /api/pagos/configuracion/`, así las claves viven en un solo lugar.

## Principio de seguridad

El número y el CVV de la tarjeta **nunca pasan por nuestro backend**. Se
escriben en el campo de Stripe (`CardElement`, Stripe Elements) y van directo a
Stripe. El backend recibe solo identificadores (`seti_...`, `pm_...`,
`pi_...`) y le consulta a Stripe el resto. De cada tarjeta se guarda:

- `MedioPago.stripe_payment_method_id`: el `pm_...` con el que se cobra.
- La marca (`banco_o_proveedor`), los últimos 4 dígitos
  (`numero_cuenta_o_tarjeta`) y el vencimiento (`tarjeta_vencimiento`).

La API rechaza cualquier intento de cargar una tarjeta con el número en crudo.

Toda la comunicación con Stripe está en `backend/pagos/servicio.py`; el resto
del sistema no importa la librería.

## Flujos

### Cargar una tarjeta (Medios de pago)

1. La maqueta pide un SetupIntent: `POST /api/medios-pago/tarjetas/preparar/`.
   El backend crea (la primera vez) el *Customer* de Stripe del usuario
   (`pagos.CuentaStripe`) y devuelve el `client_secret`.
2. Stripe.js confirma el SetupIntent con la tarjeta (`confirmCardSetup`). Si
   el banco pide 3D Secure, Stripe muestra la verificación.
3. La maqueta registra la tarjeta: `POST /api/medios-pago/tarjetas/` con el id
   del SetupIntent. El backend verifica en Stripe que sea de ese usuario y
   esté aprobado, y lee de ahí los datos de la tarjeta.

Eliminar una tarjeta la desvincula del Customer en Stripe. Si ya se usó en
operaciones de caja, el medio de pago se desactiva en vez de borrarse, para
conservar el historial.

### Compra y venta en la web

- **Compra** (el cliente compra divisa): se cobra el **total en guaraníes**.
- **Venta** (el cliente vende divisa): se cobra el **monto de divisa** que
  entrega, en esa moneda. Simula que el cliente entrega la divisa; Stripe no
  permite pagarle a una tarjeta de forma simple.

Al confirmar (`POST /api/operaciones/confirmar/`):

1. Si la cotización cambió desde el cálculo, la operación se registra
   cancelada **sin cobrar** (regla de siempre).
2. Si no, se crea la operación pendiente y se cobra con un PaymentIntent
   confirmado con la tarjeta guardada.
3. Aprobado: la operación queda **PAGADA**. Rechazado: no se registra nada y
   se muestra el motivo.
4. Si el banco pide **3D Secure**: queda **PENDIENTE** y la respuesta trae
   `pagoPendiente.clientSecret`. La maqueta muestra la verificación
   (`handleNextAction`) y llama a `POST /api/operaciones/<id>/verificar-pago/`;
   el backend consulta a Stripe (monto y moneda incluidos) y la marca pagada.

**Operaciones que quedaron pendientes** (el 3D Secure falló o no se terminó):
desde el Historial de Transacciones se pueden **pagar** o **cancelar**. Antes
de reintentar o cancelar, el backend consulta el cobro anterior en Stripe: si
ya se había aprobado (el cliente completó la verificación pero se cerró la
página), la operación queda pagada sin cobrar de nuevo; si no, ese cobro se
cancela en Stripe.

Con medios de pago que no son tarjetas de Stripe no se cobra nada: se
registra como antes.

### Caja (ventanilla)

El cajero puede cobrar con las tarjetas de los usuarios asociados al cliente
(`GET /api/caja/clientes/<id>/tarjetas/`).

- **Venta de caja** (la casa vende divisa): se cobra el total en guaraníes.
- **Compra de caja** (la casa compra divisa): se cobra el monto de divisa.

La operación se registra solo con el cobro aprobado. Con 3D Secure, el
backend responde `202` con `pagoPendiente`; la maqueta completa la
verificación y reenvía la operación con `payment_intent_id`. Un mismo cobro no
puede registrar dos operaciones.

**Arqueo.** Lo cobrado con tarjeta no pasa por el cajón:

- Compra con tarjeta: la divisa no entra al cajón (se informa aparte en el
  cierre); los guaraníes que se le pagan al cliente sí salen.
- Venta con tarjeta o transferencia: la divisa sale; los guaraníes no entran.
- Venta en efectivo: la divisa sale y los guaraníes entran.

## Sin webhooks

El estado de cada pago se consulta a Stripe en el momento (al confirmar, al
verificar el 3D Secure, al reintentar o cancelar). Los webhooks requieren el
`stripe` CLI en cada máquina para el desarrollo local; se pueden agregar más
adelante si hacen falta.

## Cómo probar

Tarjetas de prueba (vencimiento futuro y cualquier CVC):

- `4242 4242 4242 4242`: aprobada.
- `4000 0027 6000 3184`: pide 3D Secure siempre.
- `4000 0000 0000 0002`: rechazada.

Los cobros se ven en el dashboard de Stripe (*Test mode*) en **Payments**, y
los clientes con sus tarjetas en **Customers**.

Pruebas automáticas (Stripe simulado, sin red):

```
cd backend
.venv/bin/python manage.py test pagos operaciones caja medios_pago
```

El paso a paso de prueba manual completo está en
`docs/conversaciones-ia/2026-10-12-integracion-stripe.md`.
