// Notificaciones de la campanita. Las crea el backend cuando se paga o falla
// una compra/venta y cuando cambia una cotización; acá solo se leen.
import { get, post, put } from "./api";

export type TipoNotificacion = "OPERACION_EXITOSA" | "OPERACION_FALLIDA" | "COTIZACION";

export type Notificacion = {
  id: number;
  tipo: TipoNotificacion;
  titulo: string;
  mensaje: string;
  datos: Record<string, unknown>;
  leida: boolean;
  fecha: string;
};

export type RespuestaNotificaciones = { noLeidas: number; notificaciones: Notificacion[] };

export const listarNotificaciones = () => get<RespuestaNotificaciones>("/api/notificaciones/");

/** Marca como leídas las indicadas, o todas si no se pasan ids. */
export const marcarLeidas = (ids?: number[]) =>
  post<{ noLeidas: number }>("/api/notificaciones/marcar-leidas/", ids ? { ids } : {});

// --- Preferencias (suscripciones) -------------------------------------------

export type PreferenciasNotificaciones = {
  compras: boolean;
  ventas: boolean;
  cotizaciones: boolean;
  // Divisas de las que avisar los cambios de cotización. Vacío = todas.
  monedas: string[];
  monedasDisponibles: { codigo: string; nombre: string }[];
};

export const obtenerPreferencias = () => get<PreferenciasNotificaciones>("/api/notificaciones/preferencias/");

export const guardarPreferencias = (datos: Omit<PreferenciasNotificaciones, "monedasDisponibles">) =>
  put<PreferenciasNotificaciones>("/api/notificaciones/preferencias/", datos);
