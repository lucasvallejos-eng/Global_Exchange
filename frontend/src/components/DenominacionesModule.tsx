import { useEffect, useMemo, useState } from "react";
import {
  borrarDenominacion,
  crearDenominacion,
  listarDenominaciones,
  type Denominacion,
} from "../lib/denominacionesApi";
import { listarMonedas, type Moneda } from "../lib/monedasApi";

const formatValor = (valor: number, codigo?: string) => {
  if (codigo === "PYG") {
    return new Intl.NumberFormat("es-PY", {
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(valor);
  }
  return new Intl.NumberFormat("es-PY", {
    minimumFractionDigits: Number.isInteger(valor) ? 0 : 2,
    maximumFractionDigits: 2,
  }).format(valor);
};

export default function DenominacionesModule() {
  const [monedas, setMonedas] = useState<Moneda[]>([]);
  const [denominaciones, setDenominaciones] = useState<Denominacion[]>([]);
  const [cargando, setCargando] = useState(true);

  // Filtro por moneda: "" = todas las monedas
  const [filtroMonedaId, setFiltroMonedaId] = useState<string>("");

  // Modal Agregar Denominacion
  const [showModal, setShowModal] = useState(false);
  const [formData, setFormData] = useState({ monedaId: "", valor: "" });
  const [guardando, setGuardando] = useState(false);

  // Modal de Confirmacion de Borrado
  const [deletingDenominacion, setDeletingDenominacion] = useState<Denominacion | null>(null);
  const [borrando, setBorrando] = useState(false);

  // Toast feedback
  const [toast, setToast] = useState<{ tipo: "success" | "error"; mensaje: string } | null>(null);

  const avisar = (mensaje: string, tipo: "success" | "error" = "success") => {
    setToast({ tipo, mensaje });
    setTimeout(() => setToast(null), 3000);
  };

  const cargarDatos = async () => {
    try {
      setCargando(true);
      const [listaMonedas, listaDenom] = await Promise.all([
        listarMonedas(),
        listarDenominaciones(),
      ]);
      setMonedas(listaMonedas);
      setDenominaciones(listaDenom);
    } catch (e) {
      avisar(e instanceof Error ? e.message : "Error al cargar los datos.", "error");
    } finally {
      setCargando(false);
    }
  };

  useEffect(() => {
    void cargarDatos();
  }, []);

  const denominacionesPorMoneda = useMemo(() => {
    const mapa: Record<number, Denominacion[]> = {};
    for (const m of monedas) {
      mapa[m.id] = [];
    }
    for (const d of denominaciones) {
      if (mapa[d.monedaId]) {
        mapa[d.monedaId].push(d);
      } else {
        mapa[d.monedaId] = [d];
      }
    }
    for (const id in mapa) {
      mapa[id].sort((a, b) => a.valor - b.valor);
    }
    return mapa;
  }, [monedas, denominaciones]);

  const monedasFiltradas = useMemo(() => {
    if (!filtroMonedaId) return monedas;
    return monedas.filter((m) => String(m.id) === filtroMonedaId);
  }, [monedas, filtroMonedaId]);

  const abrirModalCrear = (monedaIdDefecto?: number) => {
    const primeraMonedaId = monedaIdDefecto ?? monedas[0]?.id ?? "";
    setFormData({ monedaId: String(primeraMonedaId), valor: "" });
    setShowModal(true);
  };

  const handleGuardar = async (e: React.FormEvent) => {
    e.preventDefault();
    const monedaIdNum = Number(formData.monedaId);
    const valorNum = Number.parseFloat(formData.valor);
    if (!formData.monedaId || !monedaIdNum) {
      avisar("Debe seleccionar una moneda.", "error");
      return;
    }
    if (Number.isNaN(valorNum) || valorNum <= 0) {
      avisar("El valor nominal debe ser un numero positivo mayor a 0.", "error");
      return;
    }
    try {
      setGuardando(true);
      await crearDenominacion({ moneda_id: monedaIdNum, valor: valorNum });
      avisar("Denominacion creada exitosamente.");
      setShowModal(false);
      await cargarDatos();
    } catch (err) {
      avisar(err instanceof Error ? err.message : "Error al guardar la denominacion.", "error");
    } finally {
      setGuardando(false);
    }
  };

  const confirmarBorrado = async () => {
    if (!deletingDenominacion) return;
    try {
      setBorrando(true);
      await borrarDenominacion(deletingDenominacion.id);
      avisar(`Denominacion ${formatValor(deletingDenominacion.valor, deletingDenominacion.monedaCodigo)} ${deletingDenominacion.monedaCodigo} eliminada.`);
      setDeletingDenominacion(null);
      await cargarDatos();
    } catch (err) {
      avisar(err instanceof Error ? err.message : "Error al eliminar la denominacion.", "error");
    } finally {
      setBorrando(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header card */}
      <div className="rounded-3xl border border-[#dbe3ee] bg-white p-6 shadow-sm">
        <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <div>
            <div className="flex items-center gap-2">
              <span className="rounded-md bg-blue-50 px-2 py-0.5 text-xs font-semibold text-[#1a7eff]">Modulo 1:N</span>
              <p className="text-sm font-medium text-[#64748b]">Panel de Administracion</p>
            </div>
            <h2 className="mt-1 text-2xl font-bold tracking-tight text-[#0f172a]">Gestion de Denominaciones</h2>
            <p className="mt-0.5 text-sm text-[#64748b]">Administra los valores nominales de billetes y monedas vinculados a cada divisa.</p>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <button
              onClick={() => abrirModalCrear()}
              disabled={monedas.length === 0}
              className="inline-flex items-center gap-2 rounded-xl bg-[#1a7eff] px-4 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-[#146be7] disabled:cursor-not-allowed disabled:opacity-50"
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                <line x1="12" y1="5" x2="12" y2="19" />
                <line x1="5" y1="12" x2="19" y2="12" />
              </svg>
              Agregar Denominacion
            </button>
          </div>
        </div>

        {/* Barra de filtro y estadisticas */}
        <div className="mt-6 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between border-t border-[#f1f5f9] pt-4">
          <div className="relative max-w-sm flex-1">
            <svg className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-[#94a3b8]" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="12" cy="12" r="10" />
              <path d="M16 8h-6a2 2 0 1 0 0 4h4a2 2 0 1 1 0 4H8" />
              <path d="M12 6v2m0 8v2" />
            </svg>
            <select
              value={filtroMonedaId}
              onChange={(e) => setFiltroMonedaId(e.target.value)}
              className="w-full appearance-none rounded-xl border border-[#dbe3ee] bg-[#f8fafc] py-2 pl-9 pr-8 text-sm text-[#1f2937] outline-none transition focus:border-[#1a7eff] focus:bg-white"
            >
              <option value="">Todas las monedas</option>
              {monedas.map((m) => (
                <option key={m.id} value={String(m.id)}>
                  {m.codigo} - {m.nombre}
                </option>
              ))}
            </select>
            <svg className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-[#94a3b8]" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <polyline points="6 9 12 15 18 9" />
            </svg>
          </div>
          <div className="flex items-center gap-4 text-xs font-medium text-[#64748b]">
            <span className="flex items-center gap-1.5">
              <span className="h-2 w-2 rounded-full bg-[#1a7eff]" />
              {monedas.length} Divisas registradas
            </span>
            <span className="flex items-center gap-1.5">
              <span className="h-2 w-2 rounded-full bg-emerald-500" />
              {denominaciones.length} Denominaciones activas
            </span>
          </div>
        </div>
      </div>

      {/* Loading state */}
      {cargando && (
        <div className="flex min-h-[300px] items-center justify-center rounded-3xl border border-[#dbe3ee] bg-white p-12">
          <div className="flex flex-col items-center gap-3">
            <div className="h-8 w-8 animate-spin rounded-full border-4 border-[#1a7eff] border-t-transparent" />
            <p className="text-sm font-medium text-[#64748b]">Cargando divisas y denominaciones...</p>
          </div>
        </div>
      )}

      {/* Empty state */}
      {!cargando && monedas.length === 0 && (
        <div className="flex min-h-[320px] flex-col items-center justify-center rounded-3xl border-2 border-dashed border-[#dbe3ee] bg-white p-12 text-center">
          <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-blue-50 text-[#1a7eff]">
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="12" cy="12" r="10" />
              <path d="M16 8h-6a2 2 0 1 0 0 4h4a2 2 0 1 1 0 4H8" />
              <path d="M12 6v2m0 8v2" />
            </svg>
          </div>
          <h3 className="text-lg font-bold text-[#0f172a]">No hay divisas registradas</h3>
          <p className="mt-1 max-w-sm text-sm text-[#64748b]">Para asociar denominaciones primero debes registrar divisas en el modulo de Monedas.</p>
        </div>
      )}

      {/* Tablas por moneda */}
      {!cargando && monedasFiltradas.length > 0 && (
        <div className="space-y-6">
          {monedasFiltradas.map((moneda) => {
            const denoms = denominacionesPorMoneda[moneda.id] ?? [];
            const tieneDenominaciones = denoms.length > 0;
            return (
              <div key={moneda.id} className="overflow-hidden rounded-3xl border border-[#dbe3ee] bg-white shadow-sm transition hover:shadow-md">
                <div className="flex flex-col gap-3 border-b border-[#edf2f7] bg-[#f8fafc] px-6 py-4 sm:flex-row sm:items-center sm:justify-between">
                  <div className="flex items-center gap-3">
                    <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-[#1a7eff] to-[#0052cc] font-bold text-white shadow-sm">
                      {moneda.simbolo || moneda.codigo.charAt(0)}
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <h3 className="text-base font-bold text-[#0f172a]">{moneda.nombre}</h3>
                        <span className="rounded-md bg-slate-200/70 px-2 py-0.5 text-xs font-bold text-[#334155]">{moneda.codigo}</span>
                        <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-semibold ${moneda.activo ? "bg-emerald-100 text-emerald-700" : "bg-amber-100 text-amber-700"}`}>
                          <span className={`h-1.5 w-1.5 rounded-full ${moneda.activo ? "bg-emerald-500" : "bg-amber-500"}`} />
                          {moneda.activo ? "Activa" : "Inactiva"}
                        </span>
                      </div>
                      <p className="text-xs text-[#64748b]">
                        {denoms.length === 1 ? "1 denominacion configurada" : `${denoms.length} denominaciones configuradas`}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2 self-start sm:self-auto">
                    <button
                      onClick={() => abrirModalCrear(moneda.id)}
                      className="inline-flex items-center gap-1.5 rounded-lg border border-[#dbe3ee] bg-white px-3 py-1.5 text-xs font-semibold text-[#1a7eff] shadow-sm transition hover:bg-blue-50"
                      title={`Agregar denominacion para ${moneda.codigo}`}
                    >
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                        <line x1="12" y1="5" x2="12" y2="19" />
                        <line x1="5" y1="12" x2="19" y2="12" />
                      </svg>
                      Nueva Denominacion
                    </button>
                  </div>
                </div>

                {tieneDenominaciones ? (
                  <div className="overflow-x-auto">
                    <table className="min-w-full border-collapse text-left text-sm text-[#1f2937]">
                      <thead className="border-b border-[#edf2f7] bg-white text-xs uppercase tracking-wider text-[#64748b]">
                        <tr>
                          <th className="px-6 py-3 font-semibold">Valor Nominal</th>
                          <th className="px-6 py-3 font-semibold">Codigo Divisa</th>
                          <th className="px-6 py-3 text-right font-semibold">Acciones</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-[#edf2f7] bg-white">
                        {denoms.map((d) => (
                          <tr key={d.id} className="transition hover:bg-[#f8fafc]">
                            <td className="whitespace-nowrap px-6 py-3.5">
                              <span className="font-bold text-[#0f172a] text-base">{formatValor(d.valor, moneda.codigo)}</span>
                            </td>
                            <td className="whitespace-nowrap px-6 py-3.5 text-xs font-medium text-[#64748b]">{moneda.codigo}</td>
                            <td className="whitespace-nowrap px-6 py-3.5 text-right">
                              <button
                                type="button"
                                onClick={() => setDeletingDenominacion(d)}
                                className="rounded-lg border border-red-200 bg-red-50/60 px-3 py-1.5 text-xs font-semibold text-red-600 transition hover:bg-red-100"
                              >
                                Borrar
                              </button>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : (
                  <div className="flex flex-col items-center justify-center p-8 text-center bg-white">
                    <div className="mb-2 flex h-10 w-10 items-center justify-center rounded-xl bg-slate-100 text-[#94a3b8]">
                      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <circle cx="12" cy="12" r="10" />
                        <line x1="12" y1="8" x2="12" y2="12" />
                        <line x1="12" y1="16" x2="12.01" y2="16" />
                      </svg>
                    </div>
                    <p className="text-sm font-semibold text-[#475569]">Sin denominaciones registradas</p>
                    <p className="mt-1 text-xs text-[#94a3b8] max-w-xs">Esta divisa no posee billetes o monedas nominales asignados en el sistema.</p>
                    <button onClick={() => abrirModalCrear(moneda.id)} className="mt-3 text-xs font-semibold text-[#1a7eff] hover:underline">
                      + Agregar primera denominacion
                    </button>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* Modal Agregar Denominacion */}
      {showModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 p-4 backdrop-blur-sm">
          <div className="w-full max-w-md rounded-2xl bg-white p-6 shadow-2xl animate-in fade-in zoom-in-95 duration-150">
            <div className="flex items-center justify-between border-b border-[#edf2f7] pb-3">
              <div>
                <h3 className="text-xl font-bold text-[#0f172a]">Agregar Denominacion</h3>
                <p className="text-xs text-[#64748b] mt-0.5">Asigna un nuevo valor nominal a la divisa seleccionada.</p>
              </div>
              <button type="button" onClick={() => setShowModal(false)} className="rounded-lg p-1.5 text-[#94a3b8] transition hover:bg-slate-100 hover:text-[#475569]">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <line x1="18" y1="6" x2="6" y2="18" />
                  <line x1="6" y1="6" x2="18" y2="18" />
                </svg>
              </button>
            </div>
            <form onSubmit={handleGuardar} className="mt-5 space-y-4">
              <div>
                <label className="block text-xs font-bold uppercase tracking-wider text-[#475569] mb-1.5">Moneda / Divisa</label>
                <select
                  value={formData.monedaId}
                  onChange={(e) => setFormData({ ...formData, monedaId: e.target.value })}
                  className="w-full rounded-xl border border-[#dbe3ee] bg-[#f8fafc] px-3.5 py-2.5 text-sm font-medium text-[#1f2937] outline-none transition focus:border-[#1a7eff] focus:bg-white"
                  required
                >
                  <option value="" disabled>Seleccionar divisa...</option>
                  {monedas.map((m) => (
                    <option key={m.id} value={m.id}>
                      {m.codigo} - {m.nombre} ({m.simbolo})
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-xs font-bold uppercase tracking-wider text-[#475569] mb-1.5">Valor Nominal (Denominacion)</label>
                <div className="relative">
                  <input
                    type="number"
                    step="any"
                    min="0.01"
                    value={formData.valor}
                    onChange={(e) => setFormData({ ...formData, valor: e.target.value })}
                    placeholder="Ej. 10, 20, 50, 100 o 10000"
                    className="w-full rounded-xl border border-[#dbe3ee] bg-[#f8fafc] px-3.5 py-2.5 text-sm font-semibold text-[#1f2937] placeholder-[#94a3b8] outline-none transition focus:border-[#1a7eff] focus:bg-white"
                    required
                    autoFocus
                  />
                  {formData.monedaId && (
                    <span className="absolute right-3.5 top-1/2 -translate-y-1/2 text-xs font-bold text-[#64748b]">
                      {monedas.find((m) => String(m.id) === formData.monedaId)?.codigo}
                    </span>
                  )}
                </div>
                <p className="mt-1 text-[11px] text-[#64748b]">Ingrese unicamente montos numericos mayores a 0 (ej: 1, 5, 10, 20, 50, 100).</p>
              </div>
              <div className="mt-6 flex justify-end gap-3 border-t border-[#edf2f7] pt-4">
                <button type="button" onClick={() => setShowModal(false)} disabled={guardando} className="rounded-xl border border-[#dbe3ee] bg-white px-4 py-2 text-sm font-semibold text-[#475569] transition hover:bg-slate-50">
                  Cancelar
                </button>
                <button type="submit" disabled={guardando} className="inline-flex items-center gap-2 rounded-xl bg-[#1a7eff] px-4 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-[#146be7] disabled:opacity-50">
                  {guardando ? (
                    <>
                      <span className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
                      Guardando...
                    </>
                  ) : ("Guardar")}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal Confirmacion Borrado */}
      {deletingDenominacion && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 p-4 backdrop-blur-sm">
          <div className="w-full max-w-md rounded-2xl bg-white p-6 shadow-2xl animate-in fade-in zoom-in-95 duration-150">
            <div className="flex items-center gap-3 text-red-600">
              <div className="flex h-10 w-10 items-center justify-center rounded-full bg-red-100">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M3 6h18m-2 0v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
                  <line x1="10" y1="11" x2="10" y2="17" />
                  <line x1="14" y1="11" x2="14" y2="17" />
                </svg>
              </div>
              <h3 className="text-lg font-bold text-[#0f172a]">Eliminar denominacion?</h3>
            </div>
            <p className="mt-3 text-sm text-[#64748b]">
              Esta seguro de que deseas eliminar la denominacion nominal de{" "}
              <strong className="text-[#0f172a]">
                {formatValor(deletingDenominacion.valor, deletingDenominacion.monedaCodigo)}{" "}
                {deletingDenominacion.monedaCodigo}
              </strong>
              ? Esta accion no se puede deshacer.
            </p>
            <div className="mt-6 flex justify-end gap-3 border-t border-[#edf2f7] pt-4">
              <button type="button" onClick={() => setDeletingDenominacion(null)} disabled={borrando} className="rounded-xl border border-[#dbe3ee] bg-white px-4 py-2 text-sm font-semibold text-[#475569] hover:bg-slate-50">
                Cancelar
              </button>
              <button type="button" onClick={confirmarBorrado} disabled={borrando} className="inline-flex items-center gap-2 rounded-xl bg-red-600 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-red-700 disabled:opacity-50">
                {borrando ? (
                  <>
                    <span className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
                    Borrando...
                  </>
                ) : ("Confirmar Borrado")}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Toast */}
      {toast && (
        <div className={`fixed bottom-6 right-6 z-[60] flex items-center gap-2.5 rounded-xl px-4 py-3 text-sm font-medium text-white shadow-xl ${toast.tipo === "error" ? "bg-red-600" : "bg-[#0f172a]"}`}>
          {toast.tipo === "error" ? (
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="12" cy="12" r="10" />
              <line x1="12" y1="8" x2="12" y2="12" />
              <line x1="12" y1="16" x2="12.01" y2="16" />
            </svg>
          ) : (
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <polyline points="20 6 9 17 4 12" />
            </svg>
          )}
          <span>{toast.mensaje}</span>
        </div>
      )}
    </div>
  );
}
