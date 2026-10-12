import { get, post } from "./api";

export type CajaDenominacion = {
  id: number;
  valor: number;
  codigo: string;
};

export type CajaMoneda = {
  id: number;
  codigo: string;
  nombre: string;
  simbolo: string;
  tieneDenominaciones: boolean;
  denominaciones: CajaDenominacion[];
};

export type AperturaEntrada = {
  denominacion_id: number;
  cantidad_unidades: number;
};

export function listarDenominacionesPorMoneda(): Promise<CajaMoneda[]> {
  return get<CajaMoneda[]>("/api/cajero/denominaciones-por-moneda/");
}

export function crearApertura(denominaciones: AperturaEntrada[]) {
  return post("/api/caja/apertura/", { denominaciones });
}

export function crearCierre(totales_reales: Record<string, number>) {
  return post("/api/caja/cierre/", { totales_reales });
}

/** Los 3 estados de la máquina de estados de caja del cajero. */
export type EstadoCaja = "ESPERANDO_ARQUEO" | "EN_SERVICIO" | "CAJA_CERRADA";

export type EstadoDiario = {
  aperturada: boolean;
  activa: boolean;
  horaApertura: string | null;
  /** Estado explícito de la máquina de estados. Derivado del backend; persiste entre sesiones. */
  estadoCaja: EstadoCaja;
};

export type ResumenCierre = {
  aperturaId: number;
  resumen: Array<{
    moneda: string;
    saldoInicial: number;
    compras: number;
    ventas: number;
    saldoTeorico: number;
  }>;
};

export function obtenerEstadoDiario(): Promise<EstadoDiario> {
  return get<EstadoDiario>("/api/caja/estado-diario/");
}

export function obtenerResumenCierre(): Promise<ResumenCierre> {
  return get<ResumenCierre>("/api/caja/resumen-cierre/");
}

export function registrarCompraCaja(datos: {
  cliente_id: string;
  moneda: string;
  monto_divisa: number;
  medio_pago_id?: number;
}) {
  return post("/api/caja/compras/", datos);
}

export function registrarVentaCaja(datos: {
  cliente_id: string;
  moneda: string;
  monto_divisa: number;
  tipo_pago: string;
}) {
  return post("/api/caja/ventas/", datos);
}
