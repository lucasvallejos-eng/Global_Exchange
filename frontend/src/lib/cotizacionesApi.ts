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
  ultimaActualizacion: string | null;
};

export type CotizacionEntrada = {
  monedaId?: number;
  precioCompra?: number;
  precioVenta?: number;
  activa?: boolean;
};

export type PuntoEvolucion = {
  date: string;
  label: string;
  dia: string;
  value: number;
  compra: number;
  esProyeccion: boolean;
};

export type EvolucionTasasRespuesta = {
  moneda: string;
  nombre: string;
  simbolo: string;
  rango: string;
  fechaActual: string;
  fechaActualFormateada: string;
  valorActual: number;
  valorCompraActual: number;
  historico: PuntoEvolucion[];
  proyeccion: PuntoEvolucion[];
  rangoFechas: {
    inicio: string;
    fin: string;
    proyeccionHasta: string;
  };
  resumen: {
    minimo: number;
    maximo: number;
    proyeccionFin: number;
  };
};

/** Solo las cotizaciones vigentes de las monedas activas. */
export const listarVigentes = () => get<Cotizacion[]>("/api/cotizaciones/?activas=1");

/** Histórico completo; con `codigo` trae el de una sola moneda. */
export const listarHistorial = (codigo?: string, orden: "asc" | "desc" = "asc") => {
  const params = new URLSearchParams();
  if (codigo) params.set("moneda", codigo);
  if (orden) params.set("orden", orden);
  const q = params.toString();
  return get<Cotizacion[]>(`/api/cotizaciones/${q ? `?${q}` : ""}`);
};

/** Evolución histórica diaria y proyección semanal conectada al backend. */
export const obtenerEvolucionTasas = (codigo?: string, rango: string = "1M") => {
  const params = new URLSearchParams();
  if (codigo) params.set("moneda", codigo);
  if (rango) params.set("rango", rango);
  return get<EvolucionTasasRespuesta>(`/api/cotizaciones/evolucion/?${params.toString()}`);
};

export const crearCotizacion = (c: CotizacionEntrada) => post<Cotizacion>("/api/cotizaciones/", c);
export const actualizarCotizacion = (id: number, c: CotizacionEntrada) =>
  patch<Cotizacion>(`/api/cotizaciones/${id}/`, c);
export const borrarCotizacion = (id: number) => del<void>(`/api/cotizaciones/${id}/`);
