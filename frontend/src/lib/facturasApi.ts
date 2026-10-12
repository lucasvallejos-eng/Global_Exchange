// Facturas electrónicas de las operaciones pagadas.
// Las emite Factura Segura (SIFEN) desde el backend: la maqueta solo las
// lista, consulta su estado y las descarga.
import { BACKEND, get, post } from "./api";

export type EstadoFactura =
  | "SIMULADA" | "ERROR" | "SIN_CONFIRMAR" | "ENVIADA"
  | "APROBADA" | "RECHAZADA" | "CANCELADA";

export interface Factura {
  id: number;
  // "001-003-0000382", o "Sin número" si no se emitió.
  numero: string;
  estado: EstadoFactura;
  estadoTexto: string;
  // Lo que respondió Factura Segura o el SIFEN (motivo de un rechazo, etc.).
  detalle: string | null;
  fecha: string;
  monto: number;
  // A nombre de quién salió: el cliente de la operación, no el usuario.
  cliente: string;
  documento: string | null;
  // De dónde salió la operación facturada: la web o la caja (ventanilla).
  origen: "Web" | "Caja";
  operacionId: number;
  operacion: string;
  cdc: string | null;
  // Existe en Factura Segura: tiene KuDE (PDF) y XML para descargar.
  descargable: boolean;
  // Falló (o es simulada y la emisión está prendida): se puede volver a mandar.
  sePuedeEmitir: boolean;
}

export interface ListaFacturas {
  facturas: Factura[];
  total: number;
  // "simulada": las facturas no se emiten de verdad (no gastan números).
  emision: "real" | "simulada";
}

export const listarFacturas = () => get<ListaFacturas>("/api/facturas/");

/** Consulta en Factura Segura cómo quedó la factura en el SIFEN. */
export const actualizarFactura = (id: number) =>
  post<Factura>(`/api/facturas/${id}/actualizar/`, {});

/** Vuelve a emitir una factura que falló. */
export const reintentarFactura = (id: number) =>
  post<Factura>(`/api/facturas/${id}/reintentar/`, {});

/** Dirección de descarga del KuDE (PDF) o del XML firmado. */
export const urlDescarga = (id: number, formato: "kude" | "xml") =>
  `${BACKEND}/api/facturas/${id}/${formato}/`;
