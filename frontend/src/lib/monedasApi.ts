// Cliente de la API de monedas. Habla con el backend Django (app `monedas`),
// que es la fuente de verdad: la maqueta ya no guarda monedas en memoria.

import { BACKEND } from "./api";

export type Moneda = {
  id: number;
  codigo: string;
  nombre: string;
  simbolo: string;
  activo: boolean;
  precioCompra: number | null;
  precioVenta: number | null;
};

export type MonedaEntrada = {
  codigo?: string;
  nombre?: string;
  simbolo?: string;
  activo?: boolean;
  precioCompra?: number | null;
  precioVenta?: number | null;
};

function leerCookie(nombre: string): string {
  const match = document.cookie.match(new RegExp(`(?:^|; )${nombre}=([^;]*)`));
  return match ? decodeURIComponent(match[1]) : "";
}

function headersConCsrf(): HeadersInit {
  return {
    "Content-Type": "application/json",
    "X-CSRFToken": leerCookie("csrftoken"),
  };
}

async function unwrap<T>(res: Response): Promise<T> {
  if (!res.ok) {
    // El backend manda {"error": "..."} cuando la validación falla (por
    // ejemplo RN10). Se muestra ese texto en vez de un código pelado.
    const detalle = await res.json().catch(() => null);
    throw new Error(detalle?.error ?? `No se pudo completar la operación (${res.status}).`);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

export async function listarMonedas(): Promise<Moneda[]> {
  const res = await fetch(`${BACKEND}/api/monedas/`, { credentials: "include" });
  return unwrap(res);
}

export async function crearMoneda(moneda: MonedaEntrada): Promise<Moneda> {
  const res = await fetch(`${BACKEND}/api/monedas/`, {
    method: "POST",
    credentials: "include",
    headers: headersConCsrf(),
    body: JSON.stringify(moneda),
  });
  return unwrap(res);
}

export async function actualizarMoneda(id: number, moneda: MonedaEntrada): Promise<Moneda> {
  const res = await fetch(`${BACKEND}/api/monedas/${id}/`, {
    method: "PATCH",
    credentials: "include",
    headers: headersConCsrf(),
    body: JSON.stringify(moneda),
  });
  return unwrap(res);
}

export async function borrarMoneda(id: number): Promise<void> {
  const res = await fetch(`${BACKEND}/api/monedas/${id}/`, {
    method: "DELETE",
    credentials: "include",
    headers: headersConCsrf(),
  });
  return unwrap(res);
}
