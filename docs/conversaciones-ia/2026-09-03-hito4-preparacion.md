# Preparación de la entrega del Hito 4

- **Fecha:** 3 y 4 de septiembre de 2026
- **Herramienta:** Claude (Anthropic), a través de Claude Code
- **Integrante:** Milner Nogue (autenticación y control de roles)
- **Punto de partida:** `develop` en el commit `1f74e51`

---

## Contexto

A un día de la entrega del Hito 4 (Sprint 2), revisé con la IA qué parte del
alcance estaba realmente terminada y qué faltaba, verificando el sistema en
funcionamiento en vez de leer el código y asumir.

## Decisiones

- Confirmé que el proyecto se evalúa por las pantallas de Django, no por la
  maqueta React (la guía de la cátedra pide diagramas "(Django)" y el criterio
  FRA evalúa el framework).
- Al leer el primer análisis, encontré que había descartado un ítem del
  alcance (los porcentajes de comisión) dándolo por indefinido. Pedí releer la
  guía de la cátedra, que sí lo define, repartido entre el Sprint 2
  (configuración) y el Sprint 3 (cálculo). También había quedado sin revisar
  la mitad de los seis ítems del criterio ALC.
- No autoricé tocar el modelo `Cliente` (es de Gabriela y Juan Cruz) hasta
  confirmarlo; di el visto bueno recién cuando hacía falta para asociar el
  segmento de comisión.
- Dejé la clave foránea de medios de pago (¿usuario o cliente?) para
  consultar con la profesora en vez de cambiarla por mi cuenta — altera RN02 y
  no está confirmado.
- Prioricé qué resolver antes de la entrega: primero que los permisos del
  analista_cambiario coincidieran con la ERS, después la asociación de
  comisiones por cliente.

## Qué se implementó, bajo esa dirección

- Las pantallas de monedas, cotizaciones y medios de pago (estaban vacías).
- La regla RN10 (compra menor que venta) aplicada también en las vistas, no
  solo en el modelo — antes se podía saltear guardando directo.
- Los ítems de alcance que faltaban: configuración de comisión por segmento de
  cliente, visualización de tasas, simulador de conversión.
- Permisos del `analista_cambiario` corregidos para que coincidan con lo que
  dice la ERS (modificar tasas, no administrar el sistema).
- Asociación entre `Cliente` y `SegmentoCliente`, con el porcentaje de
  comisión expuesto para el cálculo del Sprint 3.
- Corrección del logout: cerraba sesión en Django pero Keycloak rechazaba la
  redirección de vuelta ("Invalid redirect uri"); ahora vuelve al login.
- Documentación técnica generada con Sphinx a partir de los docstrings.
- 63 pruebas unitarias en total (eran 23).

## Verificación

```bash
cd backend && .venv\Scripts\python manage.py test
# → Ran 63 tests ... OK

cd backend && .venv\Scripts\python manage.py check
# → System check identified no issues

cd docs && ../backend/.venv/Scripts/python -m sphinx -b html . _build/html
# → build succeeded (0 warnings), 106 símbolos documentados
```

## Estado del alcance del Sprint 2

| # | Ítem del criterio ALC | Estado |
|---|---|---|
| 1 | CRUD de Monedas | ✅ |
| 2 | CRUD de Cotizaciones | ✅, RN10 se cumple |
| 3 | CRUD de medios de pago cliente | ⚠️ funciona, pero la FK va al usuario |
| 4 | Visualización de tasas | ✅ |
| 5 | Configuración de porcentajes de comisión | ✅ (el cálculo es del Sprint 3) |
| 6 | Simulador de conversión | ✅ |

## Queda pendiente

1. Consultar con la profesora la FK de medios de pago (usuario vs. cliente).
2. Abrir los PR de `feature/crud-cotizaciones` y `feature/crud-medios-pago`
   hacia `develop` en el repositorio de entrega.
3. Crear el tag del sprint desde la rama principal, una vez mergeado.
4. Renombrar las ramas a `feature/SCRUM-XX` con el id de Jira.
5. Verificar en JIRA que el sprint actual esté cerrado y el siguiente
   planificado (criterio PLA).
