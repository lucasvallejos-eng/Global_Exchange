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

/**
 * Cálculo de una operación que todavía no existe (lo que muestra el modal de
 * confirmación). Mismas claves que `Operacion`, sin id ni estado.
 */
export type Presupuesto = Pick<
  Operacion,
  | "tipo" | "cliente" | "moneda" | "montoDivisa" | "tasaBase" | "descuentoCompra"
  | "tasaAplicada" | "montoGuaranies" | "porcentajeComision" | "comision"
  | "totalGuaranies" | "medioPago"
>;

/** Calcula la operación con la cotización vigente, sin guardar nada. */
export function cotizarOperacion(datos: NuevaOperacion): Promise<Presupuesto> {
  return post<Presupuesto>("/api/operaciones/cotizar/", datos);
}

/**
 * Registra la operación confirmada en el modal. `tasaBase` es la del
 * presupuesto que se mostró: si la cotización cambió desde entonces, el
 * backend la registra "CANCELADA" con `canceladaPorCotizacion` en vez de
 * cobrarla. No es un error: hay que mirar el estado de la respuesta.
 */
export function confirmarOperacion(datos: NuevaOperacion & { tasaBase: number }): Promise<Operacion> {
  return post<Operacion>("/api/operaciones/confirmar/", datos);
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

/** Filtros del historial. Los vacíos no filtran. Fechas en formato AAAA-MM-DD. */
export interface FiltrosHistorial {
  estado?: EstadoOperacion | "";
  tipo?: TipoOperacion | "";
  moneda?: string;
  desde?: string;
  hasta?: string;
}

/**
 * Historial de operaciones (solo consulta). El backend ya devuelve solo las
 * que el usuario puede ver: las de sus clientes, o todas si es administrador,
 * analista o cajero.
 */
export function listarOperaciones(filtros: FiltrosHistorial = {}): Promise<{ operaciones: Operacion[]; total: number }> {
  const parametros = new URLSearchParams();
  for (const [clave, valor] of Object.entries(filtros)) {
    if (valor) parametros.set(clave, valor);
  }
  const consulta = parametros.toString();
  return get(`/api/operaciones/${consulta ? `?${consulta}` : ""}`);
}
