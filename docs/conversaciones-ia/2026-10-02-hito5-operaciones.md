# Operaciones de compra/venta, cancelación e historial (Hito 5)

- **Fecha:** 2 de octubre de 2026
- **Herramienta:** Claude (Anthropic), a través de Claude Code
- **Integrante:** Milner Noguera (autenticación y control de roles; historia IS2GE-70)
- **Punto de partida:** `develop` en el commit `4c395f5`

---

## Contexto

Había que cerrar el alcance del Sprint 3 (criterio ALC del Hito 5):
operación de compra/venta con cálculo de comisión y tasa aplicada,
cancelación de la transacción si cambia la cotización antes del pago, e
historial de transacciones de solo consulta. La versión que circulaba en el
equipo era que solo faltaba el historial.

## Decisiones

- **Usar solo el repositorio de entrega** (`origin`) de acá en adelante, y
  alinear `develop` con él (el anterior quedó respaldado en una rama).
- **Verificar antes de dar por buena la versión del equipo.** La revisión
  mostró que en `develop` no estaba ninguno de los tres ítems. Pedí además
  buscar en todas las ramas de los dos repositorios, en los pull requests y en
  posibles forks, por si había trabajo subido en otro lado: lo único era un
  borrador en `feature/IS2GE-32`, que no funcionaba.
- **Respetar el reparto de Jira.** Con la captura del tablero se asignaron las
  ramas: el backend de las historias de Gabriela (IS2GE-63 a 67) sobre su
  propia rama `feature/IS2GE-32`, construyendo encima de su commit para que
  quede su autoría; la alerta de cancelación en `feature/IS2GE-71` (JF); el
  historial, mi historia, en `feature/IS2GE-70`.
- **Respetar las reglas de negocio que el equipo ya había definido** en vez
  de inventar otras: el descuento por segmento sobre el precio de venta lo
  aplicaba la maqueta, y se mantuvo igual en el backend.
- **Producción: dejarla preparada, no montarla todavía.** El servidor lo
  decide el equipo.

## Qué se encontró

- El borrador de IS2GE-32 importaba Django REST Framework (no instalado:
  rompía el proyecto al cargar las urls) y leía un campo de `Moneda` que no
  existe. No calculaba comisión ni tenía forma de crear una operación.
- En la maqueta, "Confirmar" en compra y venta solo mostraba un mensaje: no se
  registraba nada. El historial era una lista escrita a mano y permitía
  cancelar operaciones de menos de 24 horas, que no es una regla de la ERS y
  contradice el "solo consulta".
- El fixture de demo ya no cargaba en una base nueva (cambios de modelo
  posteriores al Hito 4).

## Qué se implementó

| Rama / PR | Qué |
|---|---|
| `feature/IS2GE-32` (#8) | Modelo de transacción (RN02, estados de RN04), cálculo de tasa aplicada y comisión, pago con cancelación automática si cambió la cotización, pantallas de Django, API para la maqueta, y compra/venta de la maqueta conectadas al backend |
| `feature/IS2GE-71` (#9) | Alerta de cancelación: precio anterior y nuevo, cuánto saldría ahora, y "volver a operar" con los datos precargados; en Django y en la maqueta |
| `feature/IS2GE-70` (#10) | Historial de solo consulta con filtros (estado, tipo, moneda, cliente, fechas), paginado, por pantalla y por API; la maqueta lee la base |
| `feature/ambiente-produccion` (#11) | Ambiente de producción con Docker (criterio AMB) y fixture de demo arreglado |

La cancelación compara el **precio** usado al crear la operación contra el
vigente al pagar, porque la cotización cambia de dos maneras distintas (la
maqueta crea una nueva; la pantalla de Django edita la existente).

## Verificación

- **134 pruebas unitarias** en verde (71 nuevas en `operaciones`).
- Sphinx compila sin warnings, con el módulo nuevo documentado.
- **Prueba de punta a punta con el sistema corriendo** (Keycloak real, login
  con usuario y contraseña): compra con descuento y comisión, cambio de
  cotización antes del pago → cancelación con alerta, venta y pago por la API
  con CSRF real, historial filtrado, y un usuario sin cliente (RN02).
- **El ambiente de producción se levantó en una máquina local** siguiendo la
  guía (`docs/despliegue-produccion.md`) y se probó el flujo completo; después
  se bajó.

## Queda abierto

- **Los descuentos de la semilla de segmentos** (5 %, 10 %, 15 % sobre el
  precio de venta) dejan la tasa aplicada por debajo del precio de compra: con
  USD a 7.300 / 7.400, cualquier segmento compraría a menos de lo que la casa
  paga. Es una decisión de negocio del equipo, no se cambió.
- Elegir el servidor de producción y montarlo.
- La planificación de casos de uso del próximo sprint, el tablero de Jira
  (criterio PLA) y el tag de la versión.
