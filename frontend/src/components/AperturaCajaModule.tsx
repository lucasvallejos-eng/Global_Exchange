import { useMemo, useState } from "react";

const CURRENCIES = ["PYG", "USD", "EUR", "BRL"] as const;
type Currency = (typeof CURRENCIES)[number];

type Denomination = {
  id: string;
  moneda: Currency;
  denominacion: string;
  valor: number;
  cantidad: number;
};

const DENOMINACIONES: Record<Currency, { label: string; value: number }[]> = {
  PYG: [
    { label: "10.000", value: 10000 },
    { label: "20.000", value: 20000 },
    { label: "50.000", value: 50000 },
    { label: "100.000", value: 100000 },
  ],
  USD: [
    { label: "1 USD", value: 1 },
    { label: "5 USD", value: 5 },
    { label: "10 USD", value: 10 },
    { label: "20 USD", value: 20 },
    { label: "50 USD", value: 50 },
    { label: "100 USD", value: 100 },
  ],
  EUR: [
    { label: "5 EUR", value: 5 },
    { label: "10 EUR", value: 10 },
    { label: "20 EUR", value: 20 },
    { label: "50 EUR", value: 50 },
    { label: "100 EUR", value: 100 },
  ],
  BRL: [
    { label: "10 BRL", value: 10 },
    { label: "20 BRL", value: 20 },
    { label: "50 BRL", value: 50 },
    { label: "100 BRL", value: 100 },
    { label: "200 BRL", value: 200 },
  ],
};

const RATE_TO_PYG: Record<Currency, number> = {
  PYG: 1,
  USD: 7600,
  EUR: 8250,
  BRL: 1150,
};

