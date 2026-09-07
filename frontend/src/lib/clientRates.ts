export type ClientType = "Minorista" | "Mayorista" | "VIP";

export const CLIENT_TYPE_OPTIONS: ClientType[] = ["Minorista", "Mayorista", "VIP"];

export const BASE_RATES = {
  USD: { compra: 7500, venta: 7600 },
  EUR: { compra: 8100, venta: 8250 },
  BRL: { compra: 1140, venta: 1150 },
} as const;

export const CLIENT_MARGINS: Record<ClientType, { descVenta: number; benefCompra: number }> = {
  Minorista: { descVenta: 0, benefCompra: 0 },
  Mayorista: { descVenta: 0.02, benefCompra: 0.02 },
  VIP: { descVenta: 0.05, benefCompra: 0.05 },
};

export function getAppliedRate(currency: keyof typeof BASE_RATES, mode: "compra" | "venta", userType: ClientType) {
  const base = BASE_RATES[currency];
  const margin = CLIENT_MARGINS[userType];

  if (mode === "compra") {
    return base.compra * (1 + margin.benefCompra);
  }

  return base.venta * (1 - margin.descVenta);
}

export function getClientTypeBadge(userType: ClientType) {
  if (userType === "Minorista") return "Nivel Actual: Minorista (sin variación)";
  if (userType === "Mayorista") return "Nivel Actual: Mayorista (-2% en ventas / +2% en compras)";
  return "Nivel Actual: VIP (-5% en ventas / +5% en compras)";
}
