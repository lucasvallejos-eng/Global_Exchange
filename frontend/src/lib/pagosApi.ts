// Pagos con tarjeta vía Stripe (modo test).
//
// El número y el CVV de la tarjeta se escriben en un campo de Stripe
// (CardElement) y van directo a Stripe: nunca pasan por nuestro backend. El
// backend solo recibe ids (pm_..., seti_..., pi_...) y le consulta a Stripe.
import { loadStripe, type Stripe } from "@stripe/stripe-js";
import { get, post } from "./api";
import type { Operacion } from "./operacionesApi";

type ConfiguracionPagos = { habilitado: boolean; publishableKey: string };

// La clave publicable la da el backend (vive en backend/.env.stripe), así el
// frontend no necesita su propio .env para Stripe. Se carga una sola vez.
let stripePromesa: Promise<Stripe | null> | null = null;

export function obtenerStripe(): Promise<Stripe | null> {
  if (!stripePromesa) {
    stripePromesa = get<ConfiguracionPagos>("/api/pagos/configuracion/")
      .then((config) => (config.habilitado ? loadStripe(config.publishableKey) : null))
      .catch(() => null);
  }
  return stripePromesa;
}

// --- Alta de tarjetas ---------------------------------------------------------

export const prepararTarjeta = () => post<{ clientSecret: string }>("/api/medios-pago/tarjetas/preparar/", {});

export const registrarTarjeta = (datos: { setupIntentId: string; tipo: string; alias: string }) =>
  post<unknown>("/api/medios-pago/tarjetas/", datos);

// --- 3D Secure ----------------------------------------------------------------

/**
 * Si el banco pidió 3D Secure, Stripe muestra su ventana de verificación.
 * Devuelve el error de Stripe como Error para que cada pantalla lo muestre.
 */
export async function completarVerificacion(clientSecret: string): Promise<void> {
  const stripe = await obtenerStripe();
  if (!stripe) throw new Error("Los pagos con tarjeta no están disponibles.");
  const { error } = await stripe.handleNextAction({ clientSecret });
  if (error) throw new Error(error.message ?? "No se pudo verificar el pago con el banco.");
}

/**
 * Para las operaciones normales: si el cobro quedó esperando 3D Secure, lo
 * completa y le pide al backend que confirme con Stripe que quedó pagado.
 */
export async function completarPagoOperacion(operacion: Operacion): Promise<Operacion> {
  if (!operacion.pagoPendiente) return operacion;
  await completarVerificacion(operacion.pagoPendiente.clientSecret);
  return post<Operacion>(`/api/operaciones/${operacion.id}/verificar-pago/`, {});
}

// --- Caja -----------------------------------------------------------------------

export type TarjetaCliente = { id: number; nombre: string; titular: string; vencimiento: string };

export const tarjetasDelCliente = (clienteId: string | number) =>
  get<TarjetaCliente[]>(`/api/caja/clientes/${clienteId}/tarjetas/`);
