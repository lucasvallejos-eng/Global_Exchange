// Reportes de transacciones y ganancias (administrador y analista cambiario).
// Todo se calcula en el backend sobre las operaciones pagadas: la ganancia de
// una operación es su comisión más el margen de cambio (ver reportes/servicio.py).
// Entran las operaciones de la web y las de la caja.
import { BACKEND, get } from "./api";
import type { TipoOperacion } from "./operacionesApi";

// WEB = operación de la web; CAJA = de la ventanilla.
export type OrigenReporte = "WEB" | "CAJA";

export interface FiltrosReporte {
  desde?: string; // AAAA-MM-DD, por fecha de pago
  hasta?: string;
  moneda?: string;
  tipo?: TipoOperacion | "";
  origen?: OrigenReporte | "";
}

export interface Totales {
  operaciones: number;
  // Monto operado en guaraníes, antes de la comisión.
  volumen: number;
  comisiones: number;
  // Puede ser negativo: la casa vendió por debajo del precio medio.
  margen: number;
  ganancia: number;
}

export interface FilaReporte {
  id: number;
  origen: OrigenReporte;
  // "Web #5", "Caja, venta #2": única entre las dos fuentes.
  referencia: string;
  fecha: string;
  cliente: string;
  tipo: TipoOperacion;
  tipoTexto: string;
  moneda: string;
  montoDivisa: number;
  tasaAplicada: number;
  montoGuaranies: number;
  comision: number;
  margen: number;
  ganancia: number;
  medioPago: string | null;
}

export interface ReporteTransacciones {
  operaciones: FilaReporte[];
  totales: Totales;
}

export interface Ganancias {
  totales: Totales;
  porTipo: Record<TipoOperacion, Totales>;
  // De mayor a menor ganancia.
  porMoneda: (Totales & { moneda: string; montoDivisa: number })[];
  // Un punto por día, en orden; los días sin operaciones vienen en cero.
  porDia: (Totales & { fecha: string })[];
}

function consulta(filtros: FiltrosReporte): string {
  const parametros = new URLSearchParams();
  Object.entries(filtros).forEach(([clave, valor]) => {
    if (valor) parametros.set(clave, valor);
  });
  const texto = parametros.toString();
  return texto ? `?${texto}` : "";
}

export const reporteTransacciones = (filtros: FiltrosReporte = {}) =>
  get<ReporteTransacciones>(`/api/reportes/transacciones/${consulta(filtros)}`);

export const reporteGanancias = (filtros: FiltrosReporte = {}) =>
  get<Ganancias>(`/api/reportes/ganancias/${consulta(filtros)}`);

/** Dirección para descargar el reporte de transacciones en CSV. */
export const urlExportarTransacciones = (filtros: FiltrosReporte = {}) =>
  `${BACKEND}/api/reportes/transacciones/exportar/${consulta(filtros)}`;
