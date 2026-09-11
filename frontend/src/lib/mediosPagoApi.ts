// Medios de pago del usuario. Fuente de verdad: la app `medios_pago` del
// backend, que además decide qué ve cada rol (un cliente solo los suyos).
import { del, get, patch, post } from "./api";

export type MedioPago = {
  id: number;
  tipo: string;
  tipoTexto: string;
  alias: string;
  activo: boolean;
  usuario: string;
  detalle: Record<string, string>;
};

export type TipoMedioPago = { valor: string; texto: string; activo: boolean };

export type RespuestaMedios = {
  tipos: TipoMedioPago[];
  medios: MedioPago[];
};

export type MedioPagoEntrada = {
  tipo: string;
  alias: string;
  activo?: boolean;
  [key: string]: string | boolean | undefined;
};

export function etiquetaMedioPago(medio: MedioPago): string {
  const numero = medio.detalle.numeroTarjeta;
  const identificador = numero ?? medio.detalle.numeroCuentaOrigen ?? medio.detalle.identificadorCuenta;
  const sufijo = identificador ? ` ${identificador.slice(-4)}` : "";
  return `${medio.alias}${sufijo ? ` ****${sufijo}` : ""}`;
}

export const listarMediosPago = () => get<RespuestaMedios>("/api/medios-pago/");
export const crearMedioPago = (m: MedioPagoEntrada) => post<MedioPago>("/api/medios-pago/", m);
export const actualizarMedioPago = (id: number, m: MedioPagoEntrada) =>
  patch<MedioPago>(`/api/medios-pago/${id}/`, m);
export const borrarMedioPago = (id: number) => del<void>(`/api/medios-pago/${id}/`);
export const actualizarTipoMedioPago = (clave: string, activo: boolean) =>
  patch<TipoMedioPago>(`/api/medios-pago/tipos/${clave}/`, { activo } as MedioPagoEntrada);
