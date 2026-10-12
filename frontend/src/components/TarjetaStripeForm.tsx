import { useState } from "react";
import { CardElement, Elements, useElements, useStripe } from "@stripe/react-stripe-js";
import { obtenerStripe, prepararTarjeta, registrarTarjeta } from "../lib/pagosApi";

type Props = {
  tipo: string;
  alias: string;
  onGuardada: () => void;
  onCancelar: () => void;
};

/**
 * Alta de una tarjeta con Stripe. El número, el vencimiento y el CVV se
 * escriben en el campo de Stripe (CardElement) y van directo a Stripe; a
 * nuestro backend solo llega el id del SetupIntent.
 *
 * Tarjetas de prueba (modo test): 4242 4242 4242 4242 (aprobada) o
 * 4000 0025 0000 3155 (pide 3D Secure). Vencimiento futuro, cualquier CVC.
 */
export default function TarjetaStripeForm(props: Props) {
  return (
    <Elements stripe={obtenerStripe()}>
      <Formulario {...props} />
    </Elements>
  );
}

function Formulario({ tipo, alias, onGuardada, onCancelar }: Props) {
  const stripe = useStripe();
  const elements = useElements();
  const [titular, setTitular] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [guardando, setGuardando] = useState(false);

  const guardar = async () => {
    const tarjeta = elements?.getElement(CardElement);
    if (!stripe || !tarjeta) return setError("Los pagos con tarjeta no están disponibles.");
    if (!alias.trim()) return setError("El alias es obligatorio.");
    setError(null);
    setGuardando(true);
    try {
      const { clientSecret } = await prepararTarjeta();
      const { setupIntent, error: errorStripe } = await stripe.confirmCardSetup(clientSecret, {
        payment_method: { card: tarjeta, billing_details: { name: titular || undefined } },
      });
      if (errorStripe || !setupIntent) throw new Error(errorStripe?.message ?? "No se pudo guardar la tarjeta.");
      await registrarTarjeta({ setupIntentId: setupIntent.id, tipo, alias });
      onGuardada();
    } catch (e) {
      setError(e instanceof Error ? e.message : "No se pudo guardar la tarjeta.");
    } finally {
      setGuardando(false);
    }
  };

  return (
    <>
      <input value={titular} onChange={(e) => setTitular(e.target.value)} placeholder="Nombre del titular" className="mt-3 w-full rounded-xl border px-3 py-2.5" />
      <div className="mt-3 rounded-xl border px-3 py-3">
        <CardElement options={{ hidePostalCode: true, style: { base: { fontSize: "15px", color: "#0f172a" } } }} />
      </div>
      <p className="mt-2 text-xs text-[#64748b]">
        Los datos de la tarjeta los guarda Stripe de forma segura; Global Exchange solo ve la marca y los últimos 4 dígitos.
      </p>
      {error && <p className="mt-3 rounded-xl border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>}
      <div className="mt-5 flex justify-end gap-3">
        <button onClick={onCancelar} disabled={guardando} className="rounded-xl border px-4 py-2">Cancelar</button>
        <button onClick={() => void guardar()} disabled={guardando || !stripe} className="rounded-xl bg-[#1a7eff] px-4 py-2 font-semibold text-white disabled:bg-slate-300">
          {guardando ? "Verificando..." : "Guardar tarjeta"}
        </button>
      </div>
    </>
  );
}
