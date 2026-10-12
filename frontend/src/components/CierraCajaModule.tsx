import { useEffect, useMemo, useState } from "react";
import { crearCierre } from "../lib/cajaApi";
import { obtenerResumenCierre, type ResumenCierre } from "../lib/cajaApi";
import MontoInput from "./MontoInput";

const formatNumber = (value: number) =>
  new Intl.NumberFormat("es-PY", {
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
  }).format(value);

export default function CierraCajaModule({ onCierre }: { onCierre?: () => void }) {
  const [modalOpen, setModalOpen] = useState(false);
  const [resumen, setResumen] = useState<ResumenCierre["resumen"]>([]);
  const [totalEnLocal, setTotalEnLocal] = useState(0);
  const [monedaLocal, setMonedaLocal] = useState<string | null>(null);
  const [reales, setReales] = useState<Record<string, string>>({});
  const [bloqueado, setBloqueado] = useState(false);
  const [toast, setToast] = useState<string | null>(null);

  useEffect(() => {
    obtenerResumenCierre()
      .then((data) => {
        setResumen(data.resumen);
        setTotalEnLocal(data.totalEnLocal);
        setMonedaLocal(data.monedaLocal);
      })
      .catch(() => setBloqueado(true));
  }, []);

  const rows = useMemo(
    () => resumen.map((row) => ({
      moneda: row.moneda,
      saldoInicial: row.saldoInicial,
      saldoFinal: row.saldoTeorico,
      compras: { cantidad: row.cantidadCompras, total: row.compras },
      ventas: { cantidad: row.cantidadVentas, total: row.ventas },
      conTarjeta: row.comprasConTarjeta,
    })),
    [resumen],
  );

  // Hasta que no se carga el conteo físico de una moneda no hay diferencia que mostrar.
  const diferencia = (moneda: string, teorico: number) =>
    reales[moneda] === undefined || reales[moneda] === "" ? null : Number(reales[moneda]) - teorico;
  const faltanConteos = rows.some((row) => diferencia(row.moneda, row.saldoFinal) === null);

  const handleFinalizar = async () => {
    if (faltanConteos) {
      setModalOpen(false);
      setToast("Cargá el saldo real físico de todas las monedas antes de cerrar.");
      setTimeout(() => setToast(null), 3000);
      return;
    }
    try {
      await crearCierre(Object.fromEntries(rows.map((row) => [row.moneda, Number(reales[row.moneda] || 0)])));
      setModalOpen(false);
      setToast("Cierre de caja finalizado correctamente.");
      setTimeout(() => setToast(null), 2200);
      onCierre?.();
    } catch (error) {
      setToast(error instanceof Error ? error.message : "No se pudo registrar el cierre.");
    }
  };

  return (
    <div className="space-y-6">
      {bloqueado ? (
        <div className="rounded-3xl border border-[#dbe3ee] bg-white p-10 text-center shadow-sm"><h2 className="text-2xl font-bold text-[#0f172a]">Arqueo aún no realizado</h2></div>
      ) : (
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
                <th className="px-4 py-3 font-semibold">Entradas al cajón</th>
                <th className="px-4 py-3 font-semibold">Salidas del cajón</th>
                <th className="px-4 py-3 font-semibold text-right">Saldo Inicial</th>
                <th className="px-4 py-3 font-semibold text-right">Saldo Teórico Final</th>
                <th className="px-4 py-3 font-semibold text-right">Saldo Real Físico</th>
                <th className="px-4 py-3 font-semibold text-right">Diferencia</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.moneda} className="border-t border-[#edf2f7] bg-white hover:bg-[#f8fafc]">
                  <td className="px-4 py-3 font-semibold text-[#0f172a]">{row.moneda}</td>
                  <td className="px-4 py-3">
                    {row.compras.cantidad} operaciones / {formatNumber(row.compras.total)}
                    {row.conTarjeta.cantidad > 0 && (
                      <span className="mt-1 block text-xs text-[#64748b]">
                        + {row.conTarjeta.cantidad} compra(s) con tarjeta: {formatNumber(row.conTarjeta.monto)} {row.moneda} por Stripe (no entran al cajón)
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    {row.ventas.cantidad} operaciones / {formatNumber(row.ventas.total)}
                  </td>
                  <td className="px-4 py-3 text-right">{formatNumber(row.saldoInicial)}</td>
                  <td className="px-4 py-3 text-right font-semibold text-[#1a7eff]">
                    {formatNumber(row.saldoFinal)}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <MontoInput
                      valor={reales[row.moneda] ?? ""}
                      onCambio={(valor) => setReales((current) => ({ ...current, [row.moneda]: valor }))}
                      // Los guaraníes no tienen decimales; las divisas pueden tener monedas (centavos).
                      decimales={row.moneda === monedaLocal ? 0 : 2}
                      className="w-36 rounded-lg border px-2 py-1 text-right"
                    />
                  </td>
                  <td className="px-4 py-3 text-right font-semibold">
                    {(() => {
                      const valor = diferencia(row.moneda, row.saldoFinal);
                      if (valor === null) return <span className="text-[#94a3b8]">—</span>;
                      return <span className={valor === 0 ? "text-green-600" : "text-red-600"}>{valor > 0 ? "+" : ""}{formatNumber(valor)}</span>;
                    })()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="mt-6 rounded-2xl border border-[#dbe3ee] bg-[#f0f7ff] p-4">
          <p className="text-sm text-[#64748b]">Fórmula aplicada</p>
          <p className="mt-1 text-base font-semibold text-[#0f172a]">
            Saldo inicial + entradas - salidas = saldo teórico final en caja
          </p>
          <p className="mt-3 text-sm text-[#64748b]">Saldo teórico total, con las divisas al precio de compra vigente</p>
          <p className="mt-1 text-2xl font-bold text-[#1a7eff]">{formatNumber(totalEnLocal)} {monedaLocal ?? "PYG"}</p>
        </div>
      </div>
      )}

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
