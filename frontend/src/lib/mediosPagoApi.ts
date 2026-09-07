// Medios de pago del usuario. Fuente de verdad: la app `medios_pago` del
// backend, que además decide qué ve cada rol (un cliente solo los suyos).
import { del, get, patch, post } from "./api";

export type MedioPago = {
  id: number;
  tipo: string;
  tipoTexto: string;
  alias: string;
  numero: string;
  banco: string;
  activo: boolean;
  usuario: string;
};

export type TipoMedioPago = { valor: string; texto: string };

export type RespuestaMedios = {
  tipos: TipoMedioPago[];
  medios: MedioPago[];
};

export type MedioPagoEntrada = {
  tipo?: string;
  alias?: string;
  numero?: string;
  banco?: string;
  activo?: boolean;
};

export const listarMediosPago = () => get<RespuestaMedios>("/api/medios-pago/");
export const crearMedioPago = (m: MedioPagoEntrada) => post<MedioPago>("/api/medios-pago/", m);
export const actualizarMedioPago = (id: number, m: MedioPagoEntrada) =>
  patch<MedioPago>(`/api/medios-pago/${id}/`, m);
export const borrarMedioPago = (id: number) => del<void>(`/api/medios-pago/${id}/`);
