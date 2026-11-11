import { useEffect, useState } from "react";

import { useTasas } from "../lib/useTasas";
import {
  reporteTransacciones,
  urlExportarTransacciones,
  type FiltrosReporte,
  type ReporteTransacciones,
} from "../lib/reportesApi";

// Reporte de transacciones pagadas, cada una con lo que ganó la casa. Es de
// consulta: los filtros se aplican en el backend y el mismo filtro sirve para
// exportar a CSV.

const formatPyg = (value: number) =>
  new Intl.NumberFormat("es-PY", { maximumFractionDigits: 0 }).format(value);

const formatDivisa = (value: number) =>
  new Intl.NumberFormat("es-PY", { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(value);

const formatFecha = (iso: string) =>
  new Date(iso).toLocaleString("es-PY", {
    day: "2-digit", month: "2-digit", year: "numeric", hour: "2-digit", minute: "2-digit", hour12: false,
  });

const claseCampo =
  "w-full rounded-xl border border-[#dbe3ee] bg-[#f8fafc] px-3 py-2 text-sm text-[#1f2937] outline-none focus:border-[#1a7eff]";
const claseEtiqueta = "mb-2 block text-xs font-semibold uppercase tracking-[0.12em] text-[#64748b]";

const POR_PAGINA = 15;

export default function ReportesModule() {
  const { codigos } = useTasas();
  const [filtros, setFiltros] = useState<FiltrosReporte>({});
  const [reporte, setReporte] = useState<ReporteTransacciones | null>(null);
  const [error, setError] = useState("");
  const [pagina, setPagina] = useState(1);

  useEffect(() => {
    let vigente = true;
    setError("");
    reporteTransacciones(filtros)
      .then((datos) => {
        if (!vigente) return;
        setReporte(datos);
        setPagina(1);
      })
      .catch((e: Error) => vigente && setError(e.message));
    return () => {
      vigente = false;
    };
  }, [filtros]);

  const cambiar = (clave: keyof FiltrosReporte, valor: string) =>
    setFiltros((actuales) => ({ ...actuales, [clave]: valor }));

  const filas = reporte?.operaciones ?? [];
  const paginas = Math.max(1, Math.ceil(filas.length / POR_PAGINA));
  const visibles = filas.slice((pagina - 1) * POR_PAGINA, pagina * POR_PAGINA);
  const totales = reporte?.totales;
  const hayFiltros = Object.values(filtros).some(Boolean);

  return (
    <div className="space-y-6">
      <div className="rounded-3xl border border-[#dbe3ee] bg-white p-6 shadow-sm">
        <div className="mb-5 flex flex-wrap items-start justify-between gap-3">
          <div>
            <p className="text-sm font-medium text-[#64748b]">Reportes</p>
            <h2 className="text-2xl font-bold tracking-tight text-[#0f172a]">Transacciones y ganancias</h2>
            <p className="mt-1 text-sm text-[#64748b]">
              Operaciones pagadas. La ganancia es la comisión más el margen de cambio sobre el precio medio.
            </p>
          </div>
          <a
            href={urlExportarTransacciones(filtros)}
            className="rounded-xl bg-[#1a7eff] px-4 py-2.5 text-sm font-semibold text-white hover:bg-[#1569d8]"
          >
            Exportar CSV
          </a>
        </div>

        <div className="mb-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-[1fr_1fr_1fr_1fr_auto]">
          <label className="block">
            <span className={claseEtiqueta}>Desde</span>
            <input type="date" value={filtros.desde ?? ""} onChange={(e) => cambiar("desde", e.target.value)} className={claseCampo} />
          </label>
          <label className="block">
            <span className={claseEtiqueta}>Hasta</span>
            <input type="date" value={filtros.hasta ?? ""} onChange={(e) => cambiar("hasta", e.target.value)} className={claseCampo} />
          </label>
          <label className="block">
            <span className={claseEtiqueta}>Tipo</span>
            <select value={filtros.tipo ?? ""} onChange={(e) => cambiar("tipo", e.target.value)} className={claseCampo}>
              <option value="">Compras y ventas</option>
              <option value="COMPRA">Compra de divisa</option>
              <option value="VENTA">Venta de divisa</option>
            </select>
          </label>
          <label className="block">
            <span className={claseEtiqueta}>Moneda</span>
            <select value={filtros.moneda ?? ""} onChange={(e) => cambiar("moneda", e.target.value)} className={claseCampo}>
              <option value="">Todas</option>
              {codigos.map((codigo) => (
                <option key={codigo} value={codigo}>{codigo}</option>
              ))}
            </select>
          </label>
          <div className="flex items-end">
            <button
              onClick={() => setFiltros({})}
              disabled={!hayFiltros}
              className="rounded-xl border border-[#dbe3ee] bg-white px-4 py-2 text-sm font-medium text-[#374151] disabled:cursor-not-allowed disabled:opacity-50"
            >
              Limpiar
            </button>
          </div>
        </div>

        {error && <p className="mb-4 text-sm font-medium text-red-600">{error}</p>}

        {totales && (
          <div className="mb-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
            {[
              ["Operaciones", formatPyg(totales.operaciones)],
              ["Volumen operado", `${formatPyg(totales.volumen)} PYG`],
              ["Comisiones", `${formatPyg(totales.comisiones)} PYG`],
              ["Margen de cambio", `${formatPyg(totales.margen)} PYG`],
              ["Ganancia", `${formatPyg(totales.ganancia)} PYG`],
            ].map(([etiqueta, valor]) => (
              <div key={etiqueta} className="rounded-2xl border border-[#e2e8f0] bg-[#f8fafc] px-4 py-3">
                <p className="text-xs font-medium text-[#64748b]">{etiqueta}</p>
                <p className="mt-1 text-lg font-semibold text-[#0f172a]">{valor}</p>
              </div>
            ))}
          </div>
        )}

        {filas.length === 0 ? (
          <div className="flex min-h-[200px] items-center justify-center rounded-2xl border border-dashed border-[#dbe3ee] bg-[#f8fafc]">
            <p className="text-sm font-medium text-[#64748b]">
              {reporte ? "No hay operaciones pagadas con estos filtros." : "Cargando el reporte..."}
            </p>
          </div>
        ) : (
          <>
            <div className="overflow-x-auto rounded-2xl border border-[#e2e8f0]">
              <table className="min-w-full border-collapse bg-white text-left text-sm text-[#1f2937]">
                <thead className="bg-[#f8fafc] text-[#475569]">
                  <tr>
                    <th className="px-4 py-3 font-semibold">#</th>
                    <th className="px-4 py-3 font-semibold">Fecha de pago</th>
                    <th className="px-4 py-3 font-semibold">Cliente</th>
                    <th className="px-4 py-3 font-semibold">Operación</th>
                    <th className="px-4 py-3 text-right font-semibold">Monto</th>
                    <th className="px-4 py-3 text-right font-semibold">Monto PYG</th>
                    <th className="px-4 py-3 text-right font-semibold">Comisión</th>
                    <th className="px-4 py-3 text-right font-semibold">Margen</th>
                    <th className="px-4 py-3 text-right font-semibold">Ganancia</th>
                  </tr>
                </thead>
                <tbody>
                  {visibles.map((fila) => (
                    <tr key={fila.id} className="border-t border-[#edf2f7] hover:bg-[#f8fafc]">
                      <td className="px-4 py-3 text-[#64748b]">{fila.id}</td>
                      <td className="whitespace-nowrap px-4 py-3 text-[#475569]">{formatFecha(fila.fecha)}</td>
                      <td className="px-4 py-3">{fila.cliente}</td>
                      <td className="px-4 py-3 text-[#475569]">{fila.tipoTexto}</td>
                      <td className="whitespace-nowrap px-4 py-3 text-right tabular-nums">
                        {formatDivisa(fila.montoDivisa)} {fila.moneda}
                      </td>
                      <td className="px-4 py-3 text-right tabular-nums">{formatPyg(fila.montoGuaranies)}</td>
                      <td className="px-4 py-3 text-right tabular-nums">{formatPyg(fila.comision)}</td>
                      <td className="px-4 py-3 text-right tabular-nums">{formatPyg(fila.margen)}</td>
                      <td className="px-4 py-3 text-right font-semibold tabular-nums text-[#0f172a]">
                        {formatPyg(fila.ganancia)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className="mt-5 flex items-center justify-between gap-3">
              <p className="text-sm text-[#64748b]">
                Mostrando {visibles.length} de {filas.length} operaciones
              </p>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setPagina((p) => Math.max(1, p - 1))}
                  disabled={pagina === 1}
                  className="rounded-lg border border-[#dbe3ee] bg-white px-3 py-1.5 text-sm font-medium text-[#374151] disabled:cursor-not-allowed disabled:opacity-50"
                >
                  Anterior
                </button>
                <span className="text-sm text-[#64748b]">Página {pagina} de {paginas}</span>
                <button
                  onClick={() => setPagina((p) => Math.min(paginas, p + 1))}
                  disabled={pagina === paginas}
                  className="rounded-lg border border-[#dbe3ee] bg-white px-3 py-1.5 text-sm font-medium text-[#374151] disabled:cursor-not-allowed disabled:opacity-50"
                >
                  Siguiente
                </button>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
