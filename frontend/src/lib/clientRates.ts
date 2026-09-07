export type ClientType = "Minorista" | "Mayorista" | "VIP";

export const CLIENT_TYPE_OPTIONS: ClientType[] = ["Minorista", "Mayorista", "VIP"];

/** Cotización de una moneda, tal como llega del backend. */
export type Tasa = {
  compra: number;
  venta: number;
};

/**
 * Ajuste que se le aplica a la cotización base según el segmento del cliente.
 * Es configuración comercial de la maqueta; el cálculo real de la operación
 * corresponde al Sprint 3.
 */
export const CLIENT_MARGINS: Record<ClientType, { descVenta: number; benefCompra: number }> = {
  Minorista: { descVenta: 0, benefCompra: 0 },
  Mayorista: { descVenta: 0.02, benefCompra: 0.02 },
  VIP: { descVenta: 0.05, benefCompra: 0.05 },
};

/**
 * Precio que se le aplica al cliente sobre una cotización de la base.
 *
 * Antes esta función leía una tabla de tasas escrita a mano; ahora recibe la
 * cotización real para que la pantalla muestre lo que hay en la base de datos.
 */
export function getAppliedRate(tasa: Tasa, mode: "compra" | "venta", userType: ClientType) {
  const margin = CLIENT_MARGINS[userType];

  if (mode === "compra") {
    return tasa.compra * (1 + margin.benefCompra);
  }

  return tasa.venta * (1 - margin.descVenta);
}

export function getClientTypeBadge(userType: ClientType) {
  if (userType === "Minorista") return "Nivel Actual: Minorista (sin variación)";
  if (userType === "Mayorista") return "Nivel Actual: Mayorista (-2% en ventas / +2% en compras)";
  return "Nivel Actual: VIP (-5% en ventas / +5% en compras)";
}
