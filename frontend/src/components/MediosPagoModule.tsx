import { useEffect, useState } from "react";
import {
  actualizarMedioPago,
  borrarMedioPago,
  crearMedioPago,
  listarMediosPago,
  type MedioPago,
  type TipoMedioPago,
} from "../lib/mediosPagoApi";

// Los medios de pago salen de la base (app `medios_pago`). El backend decide
// qué ve cada rol: un cliente solo los suyos, administrador y cajero todos.
// La lista de tipos también viene del backend (MedioPago.TIPO_CHOICES), así no
// se duplica el catálogo en el navegador.

const formVacio = { tipo: "", alias: "", numero: "", banco: "", activo: true };

export default function MediosPagoModule() {
  const [medios, setMedios] = useState<MedioPago[]>([]);
  const [tipos, setTipos] = useState<TipoMedioPago[]>([]);
  const [cargando, setCargando] = useState(true);
  const [toast, setToast] = useState<string | null>(null);
  const [modalOpen, setModalOpen] = useState(false);
  const [editandoId, setEditandoId] = useState<number | null>(null);
  const [form, setForm] = useState(formVacio);

  const avisar = (mensaje: string) => {
    setToast(mensaje);
    setTimeout(() => setToast(null), 2800);
  };

  const recargar = async () => {
    try {
      const datos = await listarMediosPago();
      setMedios(datos.medios);
      setTipos(datos.tipos);
    } catch (e) {
      avisar(e instanceof Error ? e.message : "No se pudieron cargar los medios de pago.");
    } finally {
      setCargando(false);
    }
  };

  useEffect(() => {
    void recargar();
  }, []);

  const openAddModal = () => {
    setEditandoId(null);
    setForm({ ...formVacio, tipo: tipos[0]?.valor ?? "" });
    setModalOpen(true);
  };

  const openEditModal = (medio: MedioPago) => {
    setEditandoId(medio.id);
    setForm({
      tipo: medio.tipo,
      alias: medio.alias,
      numero: medio.numero,
      banco: medio.banco,
      activo: medio.activo,
    });
    setModalOpen(true);
  };

  const handleSave = async () => {
    if (!form.alias || !form.tipo) {
      avisar("El alias y el tipo son obligatorios.");
      return;
    }
    try {
      if (editandoId !== null) {
        await actualizarMedioPago(editandoId, form);
        avisar("Medio de pago actualizado.");
      } else {
        await crearMedioPago(form);
        avisar("Medio de pago agregado.");
      }
      await recargar();
      setModalOpen(false);
    } catch (e) {
      avisar(e instanceof Error ? e.message : "No se pudo guardar el medio de pago.");
    }
  };

  const toggleActivo = async (medio: MedioPago) => {
    try {
      await actualizarMedioPago(medio.id, { activo: !medio.activo });
      await recargar();
      avisar(`${medio.alias} ${medio.activo ? "desactivado" : "activado"}.`);
    } catch (e) {
      avisar(e instanceof Error ? e.message : "No se pudo cambiar el estado.");
    }
  };

  const eliminar = async (medio: MedioPago) => {
    try {
      await borrarMedioPago(medio.id);
      await recargar();
      avisar(`${medio.alias} eliminado.`);
    } catch (e) {
      avisar(e instanceof Error ? e.message : "No se pudo eliminar el medio de pago.");
    }
  };

  return (
    <div className="space-y-6">
      <div className="rounded-3xl border border-[#dbe3ee] bg-white p-6 shadow-sm">
        <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="text-sm font-medium text-[#64748b]">Administración</p>
            <h2 className="text-2xl font-bold tracking-tight text-[#0f172a]">Medios de pago</h2>
          </div>
          <button
            onClick={openAddModal}
            className="rounded-xl bg-[#1a7eff] px-4 py-2.5 text-sm font-semibold text-white hover:bg-[#146be7]"
          >
            Agregar
          </button>
        </div>

        <div className="overflow-x-auto rounded-2xl border border-[#e2e8f0]">
          <table className="min-w-full border-collapse bg-white text-left text-sm text-[#1f2937]">
            <thead className="bg-[#f8fafc] text-[#475569]">
              <tr>
                <th className="px-4 py-3 font-semibold">Alias</th>
                <th className="px-4 py-3 font-semibold">Tipo</th>
                <th className="px-4 py-3 font-semibold">Número / Cuenta</th>
                <th className="px-4 py-3 font-semibold">Banco o proveedor</th>
                <th className="px-4 py-3 font-semibold">Titular</th>
                <th className="px-4 py-3 font-semibold">Estado</th>
                <th className="px-4 py-3 text-center font-semibold">Acciones</th>
              </tr>
            </thead>
            <tbody>
              {cargando && (
                <tr>
                  <td colSpan={7} className="px-4 py-6 text-center text-[#64748b]">
                    Cargando medios de pago…
                  </td>
                </tr>
              )}

              {!cargando && medios.length === 0 && (
                <tr>
                  <td colSpan={7} className="px-4 py-6 text-center text-[#64748b]">
                    Todavía no hay medios de pago cargados. Usá «Agregar» para crear el primero.
                  </td>
                </tr>
              )}

              {medios.map((medio) => (
                <tr key={medio.id} className="border-t border-[#edf2f7] bg-white hover:bg-[#f8fafc]">
                  <td className="px-4 py-3 font-medium text-[#0f172a]">{medio.alias}</td>
                  <td className="px-4 py-3 text-[#475569]">{medio.tipoTexto}</td>
                  <td className="px-4 py-3 tabular-nums text-[#475569]">{medio.numero || "—"}</td>
                  <td className="px-4 py-3 text-[#475569]">{medio.banco || "—"}</td>
                  <td className="px-4 py-3 text-[#475569]">{medio.usuario}</td>
                  <td className="px-4 py-3">
                    <span
                      className={`rounded-full px-2.5 py-1 text-xs font-semibold ${
                        medio.activo ? "bg-green-100 text-green-700" : "bg-slate-200 text-slate-600"
                      }`}
                    >
                      {medio.activo ? "Activo" : "Inactivo"}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex flex-wrap justify-center gap-2">
                      <button
                        onClick={() => openEditModal(medio)}
                        className="rounded-lg bg-[#eaf3ff] px-3 py-1.5 text-xs font-semibold text-[#1a7eff] hover:bg-[#dfeeff]"
                      >
                        Modificar
                      </button>
                      <button
                        onClick={() => toggleActivo(medio)}
                        className="rounded-lg bg-[#f1f5f9] px-3 py-1.5 text-xs font-semibold text-[#475569] hover:bg-[#e2e8f0]"
                      >
                        {medio.activo ? "Desactivar" : "Activar"}
                      </button>
                      <button
                        onClick={() => eliminar(medio)}
                        className="rounded-lg bg-[#fdeceb] px-3 py-1.5 text-xs font-semibold text-[#c0392b] hover:bg-[#fbdedb]"
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
      </div>

      {modalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 px-4">
          <div className="w-full max-w-xl rounded-2xl bg-white p-6 shadow-2xl">
            <h3 className="text-2xl font-bold text-[#0f172a]">
              {editandoId !== null ? "Modificar medio de pago" : "Nuevo medio de pago"}
            </h3>

            <div className="mt-5 grid gap-4 md:grid-cols-2">
              <label className="block">
                <span className="mb-2 block text-sm font-medium text-[#374151]">Tipo</span>
                <select
                  value={form.tipo}
                  onChange={(e) => setForm({ ...form, tipo: e.target.value })}
                  className="w-full rounded-xl border border-[#dbe3ee] bg-[#f8fafc] px-3 py-2.5 text-sm text-[#1f2937] outline-none focus:border-[#1a7eff]"
                >
                  <option value="">Elegí un tipo…</option>
                  {tipos.map((t) => (
                    <option key={t.valor} value={t.valor}>
                      {t.texto}
                    </option>
                  ))}
                </select>
              </label>

              <label className="block">
                <span className="mb-2 block text-sm font-medium text-[#374151]">Alias</span>
                <input
                  value={form.alias}
                  onChange={(e) => setForm({ ...form, alias: e.target.value })}
                  placeholder="Mi Visa ITAU"
                  className="w-full rounded-xl border border-[#dbe3ee] bg-[#f8fafc] px-3 py-2.5 text-sm text-[#1f2937] outline-none focus:border-[#1a7eff]"
                />
              </label>

              <label className="block">
                <span className="mb-2 block text-sm font-medium text-[#374151]">Número o cuenta</span>
                <input
                  value={form.numero}
                  onChange={(e) => setForm({ ...form, numero: e.target.value })}
                  placeholder="**** **** **** 4521"
                  className="w-full rounded-xl border border-[#dbe3ee] bg-[#f8fafc] px-3 py-2.5 text-sm text-[#1f2937] outline-none focus:border-[#1a7eff]"
                />
              </label>

              <label className="block">
                <span className="mb-2 block text-sm font-medium text-[#374151]">Banco o proveedor</span>
                <input
                  value={form.banco}
                  onChange={(e) => setForm({ ...form, banco: e.target.value })}
                  placeholder="Banco Itaú"
                  className="w-full rounded-xl border border-[#dbe3ee] bg-[#f8fafc] px-3 py-2.5 text-sm text-[#1f2937] outline-none focus:border-[#1a7eff]"
                />
              </label>

              <label className="flex items-center gap-2 md:col-span-2">
                <input
                  type="checkbox"
                  checked={form.activo}
                  onChange={(e) => setForm({ ...form, activo: e.target.checked })}
                  className="h-4 w-4"
                />
                <span className="text-sm font-medium text-[#374151]">Medio de pago activo</span>
              </label>
            </div>

            <div className="mt-6 flex justify-end gap-3">
              <button
                onClick={() => setModalOpen(false)}
                className="rounded-xl border border-[#dbe3ee] bg-white px-4 py-2.5 text-sm font-semibold text-[#374151] hover:bg-[#f8fafc]"
              >
                Cancelar
              </button>
              <button
                onClick={handleSave}
                className="rounded-xl bg-[#1a7eff] px-4 py-2.5 text-sm font-semibold text-white hover:bg-[#146be7]"
              >
                Guardar
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
