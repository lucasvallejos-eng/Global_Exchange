import { useEffect, useState } from "react";
import {
  actualizarSegmento,
  crearSegmento,
  listarSegmentos,
  type Segmento,
} from "../lib/comisionesApi";

// Los segmentos y su porcentaje de comisión salen de la base (app `comisiones`).
// El modelo guarda UN porcentaje por segmento, no dos: la maqueta original
// dibujaba columnas de venta y compra que no existían en ninguna tabla.

const formVacio = { nombre: "", porcentaje: "", descripcion: "", activo: true };

export default function PorcentajesModule() {
  const [rows, setRows] = useState<Segmento[]>([]);
  const [cargando, setCargando] = useState(true);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editandoId, setEditandoId] = useState<number | null>(null);
  const [toast, setToast] = useState<string | null>(null);
  const [formData, setFormData] = useState(formVacio);

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

  const openAdd = () => {
    setEditandoId(null);
    setFormData(formVacio);
    setIsModalOpen(true);
  };

  const openEdit = (row: Segmento) => {
    setEditandoId(row.id);
    setFormData({
      nombre: row.nombre,
      porcentaje: String(row.porcentajeComision),
      descripcion: row.descripcion,
      activo: row.activo,
    });
    setIsModalOpen(true);
  };

  const handleSave = async () => {
    if (!formData.nombre || formData.porcentaje === "") {
      avisar("El nombre y el porcentaje son obligatorios.");
      return;
    }

    const datos = {
      nombre: formData.nombre,
      porcentajeComision: Number(formData.porcentaje),
      descripcion: formData.descripcion,
      activo: formData.activo,
    };

    try {
      if (editandoId !== null) {
        await actualizarSegmento(editandoId, datos);
        avisar(`Porcentaje actualizado para ${formData.nombre}.`);
      } else {
        await crearSegmento(datos);
        avisar(`Segmento ${formData.nombre} creado.`);
      }
      await recargar();
      setIsModalOpen(false);
    } catch (e) {
      avisar(e instanceof Error ? e.message : "No se pudo guardar el segmento.");
    }
  };

  const toggleActivo = async (row: Segmento) => {
    try {
      await actualizarSegmento(row.id, { activo: !row.activo });
      await recargar();
      avisar(`Segmento ${row.nombre} ${row.activo ? "desactivado" : "activado"}.`);
    } catch (e) {
      avisar(e instanceof Error ? e.message : "No se pudo cambiar el estado.");
    }
  };

  return (
    <div className="space-y-6">
      <div className="rounded-3xl border border-[#dbe3ee] bg-white p-6 shadow-sm">
        <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="text-sm font-medium text-[#64748b]">Administración</p>
            <h2 className="text-2xl font-bold tracking-tight text-[#0f172a]">
              Porcentajes de comisión por segmento
            </h2>
          </div>
          <button
            onClick={openAdd}
            className="rounded-xl bg-[#1a7eff] px-4 py-2.5 text-sm font-semibold text-white hover:bg-[#146be7]"
          >
            Agregar segmento
          </button>
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
                      <button
                        onClick={() => toggleActivo(row)}
                        className="rounded-lg bg-[#f1f5f9] px-3 py-1.5 text-xs font-semibold text-[#475569] hover:bg-[#e2e8f0]"
                      >
                        {row.activo ? "Desactivar" : "Activar"}
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
            <h3 className="text-2xl font-bold text-[#0f172a]">
              {editandoId !== null ? "Modificar segmento" : "Nuevo segmento"}
            </h3>

            <div className="mt-5 grid gap-4 md:grid-cols-2">
              <label className="block">
                <span className="mb-2 block text-sm font-medium text-[#374151]">Nombre del segmento</span>
                <input
                  value={formData.nombre}
                  onChange={(e) => setFormData({ ...formData, nombre: e.target.value })}
                  placeholder="VIP"
                  className="w-full rounded-xl border border-[#dbe3ee] bg-[#f8fafc] px-3 py-2.5 text-sm text-[#1f2937] outline-none focus:border-[#1a7eff]"
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

              <label className="flex items-center gap-2 md:col-span-2">
                <input
                  type="checkbox"
                  checked={formData.activo}
                  onChange={(e) => setFormData({ ...formData, activo: e.target.checked })}
                  className="h-4 w-4"
                />
                <span className="text-sm font-medium text-[#374151]">Segmento activo</span>
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
