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
  // Moneda local (guaraní): se cuenta en apertura y cierre, no se opera.
  esLocal: boolean;
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
    // Lo que entró y salió del cajón. Para la moneda local, las entradas son
    // las ventas de divisa cobradas en efectivo y las salidas, las compras.
    compras: number;
    ventas: number;
    cantidadCompras: number;
    cantidadVentas: number;
    saldoTeorico: number;
    // Compras cobradas con tarjeta: la divisa llegó por Stripe, no al cajón.
    comprasConTarjeta: { cantidad: number; monto: number };
    // El saldo teórico en guaraníes, al precio de compra vigente. null si no hay cotización.
    valorEnLocal: number | null;
  }>;
  monedaLocal: string | null;
  totalEnLocal: number;
};

export type OperacionCajaHistorial = {
  id: number;
  tipo: "COMPRA" | "VENTA";
  fechaHora: string;
  cliente: { id: number; nombre: string };
  moneda: string;
  montoDivisa: number;
  cotizacion: number;
  totalGuaranies: number;
  formaPago: string | null;
  medioPago: string | null;
  pagoConTarjeta: boolean;
};

export type CajaHistorial = {
  id: number;
  cajero: string | null;
  fechaHoraApertura: string;
  estado: "activa" | "cerrada";
  fechaHoraCierre: string | null;
  saldoInicial: Record<string, number>;
  diferenciaCierre: Record<string, number> | null;
  operaciones: OperacionCajaHistorial[];
};

export function listarHistorialCaja(filtros: { desde?: string; hasta?: string } = {}) {
  const params = new URLSearchParams(Object.entries(filtros).filter(([, v]) => v) as [string, string][]);
  const consulta = params.toString();
  return get<{ aperturas: CajaHistorial[] }>(`/api/caja/historial/${consulta ? `?${consulta}` : ""}`);
}

export function obtenerEstadoDiario(): Promise<EstadoDiario> {
  return get<EstadoDiario>("/api/caja/estado-diario/");
}

export function obtenerResumenCierre(): Promise<ResumenCierre> {
  return get<ResumenCierre>("/api/caja/resumen-cierre/");
}

export type OperacionCajaEntrada = {
  cliente_id: string;
  moneda: string;
  monto_divisa: number;
  // Venta sin tarjeta: el tipo de medio de pago (se registra como texto).
  tipo_pago?: string;
  // Tarjeta de Stripe del cliente: se cobra en el momento.
  medio_pago_id?: number;
  // Reintento después del 3D Secure: el pago que ya se verificó.
  payment_intent_id?: string;
};

// 201: la operación registrada. 202: el banco pidió 3D Secure; la operación
// todavía no se registró (ver registrarOperacionCaja en OperacionCajaForm).
export type RespuestaCaja = {
  id?: number;
  pagoConTarjeta?: boolean;
  pagoPendiente?: { clientSecret: string; paymentIntentId: string };
};

export function registrarCompraCaja(datos: OperacionCajaEntrada) {
  return post<RespuestaCaja>("/api/caja/compras/", datos);
}

export function registrarVentaCaja(datos: OperacionCajaEntrada) {
  return post<RespuestaCaja>("/api/caja/ventas/", datos);
}
