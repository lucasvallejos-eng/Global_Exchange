import { useEffect, useMemo, useState } from "react";
import { ClientType, getAppliedRate } from "../lib/clientRates";
import { useTasas } from "../lib/useTasas";
import { cotizarOperacion, type Presupuesto } from "../lib/operacionesApi";

type SimulacionType = "compra" | "venta";

const formatPyg = (value: number) =>
  new Intl.NumberFormat("es-PY", {
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(value);

const formatDivisa = (value: number) =>
  new Intl.NumberFormat("es-PY", { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(value);

// La tasa aplicada puede traer decimales (el descuento del segmento).
const formatTasa = (value: number) =>
  new Intl.NumberFormat("es-PY", { maximumFractionDigits: 4 }).format(value);

// Con un cliente activo, la simulación es completa: la calcula el backend con
// la misma cuenta que una operación real (tasa, descuento del segmento,
// comisión y total), sin guardar nada. Sin cliente no hay segmento del que
// sacar la comisión, y se muestra solo la conversión con la cotización vigente.
export default function SimulacionModule({ userType, descuentoCompra, clienteId = null }: {
  userType: ClientType;
  descuentoCompra: number;
  clienteId?: string | null;
}) {
  const [tab, setTab] = useState<SimulacionType>("compra");
  const [amount, setAmount] = useState("1000");
  const [currency, setCurrency] = useState<string>("");
  const [showSimulation, setShowSimulation] = useState(false);

  // Cotizaciones reales de la base; antes eran una tabla fija en el codigo.
  const { tasas, codigos, cargando, error } = useTasas();

  useEffect(() => {
    // Cuando llegan las monedas se elige la primera, si no hay ninguna puesta.
    if (!currency && codigos.length > 0) setCurrency(codigos[0]);
  }, [codigos, currency]);

  const tasa = tasas[currency];

  const baseRate = useMemo(() => {
    if (!tasa) return 0;
    return tab === "compra" ? tasa.venta : tasa.compra;
  }, [tasa, tab]);

  const rate = useMemo(() => {
    if (!tasa) return 0;
    const mode = tab === "compra" ? "venta" : "compra";
    return getAppliedRate(tasa, mode, descuentoCompra);
  }, [tasa, tab, descuentoCompra]);

  const numericAmount = Number.parseFloat(amount) || 0;

  const [presupuesto, setPresupuesto] = useState<Presupuesto | null>(null);
  const [errorSimulacion, setErrorSimulacion] = useState("");

  useEffect(() => {
    setPresupuesto(null);
    setErrorSimulacion("");
    if (!showSimulation || !clienteId || !currency || numericAmount <= 0) return;
    let vigente = true;
    // Espera a que se termine de escribir el monto antes de consultar.
    const espera = setTimeout(() => {
      cotizarOperacion({
        clienteId,
        tipo: tab === "compra" ? "COMPRA" : "VENTA",
        moneda: currency,
        monto: numericAmount,
      })
        .then((respuesta) => vigente && setPresupuesto(respuesta))
        .catch((e: Error) => vigente && setErrorSimulacion(e.message));
    }, 300);
    return () => {
      vigente = false;
      clearTimeout(espera);
    };
  }, [showSimulation, clienteId, currency, numericAmount, tab]);
  const total = numericAmount * rate;

  const typeLabel = tab === "compra" ? "Compra" : "Venta";
  const resultLabel = tab === "compra" ? "Total a pagar" : "Total a recibir";
  const variationLabel = `${(descuentoCompra * 100).toFixed(2)}% de descuento en compras`;

  return (
    <div className="space-y-6">
      {error && (
        <div className="rounded-2xl border border-[#f5c6c2] bg-[#fdeceb] px-4 py-3 text-sm text-[#c0392b]">
          {error}
        </div>
      )}
      <div className="rounded-3xl border border-[#dbe3ee] bg-white p-6 shadow-sm">
        <div className="mb-5 flex items-center justify-between gap-4">
          <div>
            <p className="text-sm font-medium text-[#64748b]">Simulación</p>
            <h2 className="text-2xl font-bold tracking-tight text-[#0f172a]">Cotización en tiempo real</h2>
          </div>
          <span className="rounded-full bg-[#edf4ff] px-3 py-1.5 text-xs font-semibold text-[#1a7eff]">
            {userType} • {variationLabel}
          </span>
        </div>

        <div className="inline-flex rounded-xl border border-[#dbe3ee] bg-[#f8fafc] p-1">
          <button
            onClick={() => setTab("compra")}
            className={`rounded-lg px-4 py-2 text-sm font-semibold transition ${
              tab === "compra" ? "bg-[#1a7eff] text-white" : "text-[#475569]"
            }`}
          >
            Simulación de Compra
          </button>
          <button
            onClick={() => setTab("venta")}
            className={`rounded-lg px-4 py-2 text-sm font-semibold transition ${
              tab === "venta" ? "bg-[#1a7eff] text-white" : "text-[#475569]"
            }`}
          >
            Simulación de Venta
          </button>
        </div>

        <div className="mt-6 grid gap-5 md:grid-cols-[1.5fr_0.8fr]">
          <label className="block">
            <span className="mb-2 block text-sm font-medium text-[#374151]">
              {tab === "compra" ? "Cantidad a comprar" : "Cantidad a vender"}
            </span>
            <div className="flex overflow-hidden rounded-xl border border-[#dbe3ee] bg-[#f8fafc] focus-within:border-[#1a7eff]">
              <input
                type="number"
                min="0"
                step="0.01"
                value={amount}
                onChange={(event) => setAmount(event.target.value)}
                className="w-full bg-transparent px-4 py-3 text-lg font-semibold text-[#0f172a] outline-none"
                placeholder={tab === "compra" ? "1000" : "1000"}
              />
              <select
                value={currency}
                onChange={(event) => setCurrency(event.target.value)}
                disabled={cargando || codigos.length === 0}
                className="border-l border-[#dbe3ee] bg-white px-3 py-3 text-sm font-medium text-[#374151] outline-none"
              >
                {cargando && <option>Cargando...</option>}
                {!cargando && codigos.length === 0 && <option>Sin monedas</option>}
                {codigos.map((c) => (
                  <option key={c} value={c}>
                    {c}
                  </option>
                ))}
              </select>
            </div>
          </label>

          <div className="rounded-2xl border border-[#dbe3ee] bg-[#f8fafc] p-4">
            <p className="text-xs uppercase tracking-[0.18em] text-[#64748b]">Cotización actual</p>
            <p className="mt-2 text-lg font-bold text-[#0f172a]">
              1 {currency} = {formatPyg(rate)} PYG
            </p>
          </div>
        </div>

        <div className="mt-6 flex gap-3">
          <button
            onClick={() => setShowSimulation(true)}
            className="rounded-xl bg-[#1a7eff] px-6 py-3 text-sm font-semibold text-white shadow-sm transition hover:bg-[#146be7]"
          >
            Mostrar Simulación
          </button>
        </div>
      </div>

      {showSimulation && (
        <div className="rounded-3xl border border-[#dbe3ee] bg-white p-6 shadow-sm">
          <div className="rounded-2xl border border-[#e2e8f0] bg-[#f8fafc] p-5">
            <div className="flex items-center justify-between gap-4">
              <div>
                <p className="text-sm font-medium text-[#64748b]">Tipo de operación</p>
                <h3 className="text-2xl font-bold text-[#0f172a]">{typeLabel}</h3>
              </div>
              <span className="rounded-full bg-[#ebf3ff] px-3 py-1 text-xs font-semibold text-[#1a7eff]">
                {currency}
              </span>
            </div>

            {errorSimulacion && (
              <div className="mt-5 rounded-xl border border-[#f5c6c2] bg-[#fdeceb] px-4 py-3 text-sm text-[#c0392b]">
                {errorSimulacion}
              </div>
            )}

            {presupuesto ? (
              <>
                <dl className="mt-5 divide-y divide-[#e2e8f0] rounded-xl border border-[#e2e8f0] bg-white text-sm">
                  {[
                    ["A nombre de", presupuesto.cliente.nombre],
                    ["Monto simulado", `${formatDivisa(presupuesto.montoDivisa)} ${presupuesto.moneda}`],
                    [
                      `Tasa base (${tab === "compra" ? "precio de venta" : "precio de compra"})`,
                      `${formatPyg(presupuesto.tasaBase)} PYG`,
                    ],
                    ...(presupuesto.descuentoCompra > 0
                      ? [["Descuento del segmento", `${(presupuesto.descuentoCompra * 100).toFixed(2)} %`]]
                      : []),
                    ["Tasa aplicada", `1 ${presupuesto.moneda} = ${formatTasa(presupuesto.tasaAplicada)} PYG`],
                    ["Subtotal", `${formatPyg(presupuesto.montoGuaranies)} PYG`],
                    [
                      `Comisión (${presupuesto.porcentajeComision} %)`,
                      `${tab === "compra" ? "+" : "−"} ${formatPyg(presupuesto.comision)} PYG`,
                    ],
                  ].map(([etiqueta, valor]) => (
                    <div key={etiqueta} className="flex items-center justify-between gap-4 px-4 py-3">
                      <dt className="text-[#64748b]">{etiqueta}</dt>
                      <dd className="font-semibold tabular-nums text-[#0f172a]">{valor}</dd>
                    </div>
                  ))}
                </dl>
                <div className="mt-4 flex items-center justify-between gap-4 rounded-xl border border-[#cfe2ff] bg-[#edf4ff] px-4 py-4">
                  <p className="text-sm font-semibold text-[#0f172a]">{resultLabel}</p>
                  <p className="text-2xl font-bold tabular-nums text-[#0f172a]">
                    {formatPyg(presupuesto.totalGuaranies)} PYG
                  </p>
                </div>
              </>
            ) : (
              !errorSimulacion && (
                <div className="mt-5 grid gap-4 md:grid-cols-4">
                  <div className="rounded-xl bg-white p-4 border border-[#e2e8f0]">
                    <p className="text-xs uppercase tracking-[0.12em] text-[#64748b]">Monto simulado</p>
                    <p className="mt-2 text-lg font-bold text-[#0f172a]">
                      {formatPyg(numericAmount)} {currency}
                    </p>
                  </div>
                  <div className="rounded-xl bg-white p-4 border border-[#e2e8f0]">
                    <p className="text-xs uppercase tracking-[0.12em] text-[#64748b]">Tasa base</p>
                    <p className="mt-2 text-lg font-bold text-[#0f172a]">
                      1 {currency} = {formatPyg(baseRate)} PYG
                    </p>
                  </div>
                  <div className="rounded-xl bg-white p-4 border border-[#e2e8f0]">
                    <p className="text-xs uppercase tracking-[0.12em] text-[#64748b]">Tasa final</p>
                    <p className="mt-2 text-lg font-bold text-[#0f172a]">
                      1 {currency} = {formatPyg(rate)} PYG
                    </p>
                  </div>
                  <div className="rounded-xl bg-white p-4 border border-[#e2e8f0]">
                    <p className="text-xs uppercase tracking-[0.12em] text-[#64748b]">{resultLabel}</p>
                    <p className="mt-2 text-lg font-bold text-[#0a7cff]">{formatPyg(total)} PYG</p>
                  </div>
                </div>
              )
            )}

            <div className="mt-5 rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-[#7c5b00]">
              {presupuesto
                ? "Es el mismo cálculo de una operación real, sin registrar nada. La tasa puede cambiar hasta el momento de operar."
                : clienteId
                  ? "Esta simulación es puramente orientativa. Las tasas de cambio pueden variar al momento de realizar la operación real."
                  : "Sin un cliente asociado no se puede calcular la comisión: se muestra solo la conversión con la cotización vigente."}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
