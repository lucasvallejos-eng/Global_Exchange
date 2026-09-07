import { useEffect, useMemo, useState } from "react";
import { ClientType, getAppliedRate } from "../lib/clientRates";
import { useTasas } from "../lib/useTasas";

type SimulacionType = "compra" | "venta";

const formatPyg = (value: number) =>
  new Intl.NumberFormat("es-PY", {
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(value);

export default function SimulacionModule({ userType }: { userType: ClientType }) {
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
    return getAppliedRate(tasa, mode, userType);
  }, [tasa, tab, userType]);

  const numericAmount = Number.parseFloat(amount) || 0;
  const total = numericAmount * rate;

  const typeLabel = tab === "compra" ? "Compra" : "Venta";
  const resultLabel = tab === "compra" ? "Total a pagar" : "Total a recibir";
  const variationLabel = userType === "Minorista" ? "sin variación" : userType === "Mayorista" ? "-2% en ventas / +2% en compras" : "-5% en ventas / +5% en compras";

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

            <div className="mt-5 rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-[#7c5b00]">
              Esta simulación es puramente orientativa. Las tasas de cambio pueden variar al momento de realizar la operación real.
            </div>

            
          </div>
        </div>
      )}
    </div>
  );
}
