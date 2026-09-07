// Segmentos de cliente y su porcentaje de comisión. Fuente de verdad: la app
// `comisiones` del backend.
import { del, get, patch, post } from "./api";

export type Segmento = {
  id: number;
  nombre: string;
  porcentajeComision: number;
  descripcion: string;
  activo: boolean;
  cantidadClientes: number | null;
};

export type SegmentoEntrada = {
  nombre?: string;
  porcentajeComision?: number;
  descripcion?: string;
  activo?: boolean;
};

export const listarSegmentos = () => get<Segmento[]>("/api/segmentos/");
export const crearSegmento = (s: SegmentoEntrada) => post<Segmento>("/api/segmentos/", s);
export const actualizarSegmento = (id: number, s: SegmentoEntrada) =>
  patch<Segmento>(`/api/segmentos/${id}/`, s);
export const borrarSegmento = (id: number) => del<void>(`/api/segmentos/${id}/`);
