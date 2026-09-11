import { useEffect, useState } from "react";
import { actualizarSegmento, listarSegmentos, type Segmento } from "../lib/comisionesApi";

// Los segmentos y su porcentaje de comisión salen de la base (app `comisiones`).
// El modelo guarda UN porcentaje por segmento, no dos: la maqueta original
// dibujaba columnas de venta y compra que no existían en ninguna tabla.
//
// Los segmentos son fijos (Minorista, VIP, Corporativo): solo se puede
// modificar su porcentaje y su descripción, no crear ni borrar. Dar de alta o
// eliminar segmentos se hace desde las pantallas de Django.

export default function PorcentajesModule() {
  const [rows, setRows] = useState<Segmento[]>([]);
  const [cargando, setCargando] = useState(true);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editandoId, setEditandoId] = useState<number | null>(null);
  const [toast, setToast] = useState<string | null>(null);
  const [formData, setFormData] = useState({ nombre: "", porcentaje: "", descripcion: "" });

  const avisar = (mensaje: string) => {
    setToast(mensaje);
    setTimeout(() => setToast(null), 2800);
  };

  const recargar = async () => {
    try {
      setRows(await listarSegmentos());
    } catch (e) {
      avisar(e instanceof Error ? e.message : "No se pudieron cargar los segmentos.");
    } finally {
      setCargando(false);
    }
  };

  useEffect(() => {
    void recargar();
  }, []);

  const openEdit = (row: Segmento) => {
    setEditandoId(row.id);
    setFormData({
      nombre: row.nombre,
      porcentaje: String(row.porcentajeComision),
      descripcion: row.descripcion,
    });
    setIsModalOpen(true);
  };

  const handleSave = async () => {
    if (editandoId === null) return;
    if (formData.porcentaje === "") {
      avisar("El porcentaje es obligatorio.");
      return;
    }

    try {
      await actualizarSegmento(editandoId, {
        porcentajeComision: Number(formData.porcentaje),
        descripcion: formData.descripcion,
      });
      await recargar();
      setIsModalOpen(false);
      avisar(`Porcentaje actualizado para ${formData.nombre}.`);
    } catch (e) {
      avisar(e instanceof Error ? e.message : "No se pudo guardar el segmento.");
    }
  };

  return (
    <div className="space-y-6">
      <div className="rounded-3xl border border-[#dbe3ee] bg-white p-6 shadow-sm">
        <div className="mb-5">
          <p className="text-sm font-medium text-[#64748b]">Administración</p>
          <h2 className="text-2xl font-bold tracking-tight text-[#0f172a]">
            Porcentajes de comisión por segmento
          </h2>
        </div>

        <div className="overflow-x-auto rounded-2xl border border-[#e2e8f0]">
          <table className="min-w-full border-collapse bg-white text-left text-sm text-[#1f2937]">
            <thead className="bg-[#f8fafc] text-[#475569]">
              <tr>
                <th className="px-4 py-3 font-semibold">Segmento</th>
                <th className="px-4 py-3 font-semibold">Comisión</th>
                <th className="px-4 py-3 font-semibold">Clientes</th>
                <th className="px-4 py-3 font-semibold">Estado</th>
                <th className="px-4 py-3 font-semibold">Descripción</th>
                <th className="px-4 py-3 text-center font-semibold">Acciones</th>
              </tr>
            </thead>
            <tbody>
              {cargando && (
                <tr>
                  <td colSpan={6} className="px-4 py-6 text-center text-[#64748b]">
                    Cargando segmentos…
                  </td>
                </tr>
              )}

              {!cargando && rows.length === 0 && (
                <tr>
                  <td colSpan={6} className="px-4 py-6 text-center text-[#64748b]">
                    Todavía no hay segmentos cargados.
                  </td>
                </tr>
              )}

              {rows.map((row) => (
                <tr key={row.id} className="border-t border-[#edf2f7] bg-white hover:bg-[#f8fafc]">
                  <td className="px-4 py-3 font-medium text-[#0f172a]">{row.nombre}</td>
                  <td className="px-4 py-3 font-semibold tabular-nums text-[#0f172a]">
                    {row.porcentajeComision}%
                  </td>
                  <td className="px-4 py-3 tabular-nums text-[#475569]">
                    {row.cantidadClientes ?? 0}
                  </td>
                  <td className="px-4 py-3">
                    <span
                      className={`rounded-full px-2.5 py-1 text-xs font-semibold ${
                        row.activo ? "bg-green-100 text-green-700" : "bg-slate-200 text-slate-600"
                      }`}
                    >
                      {row.activo ? "Activo" : "Inactivo"}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-[#475569]">{row.descripcion || "—"}</td>
                  <td className="px-4 py-3">
                    <div className="flex justify-center gap-2">
                      <button
                        onClick={() => openEdit(row)}
                        className="rounded-lg bg-[#eaf3ff] px-3 py-1.5 text-xs font-semibold text-[#1a7eff] hover:bg-[#dfeeff]"
                      >
                        Modificar
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 px-4">
          <div className="w-full max-w-xl rounded-2xl bg-white p-6 shadow-2xl">
            <h3 className="text-2xl font-bold text-[#0f172a]">Modificar porcentaje</h3>

            <div className="mt-5 grid gap-4 md:grid-cols-2">
              <label className="block">
                <span className="mb-2 block text-sm font-medium text-[#374151]">Segmento</span>
                <input
                  value={formData.nombre}
                  readOnly
                  className="w-full rounded-xl border border-[#dbe3ee] bg-[#eef2f7] px-3 py-2.5 text-sm text-[#475569] outline-none"
                />
              </label>

              <label className="block">
                <span className="mb-2 block text-sm font-medium text-[#374151]">
                  Porcentaje de comisión (%)
                </span>
                <input
                  type="number"
                  step="0.01"
                  min="0"
                  max="100"
                  value={formData.porcentaje}
                  onChange={(e) => setFormData({ ...formData, porcentaje: e.target.value })}
                  className="w-full rounded-xl border border-[#dbe3ee] bg-[#f8fafc] px-3 py-2.5 text-sm text-[#1f2937] outline-none focus:border-[#1a7eff]"
                />
              </label>

              <label className="block md:col-span-2">
                <span className="mb-2 block text-sm font-medium text-[#374151]">Descripción</span>
                <textarea
                  value={formData.descripcion}
                  onChange={(e) => setFormData({ ...formData, descripcion: e.target.value })}
                  rows={3}
                  className="w-full rounded-xl border border-[#dbe3ee] bg-[#f8fafc] px-3 py-2.5 text-sm text-[#1f2937] outline-none focus:border-[#1a7eff]"
                />
              </label>

            </div>

            <div className="mt-6 flex justify-end gap-3">
              <button
                onClick={() => setIsModalOpen(false)}
                className="rounded-xl border border-[#dbe3ee] bg-white px-4 py-2.5 text-sm font-semibold text-[#374151] hover:bg-[#f8fafc]"
              >
                Cancelar
              </button>
              <button
                onClick={handleSave}
                className="rounded-xl bg-[#1a7eff] px-4 py-2.5 text-sm font-semibold text-white hover:bg-[#146be7]"
              >
                Guardar cambios
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
