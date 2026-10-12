import { del, get, post, put } from "./api";

export type Denominacion = {
  id: number;
  monedaId: number;
  moneda_id?: number;
  monedaCodigo: string;
  monedaNombre: string;
  simbolo: string;
  valor: number;
  creadoEn?: string | null;
  actualizadoEn?: string | null;
};

export type DenominacionEntrada = {
  moneda_id: number;
  valor: number;
};

export async function listarDenominaciones(monedaId?: number): Promise<Denominacion[]> {
  const ruta = monedaId ? `/api/denominaciones/?moneda_id=${monedaId}` : "/api/denominaciones/";
  return get<Denominacion[]>(ruta);
}

export async function crearDenominacion(datos: DenominacionEntrada): Promise<Denominacion> {
  return post<Denominacion>("/api/denominaciones/", datos);
}

export async function actualizarDenominacion(
  id: number,
  datos: { valor: number; moneda_id?: number }
): Promise<Denominacion> {
  return put<Denominacion>(`/api/denominaciones/${id}/`, datos);
}

export async function borrarDenominacion(id: number): Promise<void> {
  return del<void>(`/api/denominaciones/${id}/`);
}
