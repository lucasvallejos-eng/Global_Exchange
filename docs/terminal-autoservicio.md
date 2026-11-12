# Terminal de autoservicio (TAUser)

La terminal de autoservicio es la máquina donde el cliente completa **con
efectivo** una compra o venta de divisas, sin pasar por la ventanilla. En el
sistema es una pantalla de quiosco (`/terminal/`) que simula la máquina: el
validador de billetes se reemplaza por campos donde se carga cuántos billetes
de cada denominación se depositan.

## El circuito

1. **Reserva.** El cliente crea la operación y elige pagarla en la terminal.
   Queda **pendiente** y recibe un **código de 8 caracteres** (sin letras que
   se confundan, como O/0 o I/1). Se reserva de dos maneras:
   - en la maqueta, menú **Terminal de Autoservicio** → operación, moneda y
     monto → **Reservar**;
   - en Django, **Operar** → crear la operación → en el detalle, **Pagar en la
     terminal (efectivo)**.
2. **En la terminal** (`/terminal/` → elegir la terminal → ingresar el código):
   - si **compra** divisa, deposita **guaraníes** por el total (con la
     comisión) y retira la divisa;
   - si **vende** divisa, deposita la **divisa** y elige **retirar los
     guaraníes** en efectivo o **acreditarlos** en la cuenta del cliente
     (`Cliente.cuenta_acreditar`).
3. **Al confirmar**, la terminal:
   - controla que lo depositado alcance y que tenga billetes para devolver el
     **vuelto** y para **entregar** lo que corresponde (empieza por los
     billetes más grandes). Si no puede, **no cambia nada**: devuelve los
     billetes y la operación sigue esperando (el cliente puede ir a otra
     terminal o cancelarla);
   - paga la operación con la misma regla de la web: **si la cotización cambió
     desde la reserva, la operación se cancela** y se devuelven los billetes;
   - si quedó pagada, mueve los billetes de la terminal (entra lo depositado,
     sale el vuelto y lo entregado) y muestra el comprobante.
4. **Cancelación.** El cliente puede cancelarla en la terminal (botón
   **Cancelar la operación**) o en la web, como cualquier pendiente. Si se
   canceló o pagó por la web, la terminal ya no la acepta.

Al quedar pagada se genera la **factura**, igual que en la web, y el cliente
recibe la notificación de operación exitosa.

## Ejemplo (datos de ejemplo, sin segmento)

| Operación | Deposita | Recibe |
|---|---|---|
| Compra de 10 USD a 7.400 | 1 billete de 100.000 PYG | 10 USD y 26.000 PYG de vuelto (20.000 + 5.000 + 1.000) |
| Venta de 20 USD a 7.300 | 1 billete de 20 USD | 146.000 PYG en efectivo, o acreditados en la cuenta |

## Quién ve qué

| Pantalla | Quién |
|---|---|
| `/terminal/`, `/terminal/<id>/`, `/terminal/<id>/<código>/` | Cualquiera, sin iniciar sesión (es la máquina; el código identifica la operación) |
| Reservar (maqueta o detalle de la operación) | Quien opera a nombre del cliente (RN02) |
| `/terminal/estado/` (billetes de cada terminal y últimas operaciones) | Administrador y cajero |
| Cargar terminales y billetes | Admin de Django (`/admin/terminal/terminal/`) |

## Datos de ejemplo

`backend/fixtures/demo.json` trae la **Terminal Centro** con billetes de PYG,
USD y EUR. Cada `loaddata` (por ejemplo, cada `levantar_todo.py`) vuelve a
dejar esas cantidades.

## API (maqueta)

| Método | Ruta | Qué hace |
|---|---|---|
| GET | `/api/terminal/reservas/` | Las reservas de los clientes del usuario, con su estado |
| POST | `/api/terminal/reservas/` | `{clienteId, tipo, moneda, monto}`: crea la operación pendiente y la reserva; devuelve el código |
| GET | `/api/terminal/terminales/` | Las terminales habilitadas |

## Código

- `backend/terminal/models.py`: `Terminal`, `BilleteTerminal` (stock) y
  `OperacionTerminal` (la reserva, con lo depositado y lo entregado).
- `backend/terminal/servicio.py`: todas las reglas (`reservar`, `buscar`,
  `completar`, `cancelar`, `desglosar`).
- `backend/terminal/views.py` y `backend/templates/terminal/`: las pantallas.
- `backend/terminal/tests.py`: compra con vuelto, venta en efectivo y con
  acreditación, depósito insuficiente, sin billetes para entregar, sin cambio,
  cambio de cotización, cancelación, factura y el recorrido en pantalla.

## Supuestos

La ERS original no estaba a mano al construirla. Se tomó el comportamiento
típico de una terminal de casa de cambios. Si la cátedra pide otra cosa (por
ejemplo, que la terminal ofrezca aceptar la cotización nueva en vez de
cancelar), el cambio va en `terminal/servicio.py::completar`.
