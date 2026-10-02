# Arranque con un solo botón y correcciones antes del tag (IS2GE-110)

- **Fecha:** 2 de octubre de 2026
- **Herramienta:** Claude (Anthropic), a través de Claude Code
- **Integrante:** Juan Cruz Cordero
- **Punto de partida:** `develop` en el commit `2183f1a` (después del PR #12)
- **Rama:** `IS2GE-110/fixes-varios-pre-tag`

---

## Contexto

Antes de la demo del Hito 5 había que probar de punta a punta lo que el
equipo subió (operaciones de compra/venta, alerta de cancelación, historial),
siguiendo la guía de prueba que armó un compañero. Para levantar el sistema
hacían falta tres terminales en orden (Keycloak, backend y maqueta). La idea
era arrancarlo con un solo botón y, mientras se probaba, corregir lo que no
quedara presentable para la demo.

## Qué se le pidió a la IA

1. Revisar el proyecto entero y dejar **un solo "Play" en PyCharm** que
   levante todo.
2. Comparar la guía de prueba del compañero con el estado real de la máquina
   (usuarios en Keycloak y en la base, datos de demo, rutas).
3. Ir corrigiendo lo que aparecía durante la prueba, siempre **dentro de la
   maqueta**: la demo no puede depender de escribir URLs de Django a mano.
4. Llevar todo a una rama aparte para mergearlo con `develop` y `main` cuando
   esté probado.

## Qué se hizo

### 1. `levantar_todo.py`: el sistema completo con un solo comando

Un script en la raíz que:

1. Levanta Keycloak, su Postgres y Mailpit (`docker compose up -d`).
2. Espera a que el realm responda. La URL sale de `KEYCLOAK_ISSUER`, así que
   funciona con Keycloak en otro puerto.
3. Aplica las migraciones y arranca Django en el 8000.
4. Arranca la maqueta en el 8443. Si falta `node_modules`, corre
   `pnpm install` primero.
5. Muestra la salida de los dos en la misma consola, con el prefijo
   `[backend]` o `[frontend]`.
6. Al apretar **Stop** o **Ctrl+C**, cierra backend y frontend sin dejar
   procesos colgados. En Windows usa un *Job Object* para que Windows mate a
   los procesos hijos aunque el IDE corte el script de golpe.

Los contenedores de Keycloak quedan corriendo para que el próximo arranque sea
inmediato. Cómo usarlo en cada sistema e IDE está en la
[guía de abajo](#guía-levantar_todopy-en-cada-sistema-e-ide).

### 2. Correcciones encontradas al probar

| Problema | Causa | Corrección |
|---|---|---|
| No había forma de asignar el segmento VIP a un cliente desde la maqueta | El campo "Categoría" de Clientes no se guardaba; la asignación solo existía en `/comisiones/asignar/` de Django | El campo pasa a ser **Segmento**: se llena con los segmentos reales (con su comisión) y se guarda en el backend. La tabla muestra, por ejemplo, "VIP · 0.5%" |
| En Medios de pago, el usuario aparecía como un hash (`QcXkp0e_…`) | mozilla-django-oidc guarda por defecto un hash del `sub` como nombre de usuario | Se usa el `preferred_username` de Keycloak. Los usuarios que ya existían se corrigen en su próximo login |
| En Configuración de Datos aparecía "juan123 / juan.perez@email.com" para cualquier usuario | Los datos estaban escritos a mano, y "Guardar" y "Actualizar contraseña" solo mostraban un mensaje de éxito | Muestra los datos reales de la sesión (solo lectura). La contraseña se cambia en la consola de cuenta de Keycloak (RN05), con un botón que lleva ahí |
| Desde la maqueta nunca se podía cambiar una cotización ("faltan 60 minutos") | El bloqueo de 1 hora se medía desde `Moneda.fecha_actualizacion`, que es `auto_now` y se pisaba al guardar la moneda justo antes de chequear | **Se quitó el bloqueo** (ver decisiones). Además, editar una moneda sin cambiar precios ya no crea una cotización nueva |
| La pantalla de Cotizaciones del cliente no se enteraba de que el analista cambió el precio | Las cotizaciones se pedían una sola vez al abrir la pantalla | Se refrescan cada 5 segundos y al volver a la pestaña (compra, venta, cotizaciones y simulación) |
| Cada vez que se tocaba "Comprar" o "Vender" aparecía una fila nueva en el historial, y recargar con el modal abierto dejaba la operación "Pendiente de pago" para siempre | El botón creaba la operación pendiente antes de que el cliente confirmara | **La operación se registra recién al confirmar** (ver abajo) |
| En Medios de pago, el tipo decía `TARJETA_CREDITO` | Se mostraba el código en vez del texto | Muestra "Tarjeta de Crédito" |

#### El flujo nuevo de compra y venta en la maqueta

| El cliente… | Antes | Ahora |
|---|---|---|
| toca **Comprar / Vender** | se creaba una operación *Pendiente* | solo se calcula (`POST /api/operaciones/cotizar/`); no se guarda nada |
| **confirma** | se pagaba la pendiente | se registra ya *Pagada* (`POST /api/operaciones/confirmar/`) |
| confirma, pero **la cotización cambió** | se cancelaba la pendiente | se registra una sola vez como *Cancelada por cambio de cotización* y aparece la alerta |
| **cancela** o **recarga** la página | quedaba *Cancelada* o *Pendiente* | no queda nada |

Al confirmar, la maqueta manda la tasa base del cálculo que se le mostró al
cliente. El backend la compara con el precio vigente, igual que hacía `pagar`
con una operación pendiente. Las pantallas de Django (`/operaciones/nueva/`)
siguen con el flujo anterior: ahí la confirmación tiene su propio botón
"Cancelar operación".

## Decisiones

- **Un script en vez de una "Compound" de PyCharm.** Una configuración
  compuesta arranca todo a la vez, pero no espera a que Keycloak esté listo, y
  solo sirve en PyCharm. El script ordena el arranque y además sirve en VS
  Code y en la terminal.
- **Quitar el bloqueo de 1 hora entre cambios de cotización.** Una moneda
  puede cambiar varias veces en una hora. Estaba documentado como regla de
  auditoría en `docs/index.rst` y se sacó de ahí también. **Hay que
  confirmarlo con el equipo** por si salía de la ERS. El historial de cambios
  (`HistorialCotizacion`) se sigue registrando igual.
- **No tener un formulario propio para cambiar la contraseña.** Las
  credenciales las maneja Keycloak (RN05). Un formulario en la maqueta no
  podría cambiarlas de verdad, así que se reemplazó por un botón a la consola
  de cuenta.
- **Registrar la cancelación por cotización, pero no los presupuestos.** Que
  el cliente haya intentado pagar y la cotización haya cambiado es un hecho del
  negocio, y debe quedar en el historial. Abrir el modal y no confirmar, no.

## Qué se descartó y por qué

- **Cambiar la cotización desde la pantalla de Django durante la demo**, que
  era lo que proponía la guía para esquivar el bloqueo. Se descartó porque la
  demo tiene que poder hacerse entera desde la maqueta. Se corrigió la causa
  en lugar de esquivarla.
- **Una explicación equivocada de la IA:** al encontrar a dos clientes de
  demo asociados a usuarios que no correspondían, la IA lo atribuyó primero al
  fixture. Al revisarlo, el fixture trae `"usuarios": []`: eran restos de la
  base local. Se corrigió la explicación y se dejaron los clientes sin
  asociaciones.
- **Un commit anticipado:** al pedir la rama nueva, la IA commiteó los
  cambios antes de que se terminara de probar. Se deshizo con
  `git reset --mixed`, sin perder nada ni subir nada al remoto. Queda como
  regla: no se commitea hasta que se termina de probar.

## Verificación

- **142 pruebas unitarias** en verde. Se agregaron pruebas para el cambio de
  cotización sin bloqueo y para `cotizar` y `confirmar`: calcular no guarda
  nada, confirmar registra la operación pagada y, si la cotización cambió, la
  registra cancelada con los dos precios.
- Las pruebas del cambio de cotización se corrieron también **sin la
  corrección**, para comprobar que detectan el bug. Sin la corrección fallaban.
- **TypeScript** compila sin errores nuevos y Vite sirve todos los módulos
  modificados.
- **Prueba manual completa en la maqueta** con los usuarios `.test`, siguiendo
  la guía del Hito 5:
  - compra VIP de 100 USD = 632.145 PYG;
  - venta de 50 USD = 363.175 PYG;
  - cambio de cotización con el modal abierto, alerta y "volver a operar";
  - historial;
  - RN02 con `cajero.test`.
- `levantar_todo.py`:
  - **Linux**: probado con un PATH mínimo (como lo lanza PyCharm). Responden
    Keycloak, backend y maqueta, y al detenerlo se liberan los puertos sin
    procesos huérfanos.
  - **Windows y VS Code**: los cambios para Windows (*Job Object*, consola
    cp1252, rutas de `Scripts\python.exe`) **no se pudieron probar en una
    máquina Windows**. El primero que lo corra ahí, que avise si algo falla.

## Queda abierto

- Confirmar con el equipo que sacar el bloqueo de 1 hora no contradice la ERS.
- Las pantallas de Django siguen creando la operación pendiente al tocar
  "Continuar". Si se quiere el mismo comportamiento que en la maqueta, hay que
  alinearlas.
- El panel `/admin/` de cotizaciones y la pantalla `/cotizaciones/` de Django
  editan la cotización en el lugar, en vez de crear una nueva como la maqueta.
  El historial de operaciones lo tolera (compara precios), pero conviene
  unificarlo.
- Los descuentos de la semilla de segmentos siguen dejando la tasa de compra
  VIP por debajo de lo que la casa paga (ya anotado en la sesión anterior).

---

## Guía: `levantar_todo.py` en cada sistema e IDE

### Antes de la primera vez (cualquier sistema)

1. **Docker Desktop** instalado y **abierto**.
2. `keycloak/.env` creado a partir de `keycloak/.env.example`.
3. `backend/.env` creado a partir de `backend/.env.example`, con el secret de
   Keycloak.
4. El entorno virtual del backend, con las dependencias:
   - **Windows:**
     `python -m venv backend\.venv` y después
     `backend\.venv\Scripts\pip install -r backend\requirements.txt`
   - **Linux/Mac:**
     `python3 -m venv backend/.venv` y después
     `backend/.venv/bin/pip install -r backend/requirements.txt`
5. **Node.js 20+** en el PATH. En Windows el instalador oficial ya lo agrega.
   En Linux, si usás `nvm`, el script lo encuentra solo aunque el IDE no cargue
   tu `.bashrc`.

**Si Keycloak no está en el 8080.** Por ejemplo, si otra aplicación ocupa
ese puerto y usás un `docker-compose.override.yml` con el 8180. En ese caso,
agregá en `backend/.env`:

```env
KEYCLOAK_ISSUER=http://localhost:8180/realms/GlobalExchange
```

Con eso el backend y el script usan el puerto correcto, y ya no hace falta
escribir `$env:KEYCLOAK_ISSUER=...` en cada terminal.

### Desde la terminal

```bash
# Linux / Mac
backend/.venv/bin/python levantar_todo.py
```

```powershell
# Windows (PowerShell o CMD), desde la carpeta Global_Exchange
backend\.venv\Scripts\python levantar_todo.py
```

Cuando aparece `Todo arriba`, entrá a **http://localhost:8000**. Para cortar,
usá **Ctrl+C**.

### PyCharm (Linux, Mac o Windows)

`.idea/` no se sube al repositorio, así que cada uno crea la configuración una
vez:

1. **Run → Edit Configurations… → + → Python**.
2. **Name:** `Global Exchange (todo)`.
3. **Script path:** `levantar_todo.py` (el de la raíz del proyecto).
4. **Working directory:** la raíz del proyecto (`Global_Exchange`).
5. **Python interpreter:** el del backend.
   - Windows: `backend\.venv\Scripts\python.exe`
   - Linux/Mac: `backend/.venv/bin/python`
6. **OK**. Después elegila en el desplegable de arriba a la derecha y apretá
   el **▶ verde**. Para apagar, usá el **■ rojo**.

### VS Code (Linux, Mac o Windows)

Hace falta la extensión **Python** de Microsoft. Creá `.vscode/launch.json`
en la raíz del proyecto:

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Global Exchange (todo)",
      "type": "debugpy",
      "request": "launch",
      "program": "${workspaceFolder}/levantar_todo.py",
      "cwd": "${workspaceFolder}",
      "console": "integratedTerminal",
      "windows": {
        "python": "${workspaceFolder}/backend/.venv/Scripts/python.exe"
      },
      "linux": {
        "python": "${workspaceFolder}/backend/.venv/bin/python"
      },
      "osx": {
        "python": "${workspaceFolder}/backend/.venv/bin/python"
      }
    }
  ]
}
```

Después:

1. Andá al panel **Run and Debug** (Ctrl+Shift+D).
2. Elegí **Global Exchange (todo)**.
3. Apretá **▶**. También podés usar **Ctrl+F5** (*Run Without Debugging*),
   que arranca más rápido.

Para apagar, usá el **■** de la barra de depuración o **Ctrl+C** en la
terminal.

### Si algo falla

| Mensaje | Qué hacer |
|---|---|
| `Falta keycloak/.env` | Copiá `keycloak/.env.example` a `keycloak/.env` y completalo |
| `No encuentro docker en el PATH` | Instalá Docker Desktop, o abrilo si ya está instalado |
| `Keycloak no respondió a tiempo` | Mirá `cd keycloak && docker compose logs keycloak`. Si está en otro puerto, configurá `KEYCLOAK_ISSUER` (ver arriba) |
| `Puertos ocupados: 8000 / 8443` | Quedó corriendo una ejecución anterior, o otro programa usa el puerto. Cerralo y volvé a intentar |
| `No encuentro node/pnpm` | Instalá Node.js 20+ y reiniciá el IDE para que tome el PATH nuevo |
| Keycloak sigue corriendo después de cerrar | Es a propósito, para que el próximo arranque sea más rápido. Para apagarlo: `cd keycloak && docker compose stop` |
