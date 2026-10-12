// Cliente de la API de monedas. Habla con el backend Django (app `monedas`),
// que es la fuente de verdad: la maqueta ya no guarda monedas en memoria.

import { BACKEND, headersConCsrf, unwrap } from "./api";

export type Moneda = {
  id: number;
  codigo: string;
  nombre: string;
  simbolo: string;
  activo: boolean;
  // Moneda local (guaraní): sin cotización, no se compra ni se vende.
  esLocal: boolean;
  precioCompra: number | null;
  precioVenta: number | null;
};

export type MonedaEntrada = {
  codigo?: string;
  nombre?: string;
  simbolo?: string;
  activo?: boolean;
  esLocal?: boolean;
  precioCompra?: number | null;
  precioVenta?: number | null;
};

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
