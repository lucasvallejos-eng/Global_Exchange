import { useEffect, useState } from "react";
import { useTasas } from "../lib/useTasas";
import {
  listarOperaciones,
  type EstadoOperacion,
  type FiltrosHistorial,
  type Operacion,
} from "../lib/operacionesApi";

// Historial de transacciones: solo consulta, como pide el alcance del
// Sprint 3. Antes mostraba una lista escrita a mano y permitía cancelar
// operaciones; ahora lee la base y no modifica nada.

const formatDateTime = (dateStr: string) =>
  new Date(dateStr).toLocaleString("es-PY", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });

const formatCurrency = (value: number) =>
  new Intl.NumberFormat("es-PY", {
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(value);

const ESTILO_ESTADO: Record<EstadoOperacion, string> = {
  PAGADA: "bg-green-100 text-green-700",
  PENDIENTE: "bg-yellow-100 text-yellow-700",
  CANCELADA: "bg-red-100 text-red-700",
  ANULADA: "bg-gray-200 text-gray-700",
};

const claseCampo =
  "w-full rounded-xl border border-[#dbe3ee] bg-[#f8fafc] px-3 py-2 text-sm text-[#1f2937] outline-none focus:border-[#1a7eff]";

export default function HistorialTransaccionesModule() {
  const [operaciones, setOperaciones] = useState<Operacion[]>([]);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filtros, setFiltros] = useState<FiltrosHistorial>({});
  const [seleccionada, setSeleccionada] = useState<Operacion | null>(null);
  const { codigos } = useTasas();

  useEffect(() => {
    let vigente = true;
    setCargando(true);
    setError(null);
    listarOperaciones(filtros)
      .then(({ operaciones: lista }) => {
        if (vigente) setOperaciones(lista);
      })
      .catch((e: unknown) => {
        if (vigente) setError(e instanceof Error ? e.message : "No se pudo cargar el historial.");
      })
      .finally(() => {
        if (vigente) setCargando(false);
      });
    // Si cambian los filtros antes de que llegue la respuesta anterior, se
    // descarta esa respuesta para no pisar la nueva.
    return () => {
      vigente = false;
    };
  }, [filtros]);

  const cambiarFiltro = (clave: keyof FiltrosHistorial, valor: string) =>
    setFiltros((actuales) => ({ ...actuales, [clave]: valor }));

  const hayFiltros = Object.values(filtros).some(Boolean);

  return (
    <div className="space-y-6">
      <div className="rounded-3xl border border-[#dbe3ee] bg-white p-6 shadow-sm">
        <div className="mb-5">
          <p className="text-sm font-medium text-[#64748b]">Historial</p>
          <h2 className="text-2xl font-bold tracking-tight text-[#0f172a]">Transacciones</h2>
        </div>

        <div className="mb-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
          <label className="block">
            <span className="mb-1 block text-xs font-medium text-[#64748b]">Estado</span>
            <select value={filtros.estado ?? ""} onChange={(e) => cambiarFiltro("estado", e.target.value)} className={claseCampo}>
              <option value="">Todos</option>
              <option value="PENDIENTE">Pendiente de pago</option>
              <option value="PAGADA">Pagada</option>
              <option value="CANCELADA">Cancelada</option>
              <option value="ANULADA">Anulada</option>
            </select>
          </label>
          <label className="block">
            <span className="mb-1 block text-xs font-medium text-[#64748b]">Tipo</span>
            <select value={filtros.tipo ?? ""} onChange={(e) => cambiarFiltro("tipo", e.target.value)} className={claseCampo}>
              <option value="">Compras y ventas</option>
              <option value="COMPRA">Compra de divisa</option>
              <option value="VENTA">Venta de divisa</option>
            </select>
          </label>
          <label className="block">
            <span className="mb-1 block text-xs font-medium text-[#64748b]">Moneda</span>
            <select value={filtros.moneda ?? ""} onChange={(e) => cambiarFiltro("moneda", e.target.value)} className={claseCampo}>
              <option value="">Todas</option>
              {codigos.map((codigo) => (
                <option key={codigo} value={codigo}>{codigo}</option>
              ))}
            </select>
          </label>
          <label className="block">
            <span className="mb-1 block text-xs font-medium text-[#64748b]">Desde</span>
            <input type="date" value={filtros.desde ?? ""} onChange={(e) => cambiarFiltro("desde", e.target.value)} className={claseCampo} />
          </label>
          <label className="block">
            <span className="mb-1 block text-xs font-medium text-[#64748b]">Hasta</span>
            <input type="date" value={filtros.hasta ?? ""} onChange={(e) => cambiarFiltro("hasta", e.target.value)} className={claseCampo} />
          </label>
        </div>

        {hayFiltros && (
          <button onClick={() => setFiltros({})} className="mb-4 text-sm font-semibold text-[#1a7eff]">
            Limpiar filtros
          </button>
        )}

        {error && (
          <div className="mb-4 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm font-medium text-red-700">{error}</div>
        )}

        <div className="overflow-x-auto rounded-2xl border border-[#e2e8f0]">
          <table className="min-w-full border-collapse bg-white text-left text-sm text-[#1f2937]">
            <thead className="bg-[#f8fafc] text-[#475569]">
              <tr>
                <th className="px-4 py-3 font-semibold">Transacción</th>
                <th className="px-4 py-3 font-semibold">Cliente</th>
                <th className="px-4 py-3 font-semibold">Estado</th>
                <th className="px-4 py-3 font-semibold">Fecha y Hora</th>
                <th className="px-4 py-3 text-right font-semibold">Monto</th>
                <th className="px-4 py-3 text-right font-semibold">Total PYG</th>
              </tr>
            </thead>
            <tbody>
              {cargando && (
                <tr><td colSpan={6} className="px-4 py-8 text-center text-[#64748b]">Cargando...</td></tr>
              )}
              {!cargando && operaciones.length === 0 && (
                <tr>
                  <td colSpan={6} className="px-4 py-8 text-center text-[#64748b]">
                    {hayFiltros ? "Ninguna transacción coincide con estos filtros." : "Todavía no hay transacciones."}
                  </td>
                </tr>
              )}
              {!cargando && operaciones.map((operacion) => (
                <tr
                  key={operacion.id}
                  onClick={() => setSeleccionada(operacion)}
                  className="cursor-pointer border-t border-[#edf2f7] bg-white hover:bg-[#f8fafc]"
                >
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-3">
                      <span
                        className={`inline-flex rounded-full px-2.5 py-1 text-xs font-semibold ${
                          operacion.tipo === "COMPRA" ? "bg-[#eaf3ff] text-[#1a7eff]" : "bg-[#eefcf3] text-[#16a34a]"
                        }`}
                      >
                        {operacion.tipo === "COMPRA" ? "Compra" : "Venta"}
                      </span>
                      <span className="font-medium text-[#0f172a]">#{operacion.id}</span>
                    </div>
                  </td>
                  <td className="px-4 py-3 text-[#374151]">{operacion.cliente.nombre}</td>
                  <td className="px-4 py-3">
                    <span className={`inline-flex rounded-full px-2.5 py-1 text-xs font-semibold ${ESTILO_ESTADO[operacion.estado]}`}>
                      {operacion.estadoTexto}
                    </span>
                    {operacion.canceladaPorCotizacion && (
                      <span className="mt-1 block text-xs text-[#64748b]">por cambio de cotización</span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-[#374151]">{formatDateTime(operacion.fechaCreacion)}</td>
                  <td className="px-4 py-3 text-right font-semibold text-[#0f172a]">
                    {operacion.montoDivisa} {operacion.moneda}
                  </td>
                  <td className="px-4 py-3 text-right font-semibold text-[#0f172a]">
                    {formatCurrency(operacion.totalGuaranies)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {seleccionada && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 p-4" onClick={() => setSeleccionada(null)}>
          <div className="w-full max-w-lg rounded-2xl bg-white p-6 shadow-2xl" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between gap-4">
              <h3 className="text-xl font-bold text-[#0f172a]">Transacción #{seleccionada.id}</h3>
              <span className={`inline-flex rounded-full px-2.5 py-1 text-xs font-semibold ${ESTILO_ESTADO[seleccionada.estado]}`}>
                {seleccionada.estadoTexto}
              </span>
            </div>

            <div className="mt-5 space-y-2 rounded-2xl border border-[#e2e8f0] bg-[#f8fafc] p-4 text-sm text-[#374151]">
              {[
                ["Operación", `${seleccionada.tipoTexto} — ${seleccionada.moneda}`],
                ["Cliente", seleccionada.cliente.nombre],
                ["Monto", `${seleccionada.montoDivisa} ${seleccionada.moneda}`],
                ["Tasa base", `${formatCurrency(seleccionada.tasaBase)} PYG`],
                ["Tasa aplicada", `${formatCurrency(seleccionada.tasaAplicada)} PYG`],
                ["Subtotal", `${formatCurrency(seleccionada.montoGuaranies)} PYG`],
                [`Comisión (${seleccionada.porcentajeComision} %)`, `${formatCurrency(seleccionada.comision)} PYG`],
                [seleccionada.tipo === "COMPRA" ? "Total pagado" : "Total recibido", `${formatCurrency(seleccionada.totalGuaranies)} PYG`],
                ["Medio de pago", seleccionada.medioPago ?? "Sin especificar"],
                ["Creada", formatDateTime(seleccionada.fechaCreacion)],
              ].map(([etiqueta, valor]) => (
                <div key={etiqueta} className="flex items-center justify-between gap-4">
                  <span className="text-[#64748b]">{etiqueta}</span>
                  <span className="text-right font-semibold text-[#0f172a]">{valor}</span>
                </div>
              ))}
            </div>

            {seleccionada.motivoCancelacion && (
              <p className="mt-4 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
                {seleccionada.motivoCancelacion}
              </p>
            )}

            <div className="mt-6 flex justify-end">
              <button
                onClick={() => setSeleccionada(null)}
                className="rounded-xl border border-[#dbe3ee] bg-white px-4 py-2 text-sm font-semibold text-[#475569] hover:bg-[#f8fafc]"
              >
                Cerrar
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
