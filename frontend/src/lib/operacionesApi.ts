// Operaciones de compra y venta contra el backend Django.
// El cálculo (tasa aplicada, comisión, total) lo hace siempre el backend: la
// maqueta solo muestra una vista previa mientras se escribe el monto.
import { get, post } from "./api";

export type TipoOperacion = "COMPRA" | "VENTA";
export type EstadoOperacion = "PENDIENTE" | "PAGADA" | "CANCELADA" | "ANULADA";

export interface Operacion {
  id: number;
  tipo: TipoOperacion;
  tipoTexto: string;
  estado: EstadoOperacion;
  estadoTexto: string;
  cliente: { id: number; nombre: string };
  moneda: string;
  montoDivisa: number;
  tasaBase: number;
  descuentoCompra: number;
  tasaAplicada: number;
  montoGuaranies: number;
  porcentajeComision: number;
  comision: number;
  totalGuaranies: number;
  medioPago: string | null;
  motivoCancelacion: string | null;
  // true si se canceló sola porque la cotización cambió antes del pago.
  canceladaPorCotizacion: boolean;
  tasaBaseNueva: number | null;
  fechaCreacion: string;
  fechaPago: string | null;
  fechaCancelacion: string | null;
}

export interface NuevaOperacion {
  clienteId: string;
  tipo: TipoOperacion;
  moneda: string;
  monto: number;
  medioPagoId?: number | null;
}

/** Crea la operación pendiente de pago y devuelve el cálculo del backend. */
export function crearOperacion(datos: NuevaOperacion): Promise<Operacion> {
  return post<Operacion>("/api/operaciones/", datos);
}

/**
 * Paga la operación. Si la cotización cambió desde que se creó, el backend
 * la cancela y la devuelve con estado "CANCELADA": no es un error, hay que
 * mirar el estado de la respuesta.
 */
export function pagarOperacion(id: number): Promise<Operacion> {
  return post<Operacion>(`/api/operaciones/${id}/pagar/`, {});
}

export function cancelarOperacion(id: number): Promise<Operacion> {
  return post<Operacion>(`/api/operaciones/${id}/cancelar/`, {});
}

export function obtenerOperacion(id: number): Promise<Operacion> {
  return get<Operacion>(`/api/operaciones/${id}/`);
}
