export type PaymentMethodStatus = "Activo" | "Inactivo";

export interface PaymentMethodOption {
  id: string;
  medio: string;
  estado: PaymentMethodStatus;
}

export const DEFAULT_PAYMENT_METHODS: PaymentMethodOption[] = [
  { id: "transferencia", medio: "Transferencia Bancaria", estado: "Activo" },
  { id: "tc", medio: "TC (Tarjeta de Crédito / Débito)", estado: "Activo" },
  { id: "billetera", medio: "Billetera Digital", estado: "Inactivo" },
];

let PAYMENT_METHODS: PaymentMethodOption[] = [...DEFAULT_PAYMENT_METHODS];

export function getPaymentMethods(): PaymentMethodOption[] {
  return [...PAYMENT_METHODS];
}

export function setPaymentMethods(nextMethods: PaymentMethodOption[]) {
  PAYMENT_METHODS = [...nextMethods];
}

export function togglePaymentMethodStatus(id: string) {
  PAYMENT_METHODS = PAYMENT_METHODS.map((method) =>
    method.id === id
      ? { ...method, estado: method.estado === "Activo" ? "Inactivo" : "Activo" }
      : method,
  );
}

export function getActivePaymentMethods(): PaymentMethodOption[] {
  return PAYMENT_METHODS.filter((method) => method.estado === "Activo");
}
