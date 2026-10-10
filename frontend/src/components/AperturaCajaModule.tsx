import { useEffect, useMemo, useState } from "react";

import {
  CajaMoneda,
  crearApertura,
  listarDenominacionesPorMoneda,
  obtenerEstadoDiario,
} from "../lib/cajaApi";

type Entry = {
  id: string;
  moneda: string;
  monedaNombre: string;
  denominacionId: number;
  denominacion: string;
  valor: number;
  cantidad: number;
};

const formatNumber = (value: number) =>
  new Intl.NumberFormat("es-PY", {
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
  }).format(value);

export default function AperturaCajaModule({ onApertura }: { onApertura?: () => void }) {
  const [monedas, setMonedas] = useState<CajaMoneda[]>([]);
  const [currencyId, setCurrencyId] = useState("");
  const [denominationId, setDenominationId] = useState("");
  const [quantity, setQuantity] = useState("1");
  const [entries, setEntries] = useState<Entry[]>([]);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [modalOpen, setModalOpen] = useState(false);
  const [toast, setToast] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [estado, setEstado] = useState<{ aperturada: boolean; horaApertura: string | null } | null>(null);

  useEffect(() => {
    obtenerEstadoDiario().then(setEstado).catch(() => setEstado({ aperturada: false, horaApertura: null }));
    listarDenominacionesPorMoneda()
      .then((data) => {
        setMonedas(data);
        const first = data.find((moneda) => moneda.tieneDenominaciones);
        if (first) {
          setCurrencyId(String(first.id));
          setDenominationId(String(first.denominaciones[0].id));
        }
      })
      .catch((error) => setToast(error instanceof Error ? error.message : "No se pudieron cargar las monedas."))
      .finally(() => setLoading(false));
  }, []);

  const currency = monedas.find((moneda) => String(moneda.id) === currencyId);
  const options = currency?.denominaciones ?? [];
  const selectedDenomination = options.find((option) => String(option.id) === denominationId);

  const totalsByCurrency = useMemo(
    () =>
      entries.reduce<Record<string, number>>((totals, entry) => {
        totals[entry.moneda] = (totals[entry.moneda] ?? 0) + entry.valor * entry.cantidad;
        return totals;
      }, {}),
    [entries],
  );

  const showToast = (message: string) => {
    setToast(message);
    window.setTimeout(() => setToast(null), 2200);
  };

  const handleCurrencyChange = (value: string) => {
    const next = monedas.find((moneda) => String(moneda.id) === value);
    setCurrencyId(value);
    setDenominationId(next?.denominaciones[0] ? String(next.denominaciones[0].id) : "");
  };

  const handleInsert = () => {
    const numericQty = Number.parseInt(quantity, 10);
    if (!selectedDenomination || !currency || !Number.isInteger(numericQty) || numericQty <= 0) {
      showToast("Seleccione una denominación e ingrese una cantidad entera positiva.");
      return;
    }
    const nextEntry: Entry = {
      id: editingId ?? `${selectedDenomination.id}-${Date.now()}`,
      moneda: currency.codigo,
      monedaNombre: currency.nombre,
      denominacionId: selectedDenomination.id,
      denominacion: `${formatNumber(selectedDenomination.valor)} ${currency.codigo}`,
      valor: selectedDenomination.valor,
      cantidad: numericQty,
    };
    setEntries((current) =>
      editingId ? current.map((entry) => (entry.id === editingId ? nextEntry : entry)) : [...current, nextEntry],
    );
    setEditingId(null);
    setQuantity("1");
    showToast(editingId ? "Desglose actualizado correctamente." : "Desglose insertado correctamente.");
  };

  const handleFinalize = async () => {
    try {
      await crearApertura(
        entries.map((entry) => ({
          denominacion_id: entry.denominacionId,
          cantidad_unidades: entry.cantidad,
        })),
      );
      setModalOpen(false);
      // Re-fetch desde el backend para obtener la hora real registrada en BD
      obtenerEstadoDiario().then(setEstado).catch(() => setEstado({ aperturada: true, horaApertura: null }));
      onApertura?.();
      showToast("Apertura de caja confirmada.");
    } catch (error) {
      showToast(error instanceof Error ? error.message : "No se pudo registrar la apertura.");
    }
  };

  return (
    <div className="space-y-6">
      {estado?.aperturada ? (
        <div className="rounded-3xl border border-[#dbe3ee] bg-white p-10 text-center shadow-sm">
          <p className="text-2xl font-bold text-[#0f172a]"># Arqueo ya realizado</p>
          <h2 className="mt-3 text-xl font-semibold text-[#1a7eff]">Realizado a las {estado.horaApertura} hs</h2>
        </div>
      ) : (
      <div className="rounded-3xl border border-[#dbe3ee] bg-white p-6 shadow-sm">
        <div className="mb-6 flex items-center justify-between gap-4">
          <div>
            <p className="text-sm font-medium text-[#64748b]">Apertura de Caja</p>
            <h2 className="text-2xl font-bold tracking-tight text-[#0f172a]">Arqueo por denominación</h2>
          </div>
          <div className="flex gap-3">
            <button onClick={handleInsert} disabled={loading || !selectedDenomination} className="rounded-xl bg-[#0f172a] px-4 py-2.5 text-sm font-semibold text-white disabled:opacity-50">
              Agregar
            </button>
            <button onClick={() => setModalOpen(true)} disabled={!entries.length} className="rounded-xl bg-[#1a7eff] px-4 py-2.5 text-sm font-semibold text-white disabled:opacity-50">
              Finalizar Apertura
            </button>
          </div>
        </div>

        <div className="grid gap-4 lg:grid-cols-4">
          <label className="block">
            <span className="mb-2 block text-sm font-medium text-[#374151]">Moneda</span>
            <select value={currencyId} onChange={(event) => handleCurrencyChange(event.target.value)} className="w-full rounded-xl border border-[#dbe3ee] bg-[#f8fafc] px-3 py-2.5 text-sm">
              <option value="">Seleccione una moneda</option>
              {monedas.map((option) => (
                <option key={option.id} value={option.id} disabled={!option.tieneDenominaciones}>
                  {option.nombre}{option.tieneDenominaciones ? ` (${option.codigo})` : " (Sin Denominaciones)"}
                </option>
              ))}
            </select>
          </label>
          <label className="block">
            <span className="mb-2 block text-sm font-medium text-[#374151]">Denominación</span>
            <select value={denominationId} onChange={(event) => setDenominationId(event.target.value)} disabled={!options.length} className="w-full rounded-xl border border-[#dbe3ee] bg-[#f8fafc] px-3 py-2.5 text-sm">
              <option value="">Seleccione una denominación</option>
              {options.map((option) => <option key={option.id} value={option.id}>{formatNumber(option.valor)} {currency?.codigo}</option>)}
            </select>
          </label>
          <label className="block">
            <span className="mb-2 block text-sm font-medium text-[#374151]">Cantidad</span>
            <input type="number" min="1" step="1" value={quantity} onChange={(event) => setQuantity(event.target.value)} className="w-full rounded-xl border border-[#dbe3ee] bg-[#f8fafc] px-3 py-2.5 text-sm" />
          </label>
          <div className="flex items-end">
            <button onClick={handleInsert} disabled={!selectedDenomination} className="w-full rounded-xl bg-[#0f172a] px-4 py-2.5 text-sm font-semibold text-white disabled:opacity-50">{editingId ? "Guardar" : "Insertar"}</button>
          </div>
        </div>

        <div className="mt-6 overflow-hidden rounded-2xl border border-[#e2e8f0]">
          <table className="min-w-full border-collapse bg-white text-left text-sm text-[#1f2937]">
            <thead className="bg-[#f8fafc] text-[#475569]"><tr><th className="px-4 py-3">Moneda</th><th className="px-4 py-3">Denominación</th><th className="px-4 py-3">Cantidad (Unidades)</th><th className="px-4 py-3 text-right">Subtotal</th><th className="px-4 py-3 text-center">Acciones</th></tr></thead>
            <tbody>
              {entries.map((entry) => <tr key={entry.id} className="border-t border-[#edf2f7]"><td className="px-4 py-3 font-medium">{entry.moneda}</td><td className="px-4 py-3">{entry.denominacion}</td><td className="px-4 py-3">{entry.cantidad}</td><td className="px-4 py-3 text-right font-semibold text-[#1a7eff]">{formatNumber(entry.valor * entry.cantidad)}</td><td className="px-4 py-3 text-center"><button onClick={() => { setEditingId(entry.id); setCurrencyId(String(monedas.find((m) => m.codigo === entry.moneda)?.id ?? "")); setDenominationId(String(entry.denominacionId)); setQuantity(String(entry.cantidad)); }} className="mr-2 rounded-lg border px-2.5 py-1.5 text-xs font-semibold">Modificar</button><button onClick={() => setEntries((current) => current.filter((item) => item.id !== entry.id))} className="rounded-lg border border-red-200 bg-red-50 px-2.5 py-1.5 text-xs font-semibold text-red-600">Eliminar</button></td></tr>)}
            </tbody>
          </table>
        </div>

        <div className="mt-6 overflow-hidden rounded-2xl border border-[#dbe3ee]">
          <table className="min-w-full text-left text-sm"><thead className="bg-[#f8fafc] text-[#475569]"><tr><th className="px-4 py-3">Moneda</th><th className="px-4 py-3 text-right">Total Acumulado</th></tr></thead><tbody>{Object.entries(totalsByCurrency).map(([code, total]) => <tr key={code} className="border-t border-[#edf2f7]"><td className="px-4 py-3 font-semibold">{code}</td><td className="px-4 py-3 text-right font-semibold text-[#1a7eff]">{formatNumber(total)}</td></tr>)}</tbody></table>
        </div>
      </div>
      )}

      {modalOpen && <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 p-4"><div className="w-full max-w-md rounded-2xl bg-white p-6 shadow-2xl"><h3 className="text-xl font-bold">¿Desea finalizar la apertura de caja?</h3><p className="mt-3 text-sm text-[#64748b]">Se registrará el arqueo inicial asociado a su usuario.</p><div className="mt-6 flex justify-end gap-3"><button onClick={() => setModalOpen(false)} className="rounded-xl border px-4 py-2 text-sm font-semibold">Cancelar</button><button onClick={handleFinalize} className="rounded-xl bg-[#1a7eff] px-4 py-2 text-sm font-semibold text-white">Confirmar</button></div></div></div>}
      {toast && <div className="fixed bottom-6 right-6 z-[60] rounded-xl bg-[#0f172a] px-4 py-3 text-sm text-white shadow-lg">{toast}</div>}
    </div>
  );
}
