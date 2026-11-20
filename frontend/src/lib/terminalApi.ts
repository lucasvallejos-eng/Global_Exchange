// Terminal de autoservicio: el cliente reserva una operación y la completa con
// efectivo en la terminal ingresando el código. El depósito de billetes se hace
// en la pantalla de la terminal (Django, /terminal/), no acá.
import { get, post } from "./api";
import type { Operacion, TipoOperacion } from "./operacionesApi";

export type EstadoReserva = "ESPERANDO" | "COMPLETADA" | "CANCELADA";

export interface Reserva {
  codigo: string;
  estado: EstadoReserva;
  estadoTexto: string;
  detalle: string | null;
  terminal: string | null;
  entrega: "EFECTIVO" | "CUENTA";
  // Lo que el cliente pone en la terminal y lo que recibe.
  deposita: { moneda: string; monto: number };
  recibe: { moneda: string; monto: number };
  fecha: string;
  operacion: Operacion;
  urlTerminal: string;
}

export interface TerminalDisponible {
  id: number;
  nombre: string;
  ubicacion: string;
}

export const listarReservas = () => get<{ reservas: Reserva[] }>("/api/terminal/reservas/");

export const reservarEnTerminal = (datos: { clienteId: number; tipo: TipoOperacion; moneda: string; monto: number }) =>
  post<Reserva>("/api/terminal/reservas/", datos);

export const listarTerminales = () => get<{ terminales: TerminalDisponible[] }>("/api/terminal/terminales/");