const formatNumber = (value: number) =>
  new Intl.NumberFormat("es-PY", {
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(value);

export default function AperturaCajaModule() {
  const [currency, setCurrency] = useState<Currency>("PYG");
  const [denominations, setDenominations] = useState<Record<Currency, string>>({
    PYG: "10.000",
    USD: "1 USD",
    EUR: "5 EUR",
    BRL: "10 BRL",
  });
  const [quantity, setQuantity] = useState("10");
  const [entries, setEntries] = useState<Denomination[]>([
    { id: "init-1", moneda: "PYG", denominacion: "10.000", valor: 10000, cantidad: 5 },
    { id: "init-2", moneda: "USD", denominacion: "20 USD", valor: 20, cantidad: 4 },
  ]);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [modalOpen, setModalOpen] = useState(false);
  const [toast, setToast] = useState<string | null>(null);

  const options = DENOMINACIONES[currency];

  const selectedDenomination = useMemo(
    () => options.find((option) => option.label === denominations[currency]) ?? options[0],
    [currency, denominations, options],
  );

  const totalsByCurrency = useMemo(() => {
    return CURRENCIES.reduce((acc, moneda) => {
      const total = entries
        .filter((entry) => entry.moneda === moneda)
        .reduce((sum, entry) => sum + entry.valor * entry.cantidad, 0);
      acc[moneda] = total;
      return acc;
    }, {} as Record<Currency, number>);
  }, [entries]);

  const totalGeneral = useMemo(
    () => CURRENCIES.reduce((sum, moneda) => sum + totalsByCurrency[moneda] * RATE_TO_PYG[moneda], 0),
    [totalsByCurrency],
  );

  const handleInsert = () => {
    const numericQty = Number.parseInt(quantity, 10);
    if (!selectedDenomination || !Number.isFinite(numericQty) || numericQty <= 0) {
      setToast("Ingrese una cantidad válida.");
      setTimeout(() => setToast(null), 2000);
      return;
    }

    const nextEntry: Denomination = {
      id: editingId ?? `${currency}-${Date.now()}`,
      moneda: currency,
      denominacion: selectedDenomination.label,
      valor: selectedDenomination.value,
      cantidad: numericQty,
    };

    if (editingId) {
      setEntries((current) => current.map((entry) => (entry.id === editingId ? nextEntry : entry)));
      setToast("Desglose actualizado correctamente.");
      setEditingId(null);
    } else {
      setEntries((current) => [...current, nextEntry]);
      setToast("Desglose insertado correctamente.");
    }

    setQuantity("10");
    setTimeout(() => setToast(null), 2200);
  };

  const handleEdit = (entry: Denomination) => {
    setEditingId(entry.id);
    setCurrency(entry.moneda);
    setDenominations((current) => ({ ...current, [entry.moneda]: entry.denominacion }));
    setQuantity(String(entry.cantidad));
  };

  const handleDelete = (id: string) => {
    setEntries((current) => current.filter((entry) => entry.id !== id));
    setToast("Desglose eliminado.");
    setTimeout(() => setToast(null), 2000);
  };

  const onConfirmOpen = () => setModalOpen(true);
  const onConfirmClose = () => setModalOpen(false);

  const handleFinalize = () => {
    setModalOpen(false);
    setToast("Apertura de caja confirmada.");
    setTimeout(() => setToast(null), 2200);
  };

  return (
    <div className="space-y-6">
      <div className="rounded-3xl border border-[#dbe3ee] bg-white p-6 shadow-sm">
        <div className="mb-6 flex items-center justify-between gap-4">
          <div>
            <p className="text-sm font-medium text-[#64748b]">Apertura de Caja</p>
            <h2 className="text-2xl font-bold tracking-tight text-[#0f172a]">Arqueo por denominación</h2>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={handleInsert}
              className="rounded-xl bg-[#0f172a] px-4 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-[#1e293b]"
            >
              Agregar
            </button>
            <button
              onClick={onConfirmOpen}
              className="rounded-xl bg-[#1a7eff] px-4 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-[#176ae6]"
            >
              Finalizar Apertura
            </button>
          </div>
        </div>

        <div className="grid gap-4 lg:grid-cols-4">
          <label className="block">
            <span className="mb-2 block text-sm font-medium text-[#374151]">Moneda</span>
            <select
              value={currency}
              onChange={(e) => {
                const nextCurrency = e.target.value as Currency;
                setCurrency(nextCurrency);
                setDenominations((current) => ({ ...current, [nextCurrency]: DENOMINACIONES[nextCurrency][0].label }));
              }}
              className="w-full rounded-xl border border-[#dbe3ee] bg-[#f8fafc] px-3 py-2.5 text-sm text-[#1f2937] outline-none focus:border-[#1a7eff]"
            >
              {CURRENCIES.map((option) => (
                <option key={option} value={option}>{option}</option>
              ))}
            </select>
          </label>

          <label className="block">
            <span className="mb-2 block text-sm font-medium text-[#374151]">Denominación</span>
            <select
              value={denominations[currency]}
              onChange={(e) => setDenominations((current) => ({ ...current, [currency]: e.target.value }))}
              className="w-full rounded-xl border border-[#dbe3ee] bg-[#f8fafc] px-3 py-2.5 text-sm text-[#1f2937] outline-none focus:border-[#1a7eff]"
            >
              {options.map((option) => (
                <option key={option.label} value={option.label}>{option.label}</option>
              ))}
            </select>
          </label>

          <label className="block">
            <span className="mb-2 block text-sm font-medium text-[#374151]">Cantidad</span>
            <input
              type="number"
              min="1"
              step="1"
              value={quantity}
              onChange={(e) => setQuantity(e.target.value)}
              className="w-full rounded-xl border border-[#dbe3ee] bg-[#f8fafc] px-3 py-2.5 text-sm text-[#1f2937] outline-none focus:border-[#1a7eff]"
            />
          </label>

          <div className="flex items-end">
            <button
              onClick={handleInsert}
              className="w-full rounded-xl bg-[#0f172a] px-4 py-2.5 text-sm font-semibold text-white hover:bg-[#1e293b]"
            >
              {editingId ? "Guardar" : "Insertar"}
            </button>
          </div>
        </div>

        <div className="mt-6 overflow-hidden rounded-2xl border border-[#e2e8f0]">
          <table className="min-w-full border-collapse bg-white text-left text-sm text-[#1f2937]">
            <thead className="bg-[#f8fafc] text-[#475569]">
              <tr>
                <th className="px-4 py-3 font-semibold">Moneda</th>
                <th className="px-4 py-3 font-semibold">Denominación</th>
                <th className="px-4 py-3 font-semibold">Cantidad (Unidades)</th>
                <th className="px-4 py-3 font-semibold text-right">Subtotal</th>
                <th className="px-4 py-3 font-semibold text-center">Acciones</th>
              </tr>
            </thead>
            <tbody>
              {entries.map((entry) => (
                <tr key={entry.id} className="border-t border-[#edf2f7] bg-white hover:bg-[#f8fafc]">
                  <td className="px-4 py-3 font-medium text-[#0f172a]">{entry.moneda}</td>
                  <td className="px-4 py-3">{entry.denominacion}</td>
                  <td className="px-4 py-3">{entry.cantidad}</td>
                  <td className="px-4 py-3 text-right font-semibold text-[#1a7eff]">
                    {formatNumber(entry.valor * entry.cantidad)}
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex justify-center gap-2">
                      <button
                        onClick={() => handleEdit(entry)}
                        className="rounded-lg border border-[#dbe3ee] bg-white px-2.5 py-1.5 text-xs font-semibold text-[#374151] hover:bg-[#f8fafc]"
                      >
                        Modificar
                      </button>
                      <button
                        onClick={() => handleDelete(entry.id)}
                        className="rounded-lg border border-red-200 bg-red-50 px-2.5 py-1.5 text-xs font-semibold text-red-600 hover:bg-red-100"
                      >
                        Eliminar
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="mt-6 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          {CURRENCIES.map((moneda) => (
            <div key={moneda} className="rounded-2xl border border-[#dbe3ee] bg-[#f8fafc] p-4">
              <p className="text-xs uppercase tracking-[0.15em] text-[#64748b]">{moneda}</p>
              <p className="mt-2 text-xl font-bold text-[#0f172a]">{formatNumber(totalsByCurrency[moneda])}</p>
              <p className="mt-1 text-xs text-[#64748b]">Equiv. {formatNumber(totalsByCurrency[moneda] * RATE_TO_PYG[moneda])} PYG</p>
            </div>
          ))}
        </div>

        <div className="mt-6 rounded-2xl border border-[#dbe3ee] bg-[#f0f7ff] p-4">
          <p className="text-sm text-[#64748b]">Total acumulado de apertura</p>
          <p className="mt-1 text-2xl font-bold text-[#1a7eff]">{formatNumber(totalGeneral)} PYG</p>
        </div>
      </div>

      {modalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 p-4">
          <div className="w-full max-w-md rounded-2xl bg-white p-6 shadow-2xl">
            <h3 className="text-xl font-bold text-[#0f172a]">¿Desea finalizar la apertura de caja?</h3>
            <p className="mt-3 text-sm text-[#64748b]">Se habilitará la operativa del cajero y quedará registrado el arqueo inicial.</p>

            <div className="mt-6 flex justify-end gap-3">
              <button
                onClick={onConfirmClose}
                className="rounded-xl border border-[#dbe3ee] bg-white px-4 py-2 text-sm font-semibold text-[#475569] hover:bg-[#f8fafc]"
              >
                Cancelar
              </button>
              <button
                onClick={handleFinalize}
                className="rounded-xl bg-[#1a7eff] px-4 py-2 text-sm font-semibold text-white hover:bg-[#176ae6]"
              >
                Confirmar
              </button>
            </div>
          </div>
        </div>
      )}

      {toast && (
        <div className="fixed bottom-6 right-6 z-[60] rounded-xl bg-[#0f172a] px-4 py-3 text-sm font-medium text-white shadow-lg">
          {toast}
        </div>
      )}
    </div>
  );
}
