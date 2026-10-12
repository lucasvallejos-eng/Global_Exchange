import { useEffect, useState } from "react";
import { listarHistorialCaja, type CajaHistorial } from "../lib/cajaApi";

// Historial de las cajas: cada apertura (turno) con sus compras y ventas.
// El cajero ve sus cajas; administrador y analista, las de todos (lo decide el backend).

const formatDateTime = (dateStr: string) =>
  new Date(dateStr).toLocaleString("es-PY", {
    day: "2-digit", month: "2-digit", year: "numeric", hour: "2-digit", minute: "2-digit", hour12: false,
  });

const formatHora = (dateStr: string) =>
  new Date(dateStr).toLocaleTimeString("es-PY", { hour: "2-digit", minute: "2-digit", hour12: false });

const formatNumber = (value: number) =>
  new Intl.NumberFormat("es-PY", { maximumFractionDigits: 2 }).format(value);

const FORMAS_PAGO: Record<string, string> = {
  EFECTIVO: "Efectivo",
  TARJETA_STRIPE: "Tarjeta (Stripe)",
  TRANSFERENCIA: "Transferencia",
  BILLETERA_DIGITAL: "Billetera digital",
  TARJETA_CREDITO: "Tarjeta de crédito (POS)",
  TARJETA_DEBITO: "Tarjeta de débito (POS)",
};

const claseCampo =
  "w-full rounded-xl border border-[#dbe3ee] bg-[#f8fafc] px-3 py-2 text-sm text-[#1f2937] outline-none focus:border-[#1a7eff]";

