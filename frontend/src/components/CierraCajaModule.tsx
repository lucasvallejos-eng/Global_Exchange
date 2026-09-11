import { useMemo, useState } from "react";

const CURRENCIES = ["USD", "BRL", "EUR", "PYG"] as const;
type Currency = (typeof CURRENCIES)[number];

type SummaryRow = {
  moneda: Currency;
  ventas: { cantidad: number; total: number };
  compras: { cantidad: number; total: number };
  saldoInicial: number;
};

const SUMMARY_DATA: SummaryRow[] = [
  { moneda: "USD", ventas: { cantidad: 12, total: 1500 }, compras: { cantidad: 8, total: 2500 }, saldoInicial: 12500 },
  { moneda: "BRL", ventas: { cantidad: 9, total: 5000 }, compras: { cantidad: 11, total: 6800 }, saldoInicial: 18000 },
  { moneda: "EUR", ventas: { cantidad: 5, total: 800 }, compras: { cantidad: 6, total: 950 }, saldoInicial: 7500 },
  { moneda: "PYG", ventas: { cantidad: 18, total: 2800000 }, compras: { cantidad: 14, total: 1700000 }, saldoInicial: 4200000 },
];

const CONVERSION_TO_PYG: Record<Currency, number> = {
  USD: 7600,
  BRL: 1150,
  EUR: 8250,
  PYG: 1,
};

const formatNumber = (value: number) =>
  new Intl.NumberFormat("es-PY", {
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(value);

export default function CierraCajaModule() {
  const [modalOpen, setModalOpen] = useState(false);
  const [toast, setToast] = useState<string | null>(null);

  const rows = useMemo(
    () =>
      SUMMARY_DATA.map((row) => {
        const totalCompras = row.compras.total;
        const totalVentas = row.ventas.total;
        const saldoFinal = row.saldoInicial + totalCompras - totalVentas;
        return { ...row, saldoFinal };
      }),
    [],
  );

  const totalGeneral = useMemo(
    () =>
      rows.reduce((sum, row) => {
        const saldoFinalPyg = row.saldoFinal * CONVERSION_TO_PYG[row.moneda];
        return sum + saldoFinalPyg;
      }, 0),
    [rows],
  );

  const handleFinalizar = () => {
    setModalOpen(false);
    setToast("Cierre de caja finalizado correctamente.");
    setTimeout(() => setToast(null), 2200);
  };

  return (
    <div className="space-y-6">
      <div className="rounded-3xl border border-[#dbe3ee] bg-white p-6 shadow-sm">
        <div className="mb-6 flex items-center justify-between gap-4">
          <div>
            <p className="text-sm font-medium text-[#64748b]">Cierre de Caja</p>
            <h2 className="text-2xl font-bold tracking-tight text-[#0f172a]">Resumen final del turno</h2>
          </div>
          <button
            onClick={() => setModalOpen(true)}
            className="rounded-xl bg-[#1a7eff] px-4 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-[#176ae6]"
          >
            Finalizar Cierre de Caja
          </button>
        </div>

        <div className="overflow-hidden rounded-2xl border border-[#e2e8f0]">
          <table className="min-w-full border-collapse bg-white text-left text-sm text-[#1f2937]">
            <thead className="bg-[#f8fafc] text-[#475569]">
              <tr>
                <th className="px-4 py-3 font-semibold">Monedas</th>
                <th className="px-4 py-3 font-semibold">Cantidad de Ventas</th>
                <th className="px-4 py-3 font-semibold">Cantidad de Compras</th>
                <th className="px-4 py-3 font-semibold text-right">Saldo Inicial</th>
                <th className="px-4 py-3 font-semibold text-right">Saldo Final Esperado</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.moneda} className="border-t border-[#edf2f7] bg-white hover:bg-[#f8fafc]">
                  <td className="px-4 py-3 font-semibold text-[#0f172a]">{row.moneda}</td>
                  <td className="px-4 py-3">
                    {row.ventas.cantidad} operaciones / {formatNumber(row.ventas.total)}
                  </td>
                  <td className="px-4 py-3">
                    {row.compras.cantidad} operaciones / {formatNumber(row.compras.total)}
                  </td>
                  <td className="px-4 py-3 text-right">{formatNumber(row.saldoInicial)}</td>
                  <td className="px-4 py-3 text-right font-semibold text-[#1a7eff]">
                    {formatNumber(row.saldoFinal)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="mt-6 rounded-2xl border border-[#dbe3ee] bg-[#f0f7ff] p-4">
          <p className="text-sm text-[#64748b]">Fórmula aplicada</p>
          <p className="mt-1 text-base font-semibold text-[#0f172a]">
            Saldo inicial + total compras - total ventas = saldo teórico final en caja
          </p>
          <p className="mt-3 text-2xl font-bold text-[#1a7eff]">{formatNumber(totalGeneral)} PYG</p>
        </div>
      </div>

      {modalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 p-4">
          <div className="w-full max-w-md rounded-2xl bg-white p-6 shadow-2xl">
            <h3 className="text-xl font-bold text-[#0f172a]">¿Desea cerrar la caja y emitir el reporte final?</h3>
            <p className="mt-3 text-sm text-[#64748b]">Al confirmar, se bloquearán nuevas transacciones del turno.</p>

            <div className="mt-6 flex justify-end gap-3">
              <button
                onClick={() => setModalOpen(false)}
                className="rounded-xl border border-[#dbe3ee] bg-white px-4 py-2 text-sm font-semibold text-[#475569] hover:bg-[#f8fafc]"
              >
                Cancelar
              </button>
              <button
                onClick={handleFinalizar}
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
