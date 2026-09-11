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
/**
 * Precio que se le aplica al cliente sobre una cotización de la base.
 *
 * Antes esta función leía una tabla de tasas escrita a mano; ahora recibe la
 * cotización real para que la pantalla muestre lo que hay en la base de datos.
 */
export function getAppliedRate(tasa: Tasa, mode: "compra" | "venta", descuentoCompra: number) {
  if (mode === "compra") {
    return tasa.compra;
  }

  return tasa.venta * (1 - descuentoCompra);
}

export function getClientTypeBadge(userType: ClientType, descuentoCompra: number) {
  return `Nivel Actual: ${userType} (${(descuentoCompra * 100).toFixed(2)}% de descuento en compras)`;
}
