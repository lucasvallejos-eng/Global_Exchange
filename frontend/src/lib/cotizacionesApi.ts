// Cotizaciones: las vigentes y el histórico. Fuente de verdad: la app
// `cotizaciones` del backend.
import { del, get, patch, post } from "./api";

export type Cotizacion = {
  id: number;
  monedaId: number;
  codigo: string;
  nombre: string;
  simbolo: string;
  precioCompra: number;
  precioVenta: number;
  activa: boolean;
  fecha: string;
};

export type CotizacionEntrada = {
  monedaId?: number;
  precioCompra?: number;
  precioVenta?: number;
  activa?: boolean;
};

/** Solo las cotizaciones vigentes de las monedas activas. */
export const listarVigentes = () => get<Cotizacion[]>("/api/cotizaciones/?activas=1");

/** Histórico completo; con `codigo` trae el de una sola moneda. */
export const listarHistorial = (codigo?: string) =>
  get<Cotizacion[]>(codigo ? `/api/cotizaciones/?moneda=${encodeURIComponent(codigo)}` : "/api/cotizaciones/");

export const crearCotizacion = (c: CotizacionEntrada) => post<Cotizacion>("/api/cotizaciones/", c);
export const actualizarCotizacion = (id: number, c: CotizacionEntrada) =>
  patch<Cotizacion>(`/api/cotizaciones/${id}/`, c);
export const borrarCotizacion = (id: number) => del<void>(`/api/cotizaciones/${id}/`);