export default function HistorialCajaModule() {
  const [cajas, setCajas] = useState<CajaHistorial[]>([]);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filtros, setFiltros] = useState<{ desde?: string; hasta?: string }>({});
  // Cajas desplegadas: por defecto, la más reciente.
  const [abiertas, setAbiertas] = useState<Set<number>>(new Set());

  useEffect(() => {
    let vigente = true;
    setCargando(true);
    setError(null);
    listarHistorialCaja(filtros)
      .then(({ aperturas }) => {
        if (!vigente) return;
        setCajas(aperturas);
        setAbiertas(new Set(aperturas.slice(0, 1).map((c) => c.id)));
      })
      .catch((e: unknown) => vigente && setError(e instanceof Error ? e.message : "No se pudo cargar el historial."))
      .finally(() => vigente && setCargando(false));
    return () => {
      vigente = false;
    };
  }, [filtros]);

  const alternar = (id: number) =>
    setAbiertas((actuales) => {
      const nuevas = new Set(actuales);
      if (nuevas.has(id)) nuevas.delete(id);
      else nuevas.add(id);
      return nuevas;
    });

  return (
    <div className="space-y-6">
      <div className="rounded-3xl border border-[#dbe3ee] bg-white p-6 shadow-sm">
        <div className="mb-5 flex flex-wrap items-end justify-between gap-4">
          <div>
            <p className="text-sm font-medium text-[#64748b]">Historial</p>
            <h2 className="text-2xl font-bold tracking-tight text-[#0f172a]">Operaciones de caja</h2>
          </div>
          <div className="flex flex-wrap items-end gap-3">
            <label className="block text-xs text-[#64748b]">
              Desde
              <input type="date" value={filtros.desde ?? ""} onChange={(e) => setFiltros((f) => ({ ...f, desde: e.target.value }))} className={claseCampo} />
            </label>
            <label className="block text-xs text-[#64748b]">
              Hasta
              <input type="date" value={filtros.hasta ?? ""} onChange={(e) => setFiltros((f) => ({ ...f, hasta: e.target.value }))} className={claseCampo} />
            </label>
            {(filtros.desde || filtros.hasta) && (
              <button onClick={() => setFiltros({})} className="pb-2 text-sm font-semibold text-[#1a7eff]">Limpiar</button>
            )}
          </div>
        </div>

        {error && <div className="mb-4 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm font-medium text-red-700">{error}</div>}
        {cargando && <p className="py-8 text-center text-[#64748b]">Cargando...</p>}
        {!cargando && !error && cajas.length === 0 && (
          <p className="py-8 text-center text-[#64748b]">Todavía no hay cajas abiertas en este período.</p>
        )}

        <div className="space-y-4">
          {!cargando && cajas.map((caja) => {
            const abierta = abiertas.has(caja.id);
            const compras = caja.operaciones.filter((o) => o.tipo === "COMPRA").length;
            const ventas = caja.operaciones.length - compras;
            return (
              <div key={caja.id} className="overflow-hidden rounded-2xl border border-[#e2e8f0]">
                <button
                  onClick={() => alternar(caja.id)}
                  className="flex w-full flex-wrap items-center justify-between gap-3 bg-[#f8fafc] px-4 py-3 text-left hover:bg-[#f1f5f9]"
                >
                  <div>
                    <p className="font-semibold text-[#0f172a]">
                      Caja #{caja.id} · abierta el {formatDateTime(caja.fechaHoraApertura)}
                      {caja.fechaHoraCierre && ` · cerrada a las ${formatHora(caja.fechaHoraCierre)}`}
                    </p>
                    <p className="text-xs text-[#64748b]">
                      {caja.cajero ? `Cajero: ${caja.cajero} · ` : ""}
                      {compras} compra(s), {ventas} venta(s)
                    </p>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className={`rounded-full px-2.5 py-1 text-xs font-semibold ${caja.estado === "activa" ? "bg-green-100 text-green-700" : "bg-slate-200 text-slate-600"}`}>
                      {caja.estado === "activa" ? "Abierta" : "Cerrada"}
                    </span>
                    <span className="text-[#64748b]">{abierta ? "▲" : "▼"}</span>
                  </div>
                </button>

                {abierta && (
                  <div className="overflow-x-auto">
                    <p className="border-t border-[#edf2f7] px-4 py-2 text-xs text-[#64748b]">
                      Saldo inicial: {Object.entries(caja.saldoInicial).map(([m, v]) => `${formatNumber(v)} ${m}`).join(" · ") || "—"}
                    </p>
                    <table className="min-w-full border-collapse bg-white text-left text-sm text-[#1f2937]">
                      <thead className="bg-white text-[#475569]">
                        <tr className="border-t border-[#edf2f7]">
                          <th className="px-4 py-2 font-semibold">Hora</th>
                          <th className="px-4 py-2 font-semibold">Operación</th>
                          <th className="px-4 py-2 font-semibold">Cliente</th>
                          <th className="px-4 py-2 font-semibold">Forma de pago</th>
                          <th className="px-4 py-2 text-right font-semibold">Monto</th>
                          <th className="px-4 py-2 text-right font-semibold">Cotización</th>
                          <th className="px-4 py-2 text-right font-semibold">Total PYG</th>
                        </tr>
                      </thead>
                      <tbody>
                        {caja.operaciones.length === 0 && (
                          <tr><td colSpan={7} className="border-t border-[#edf2f7] px-4 py-6 text-center text-[#64748b]">Sin operaciones en esta caja.</td></tr>
                        )}
                        {caja.operaciones.map((op) => (
                          <tr key={`${op.tipo}-${op.id}`} className="border-t border-[#edf2f7]">
                            <td className="px-4 py-2 text-[#374151]">{formatHora(op.fechaHora)}</td>
                            <td className="px-4 py-2">
                              <span className={`inline-flex rounded-full px-2.5 py-1 text-xs font-semibold ${op.tipo === "COMPRA" ? "bg-[#eaf3ff] text-[#1a7eff]" : "bg-[#eefcf3] text-[#16a34a]"}`}>
                                {op.tipo === "COMPRA" ? "Compra" : "Venta"} #{op.id}
                              </span>
                            </td>
                            <td className="px-4 py-2 text-[#374151]">{op.cliente.nombre}</td>
                            <td className="px-4 py-2 text-[#374151]">
                              {FORMAS_PAGO[op.formaPago ?? ""] ?? op.formaPago ?? "—"}
                              {op.pagoConTarjeta && op.medioPago && <span className="block text-xs text-[#64748b]">{op.medioPago}</span>}
                            </td>
                            <td className="px-4 py-2 text-right font-semibold text-[#0f172a]">{formatNumber(op.montoDivisa)} {op.moneda}</td>
                            <td className="px-4 py-2 text-right text-[#374151]">{formatNumber(op.cotizacion)}</td>
                            <td className="px-4 py-2 text-right font-semibold text-[#0f172a]">{formatNumber(op.totalGuaranies)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                    {caja.diferenciaCierre && (
                      <p className="border-t border-[#edf2f7] px-4 py-2 text-xs text-[#64748b]">
                        Diferencia al cierre: {Object.entries(caja.diferenciaCierre).map(([m, v]) => `${v > 0 ? "+" : ""}${formatNumber(v)} ${m}`).join(" · ")}
                      </p>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
