// Utilidades comunes para hablar con el backend Django.
// Las tenían repetidas clientesApi.ts y monedasApi.ts; acá viven una sola vez.

// Dirección del backend Django. En desarrollo es localhost:8000; para
// producción se define VITE_BACKEND_URL al construir (ver frontend/Dockerfile),
// porque el navegador de quien abre la página no puede llegar a "localhost"
// del servidor.
export const BACKEND = import.meta.env.VITE_BACKEND_URL ?? "http://localhost:8000";

export function leerCookie(nombre: string): string {
  const match = document.cookie.match(new RegExp(`(?:^|; )${nombre}=([^;]*)`));
  return match ? decodeURIComponent(match[1]) : "";
}

/** Cabeceras para las mutaciones: Django exige el token CSRF en POST/PATCH/DELETE. */
export function headersConCsrf(): HeadersInit {
  return {
    "Content-Type": "application/json",
    "X-CSRFToken": leerCookie("csrftoken"),
  };
}

/**
 * Devuelve el JSON de la respuesta, o lanza un error con el mensaje del
 * backend. Las vistas mandan {"error": "..."} cuando falla una validación
 * (por ejemplo RN10), y ese texto es más útil que un código pelado.
 */
export async function unwrap<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const detalle = await res.json().catch(() => null);
    throw new Error(detalle?.error ?? `No se pudo completar la operación (${res.status}).`);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

export function get<T>(ruta: string): Promise<T> {
  return fetch(`${BACKEND}${ruta}`, { credentials: "include" }).then(unwrap<T>);
}

export function post<T>(ruta: string, cuerpo: unknown): Promise<T> {
  return fetch(`${BACKEND}${ruta}`, {
    method: "POST",
    credentials: "include",
    headers: headersConCsrf(),
    body: JSON.stringify(cuerpo),
  }).then(unwrap<T>);
}

export function patch<T>(ruta: string, cuerpo: unknown): Promise<T> {
  return fetch(`${BACKEND}${ruta}`, {
    method: "PATCH",
    credentials: "include",
    headers: headersConCsrf(),
    body: JSON.stringify(cuerpo),
  }).then(unwrap<T>);
}

export function del<T>(ruta: string): Promise<T> {
  return fetch(`${BACKEND}${ruta}`, {
    method: "DELETE",
    credentials: "include",
    headers: headersConCsrf(),
  }).then(unwrap<T>);
}
