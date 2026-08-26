# Decisión de arquitectura — Global Exchange

**Equipo 04 · Ingeniería de Software 2 · FP-UNA · 2026**
**Estado: SIN RESOLVER.** Este documento es insumo para la reunión de equipo y la consulta a la
profesora (Product Owner). No decide nada por su cuenta.

---

## 1. El problema en una frase

El repositorio es un **prototipo de interfaz en React** (generado con Figma Make), pero el stack
que el equipo documentó —y que **la cátedra exige**— es **Django**. Son incompatibles tal cual, y
la forma de resolverlo cambia los diagramas de clases, componentes y despliegue del **Hito 2**. Hay
que elegir un camino antes de dibujar esos diagramas.

---

## 2. Django no está en discusión

Esto es lo que acota la decisión: **el "si usamos Django" ya está cerrado por la cátedra.** Solo se
discute *cómo* convive (o no) con el prototipo React.

- La **guía de la cátedra** exige Django de forma explícita: el **Hito 2** pide los diagramas de
  clases, de componentes y de despliegue **"(Django)"**, y el criterio de evaluación **FRA** mide la
  **aplicación del framework**. En **Recursos** solo hay enlaces a Django, incluido *"Django SSO con
  Google"*.
- Consecuencia sobre la ERS: el **RNF03** de la ERS (que menciona *".NET o similar"* y *"React
  recomendado"*) **contradice la guía de la cátedra**. La guía manda sobre la ERS en este punto.
  **Acción:** corregir RNF03 en la próxima versión de la ERS para que diga Django, y así evitar que
  el documento del equipo quede en conflicto con lo que se evalúa.

> **Por qué importa esto:** cualquier opción que descarte Django está descartada de entrada. La
> pregunta real no es "React o Django", sino "**qué hacemos con el prototipo React** dado que Django
> es obligatorio".

---

## 3. Estado real del repositorio (de qué partimos)

Es una **maqueta, no una aplicación.** Conviene tenerlo presente al medir el costo de cada opción.

- React 19 + Vite 8 + TypeScript 5.7 + Tailwind CSS v4.
- **Sin router:** la navegación es `useState` en `App.tsx` (`view: "login" | "register" | "dashboard"`).
- **Sin estado global, sin llamadas de red, sin backend.** Ni un `fetch` en todo el repo.
- Los datos son constantes en memoria (`DEMO_USERS`, `INITIAL_CLIENTS` en `src/types.ts`).
- `LoginPage.tsx` valida contra un diccionario hardcodeado; `RegisterPage.tsx` no persiste nada;
  los botones "Continuar con Google / GitHub" son decorativos.
- Único módulo funcional: `ClientesModule.tsx` (ABM en memoria; se pierde al recargar).

**Lo único aprovechable del prototipo es el markup (HTML/JSX) y las clases de Tailwind.** La lógica
de React es simulada y se iba a rehacer igual en cualquier arquitectura.

---

## 4. Las tres opciones

### A — Django con plantillas (MVT)
Se porta el markup de los `.tsx` a plantillas Django y se descarta React. El HTML lo genera el
servidor. Keycloak se integra con `mozilla-django-oidc`; sesión por cookie; ningún token en el
navegador.

- **A favor:** es lo que el equipo documentó y lo que evalúa FRA; una sola tecnología; la más
  simple; Keycloak queda trivial; el control de roles vive en el servidor por defecto.
- **En contra:** se descarta la lógica React del prototipo (que, recordemos, es simulada). Además
  hay un costo técnico concreto: **el CSS.** Tailwind v4 en este proyecto **se compila con el plugin
  de Vite** (`@tailwindcss/vite`), y Django no usa Vite. Hay que resolver **cómo se compila el CSS en
  el mundo Django** — opciones: mantener un paso de build de Tailwind por CLI que emita un `.css`
  estático servido por Django, o integrar `django-tailwind`/`django-vite`. No es difícil, pero es
  trabajo que hay que planificar y no es "gratis".

### B — React SPA + Django API, token en el navegador
El React habla directo con Keycloak (Authorization Code + PKCE) y manda el token a la API de Django.

- **A favor:** aprovecha el prototipo; rápido de montar.
- **En contra:** el token vive en el navegador (**superficie de XSS**), riesgoso en un dominio
  financiero; hay que agregar router y guardas de ruta, que hoy no existen; dos tecnologías y dos
  despliegues; **tensión con el criterio FRA**, porque parte de la lógica de presentación se va de
  Django hacia React.

### C — React SPA + Django como BFF (Backend-For-Frontend)
Django hace el intercambio OIDC y expone una sesión por cookie HttpOnly. El React nunca ve un token.

- **A favor:** más seguro; patrón recomendado para dominios financieros.
- **En contra:** la opción con más piezas (React + Django + capa BFF + sesión); dos despliegues;
  misma tensión con FRA que B.

### Comparación

| | Tecnologías | Token en el navegador | Router/guardas nuevos | Despliegues | Keycloak (parte de auth) | Encaje con FRA (Django) |
|---|---|---|---|---|---|---|
| **A** Django plantillas | 1 (Django) | No (cookie) | No aplica | 1 | Trivial (`mozilla-django-oidc`) | Alto |
| **B** React SPA + API | 2 | **Sí (XSS)** | Sí | 2 | Medio (PKCE + refresh en browser) | Bajo |
| **C** React SPA + BFF | 2 | No (Django guarda el token) | Sí | 2 | Medio-alto (BFF + sesión) | Medio |

---

## 5. Recomendación del análisis: **A > C > B**

Esta es una recomendación para discutir en la reunión, **no una decisión.** El criterio final es del
equipo, con consulta a la profesora.

**Por qué A primero.** Tres razones, en orden de peso para *esta* materia:

1. **Django es obligatorio y FRA evalúa aplicarlo.** A es la única opción donde toda la lógica de
   presentación vive en Django. B y C sacan una parte importante hacia React, lo que juega en contra
   del criterio que la cátedra va a medir.
2. **El costo de "descartar React" es menor de lo que suena.** Lo reutilizable del prototipo es el
   markup y Tailwind, y eso se porta a plantillas. La lógica de React que se pierde es simulada
   (login falso, ABM en memoria) y se rehace igual en cualquier opción.
3. **Para autenticación y roles, A es la más limpia.** Sesión por cookie, token nunca en el
   navegador, y el control de roles queda del lado del servidor por defecto — que es donde la ERS
   exige que esté (RN05, validación de rol en el servidor).

**Por qué C va segunda y no primera.** Técnicamente C es el mejor patrón para dominios financieros,
por eso está sobre la mesa. Pero su ventaja principal —que el token no viva en el navegador— **A
también la da**, con muchas menos piezas. C solo le gana a A si aparece una razón fuerte para
mantener React como SPA (interactividad de cliente rica que una plantilla server-rendered no logre
bien). **Hoy la ERS no pide ese nivel de interactividad.** Si eso cambia, C es el camino de
crecimiento natural.

**Por qué B queda última.** Es la única que mete el token en el navegador (XSS) justo en un dominio
financiero, obliga a agregar router y guardas que no existen, suma una segunda tecnología y un
segundo despliegue, **y** es la que peor encaja con FRA. Paga el costo de complejidad de separar
React sin obtener el beneficio de seguridad de C.

**El contrapeso honesto:** la cátedra premia la **simplicidad** y el backend **hay que hacerlo
igual** (clientes, transacciones, arqueo de caja, facturación con SIFEN). Ambos hechos refuerzan A.
El único argumento serio a favor de C/B es "no tirar el trabajo de React" — pero ese trabajo es, en
la práctica, markup portable + lógica simulada.

---

## 6. Impacto en la configuración de Keycloak (no bloquea)

**Corrección respecto de lo que se había dicho antes:** la decisión A/B/C **no bloquea** la
configuración del realm. Se **crean los dos clients** desde el arranque y el resto de la
configuración es **idéntico en las tres opciones**:

- `global-exchange-web` — confidential (lo usan A y C).
- `global-exchange-spa` — public + PKCE S256 (lo usa B).
- Realm `GlobalExchange`, roles, mapper *User Client Role* con "Add to userinfo", claim plano
  `roles`: **igual en las tres.** Keycloak es la fuente de verdad en todos los casos.

Es decir: el trabajo de identidad puede avanzar en paralelo mientras se decide la arquitectura. Lo
que sí depende de la decisión es **qué client termina usando la aplicación**, no cómo se arma el
realm.

---

## 7. Trabajo que es idéntico en A, B y C (se puede adelantar)

Sea cual sea la opción, estas cosas valen igual y no dependen de la decisión:

- Los **formularios propios de usuario/contraseña se caen** (RN05): ese formulario lo dibuja
  Keycloak. `LoginPage.tsx` y `RegisterPage.tsx`, tal como están, no sobreviven en ninguna opción.
- Hay que **unificar los nombres de roles a los de la ERS**: `admin → administrador`,
  `analista → analista_cambiario`, y agregar `cliente_general` (cliente eventual de ventanilla).
- El **control de roles se valida en el servidor**, no en el navegador.

> Estos tres puntos tocan el frontend del compañero (`DashboardLayout.tsx`, `types.ts`), así que se
> **coordinan con él**; no se ejecutan sin su pedido.

---

## 8. Qué llevar a la reunión

1. Confirmar con la profesora que **A** (Django con plantillas) es el camino, dado que es lo que la
   guía exige y lo que FRA evalúa.
2. **Corregir RNF03 en la ERS** para que diga Django y no ".NET/React".
3. Si el equipo quiere conservar React, entender que eso implica **C** (no B) y estar listos para
   justificar ante la cátedra por qué se agrega esa complejidad frente al criterio de simplicidad.
4. Definir, si gana A, **cómo se compila Tailwind v4 fuera de Vite** (CLI de Tailwind con salida
   estática, o `django-tailwind`/`django-vite`).

---

*Documento de análisis del Equipo 04. La decisión final es del equipo con consulta a la profesora.*
