# Integración con Factura Segura (facturación electrónica)

Global Exchange emite la factura electrónica de cada operación pagada a través
de **Factura Segura**, que arma el XML, lo firma y lo manda al SIFEN de la
DNIT. Esta guía explica cómo configurarlo, cómo funciona y cómo probarlo sin
gastar números de factura. La referencia del código está en la documentación
de Sphinx (sección "Facturación electrónica").

Especificación de la API: *API de Factura Segura para ESI v01*.

## Lo más importante: los números son pocos

La cátedra le asignó al equipo:

| Documento | Rango | Cantidad |
|---|---|---|
| Facturas electrónicas | `001-003-0000382` a `001-003-0000393` | 12 |
| Notas de crédito | `001-003-0000157` a `001-003-0000168` | 12 |

Cada factura emitida gasta un número. Por eso **por defecto no se emite nada**:

| Configuración | Qué pasa al pagar una operación |
|---|---|
| Sin token | La factura queda **simulada**. No se llama a Factura Segura. |
| Con token, `FACTURA_SEGURA_EMITIR=0` | Se **valida** con `calcular_de` (no genera nada ni gasta números) y queda simulada. |
| Con token, `FACTURA_SEGURA_EMITIR=1` | Se reserva un número del rango y se **emite de verdad** con `generar_de`. |

Los tests nunca emiten ni salen a la red: `config/settings.py` apaga el token
y la emisión cuando se corre `manage.py test`.

## Configuración

Va en `backend/.env.facturasegura`, un archivo aparte del `.env`. Se crea
copiando `backend/.env.facturasegura.example`, que explica cómo conseguir el
token y qué es cada variable.

- Está ignorado por git (regla `.env*`). **Nunca** se commitea.
- `levantar_todo.py` no lo borra: solo borra los archivos llamados `.env`.
- Producción usa el mismo archivo (`env_file` del servicio `backend` en
  `docker-compose.prod.yml`), así que `publicar.py` no necesita nada más.

Hacen falta tres cosas: el **token** del usuario ESI, los **datos del emisor**
(RUC, razón social, dirección, actividad económica) y el **timbrado** (número
y fecha de inicio). Sin los datos del emisor no se llama a Factura Segura: la
factura queda en error con la lista de lo que falta.

## A nombre de quién sale

El receptor es siempre el **cliente** de la operación, nunca el usuario que la
cargó (RN02). Sale de `Cliente.nombre`, `Cliente.correo` y `Cliente.ruc`:

- `ruc` con guion (`2595733-3`): contribuyente. Se valida el dígito verificador.
- `ruc` sin guion (`4567890`): no contribuyente, identificado con su cédula.
- Sin `ruc`: la factura queda en **error** y se puede reintentar después de
  cargarlo.

El RUC lo carga el administrador en el formulario de **Clientes** de la
maqueta (campo "RUC o Cédula").

## Qué se factura

Son supuestos a confirmar con la cátedra:

- **El cliente compra divisa** (la casa vende, `iTipTra` 5): un ítem exento de
  IVA por el monto en guaraníes y, si hay comisión, un ítem gravado al 10 %.
  El total es lo que pagó el cliente.
- **El cliente vende divisa** (la casa compra, `iTipTra` 6): un ítem exento
  por el monto en guaraníes, con la comisión como descuento. El total es lo
  que recibió el cliente.

Los ítems van en guaraníes y con cantidad 1, para que el total coincida con lo
cobrado sin decimales. Factura Segura solo admite PYG o USD como moneda de la
operación.

## Flujo

1. Una operación queda **pagada** (por cualquiera de los caminos). La señal
   `facturacion.senales` llama a `servicio.facturar` después del `commit`.
2. Se arma el documento resumido (`armar_de`) y se completa con `calcular_de`.
3. Si la emisión está prendida, se reserva el número y se manda `generar_de`.
   Factura Segura devuelve el **CDC** (44 dígitos) y la factura queda
   **enviada**.
4. Un minuto después se consulta `get_estado_sifen` (botón "Consultar
   estado"): **aprobada**, **rechazada** o todavía en proceso.
5. Con CDC se descargan el **KuDE** (PDF) y el **XML** firmado. El backend los
   baja de Factura Segura y los reenvía: el token no llega al navegador.

Un problema con la factura nunca deshace el pago: queda registrado en el
estado y el detalle de la factura.

## Estados

| Estado | Significa | Número |
|---|---|---|
| Simulada | No se emitió (emisión apagada o sin token) | No gasta |
| No se pudo emitir | Faltan datos o Factura Segura dijo que no | Se libera |
| Sin confirmar | Se cortó la conexión al emitir: pudo haberse procesado | Se conserva |
| Enviada | Factura Segura la tiene; falta la respuesta del SIFEN | Usado |
| Aprobada | El SIFEN la aprobó | Usado |
| Rechazada | El SIFEN la rechazó (el motivo queda en el detalle) | Se conserva para reintentar |
| Cancelada | Se canceló o inutilizó en el SIFEN | Usado |

**Reintentar** vuelve a mandar las que fallaron, con el mismo número si ya
tenían uno. Las simuladas no se emiten solas al prender la emisión: hay que
pedirlo con el botón "Emitir", una por una.

## Pantallas y API

- Django: `/facturas/` (lista con filtro por estado y cuántos números quedan)
  y `/facturas/<id>/` (detalle, descargas, consultar estado, reintentar).
- Maqueta: menú **Facturas**.

| Método | Ruta | Qué hace |
|---|---|---|
| GET | `/api/facturas/` | Facturas visibles y si la emisión es real o simulada |
| POST | `/api/facturas/<id>/actualizar/` | Consulta el estado en el SIFEN |
| POST | `/api/facturas/<id>/reintentar/` | Vuelve a emitir una que falló |
| GET | `/api/facturas/<id>/kude/` | Descarga el KuDE (PDF) |
| GET | `/api/facturas/<id>/xml/` | Descarga el XML firmado |

Cada uno ve las facturas de las operaciones que puede ver: el cliente las de
sus clientes; administrador, analista y cajero, todas.

## Cómo probar sin gastar números

```
cd backend
.venv\Scripts\python manage.py test facturacion
```

Para verlo en pantalla: pagar una operación con un cliente que tenga RUC y
entrar a **Facturas**. Con la emisión apagada queda simulada.

## Pendiente

- Notas de crédito y cancelación (`sol_cancelacion`) al anular una operación.
- Facturar las operaciones de la caja (ventanilla), que hoy no generan factura.
