import { useEffect, useState } from "react";
import { Client, UsuarioAsociable } from "../types";
import { createClient, deleteClient, listClients, listUsuariosAsociables, updateClient } from "../lib/clientesApi";
import MultiSelect from "./MultiSelect";

const EMPTY: Omit<Client, "id"> = { nombre: "", tipo: "Física", direccion: "", cuentaAcreditar: "", correo: "", usuarios: [] };

export default function ClientesModule() {
  const [clients, setClients] = useState<Client[]>([]);
  const [usuarios, setUsuarios] = useState<UsuarioAsociable[]>([]);
  const [loading, setLoading] = useState(true);
  const [form, setForm] = useState<Omit<Client, "id">>(EMPTY);
  const [editId, setEditId] = useState<Client["id"] | null>(null);
  const [errors, setErrors] = useState<Partial<Record<keyof Client, string>>>({});
  const [deleteConfirm, setDeleteConfirm] = useState<Client["id"] | null>(null);
  const [toast, setToast] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([listClients(), listUsuariosAsociables()])
      .then(([clientesRes, usuariosRes]) => {
        setClients(clientesRes);
        setUsuarios(usuariosRes);
      })
      .catch(() => showToast("No se pudo conectar con el backend."))
      .finally(() => setLoading(false));
  }, []);

  const showToast = (msg: string) => {
    setToast(msg);
    setTimeout(() => setToast(null), 3000);
  };

  const usuarioLabel = (id: number) => {
    const u = usuarios.find(x => x.id === id);
    return u ? `${u.nombre} (${u.username})` : String(id);
  };

  const validate = () => {
    const e: Partial<Record<keyof Client, string>> = {};
    if (!form.nombre.trim()) e.nombre = "Campo obligatorio";
    if (!form.direccion.trim()) e.direccion = "Campo obligatorio";
    if (!form.cuentaAcreditar.trim()) e.cuentaAcreditar = "Campo obligatorio";
    if (!form.correo.trim()) e.correo = "Campo obligatorio";
    else if (!/\S+@\S+\.\S+/.test(form.correo)) e.correo = "Correo inválido";
    setErrors(e);
    return Object.keys(e).length === 0;
  };

  const handleSave = async () => {
    if (!validate()) return;
    try {
      if (editId !== null) {
        const updated = await updateClient(editId, form);
        setClients(clients.map(c => c.id === editId ? updated : c));
        showToast("Cliente modificado correctamente.");
      } else {
        const created = await createClient(form);
        setClients([...clients, created]);
        showToast("Cliente creado correctamente.");
      }
      setForm(EMPTY);
      setEditId(null);
      setErrors({});
    } catch {
      showToast("No se pudo guardar el cliente.");
    }
  };

  const handleEdit = (c: Client) => {
    setForm({ nombre: c.nombre, tipo: c.tipo, direccion: c.direccion, cuentaAcreditar: c.cuentaAcreditar, correo: c.correo, usuarios: c.usuarios });
    setEditId(c.id);
    setErrors({});
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const handleDelete = async (id: Client["id"]) => {
    try {
      await deleteClient(id);
      setClients(clients.filter(c => c.id !== id));
      showToast("Cliente eliminado.");
    } catch {
      showToast("No se pudo eliminar el cliente.");
    } finally {
      setDeleteConfirm(null);
    }
  };

  const handleCancel = () => {
    setForm(EMPTY);
    setEditId(null);
    setErrors({});
  };

  const field = (key: keyof typeof form, label: string, placeholder: string, required = true, type = "text") => (
    <div>
      <label className="block text-sm font-medium text-[#374151] mb-1">
        {label}{required && <span className="text-red-500 ml-0.5">*</span>}
      </label>
      <input
        type={type}
        value={form[key] as string}
        onChange={e => { setForm({ ...form, [key]: e.target.value }); if (errors[key]) setErrors({ ...errors, [key]: undefined }); }}
        placeholder={placeholder}
        className={`w-full px-3 py-2.5 rounded-lg border text-sm focus:outline-none focus:ring-2 focus:ring-[#1a7eff] transition ${errors[key] ? "border-red-400 bg-red-50" : "border-[#e2e8f0]"}`}
      />
      {errors[key] && <p className="text-xs text-red-500 mt-1">{errors[key]}</p>}
    </div>
  );

  return (
    <div className="space-y-6 relative">
      {/* Toast */}
      {toast && (
        <div className="fixed top-5 right-5 z-50 bg-[#1a7eff] text-white text-sm font-medium px-4 py-3 rounded-xl shadow-lg flex items-center gap-2 animate-[fadeIn_0.2s_ease]">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.5"><polyline points="20 6 9 17 4 12"/></svg>
          {toast}
        </div>
      )}

      {/* Form */}
      <div className="bg-white rounded-2xl border border-[#e2e8f0] p-6 shadow-sm">
        <h2 className="text-base font-semibold text-[#1a202c] mb-1">
          {editId !== null ? "Modificar Cliente" : "Crear Cliente Nuevo"}
        </h2>
        <p className="text-xs text-[#718096] mb-5">
          {editId !== null ? "Edita los datos del cliente seleccionado." : "Completa los campos para registrar un nuevo cliente."}
          <span className="text-red-500"> * Campos obligatorios</span>
        </p>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {field("nombre", "Nombre", "Ej. Empresa XYZ S.A.")}
          <div>
            <label className="block text-sm font-medium text-[#374151] mb-1">
              Tipo<span className="text-red-500 ml-0.5">*</span>
            </label>
            <select
              value={form.tipo}
              onChange={e => setForm({ ...form, tipo: e.target.value as "Jurídica" | "Física" })}
              className="w-full px-3 py-2.5 rounded-lg border border-[#e2e8f0] text-sm focus:outline-none focus:ring-2 focus:ring-[#1a7eff] transition bg-white"
            >
              <option value="Jurídica">Jurídica</option>
              <option value="Física">Física</option>
            </select>
          </div>
          {field("direccion", "Dirección", "Ej. Av. Principal 1234, Ciudad")}
          {field("cuentaAcreditar", "Cuenta a Acreditar", "PY38-XXXX-XXXX-XXXX-XXXX-XXXX-X")}
          {field("correo", "Correo Electrónico", "contacto@empresa.com", true, "email")}
          <div>
            <label className="block text-sm font-medium text-[#374151] mb-1">Usuarios a Asociar</label>
            <MultiSelect
              options={usuarios.map(u => ({ value: String(u.id), label: `${u.nombre} (${u.username})` }))}
              selected={form.usuarios.map(String)}
              onChange={values => setForm({ ...form, usuarios: values.map(Number) })}
              placeholder="Ninguno (opcional)"
            />
          </div>
        </div>

        <div className="flex gap-3 mt-5 pt-4 border-t border-[#f1f5f9]">
          <button
            onClick={handleSave}
            className="bg-[#1a7eff] hover:bg-[#1565d8] text-white font-semibold px-5 py-2.5 rounded-lg text-sm transition-colors flex items-center gap-2"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/><polyline points="17 21 17 13 7 13 7 21"/><polyline points="7 3 7 8 15 8"/></svg>
            {editId !== null ? "Guardar Cambios" : "Guardar Cliente"}
          </button>
          {editId !== null && (
            <button
              onClick={handleCancel}
              className="border border-[#e2e8f0] text-[#374151] hover:bg-[#f8fafc] font-medium px-5 py-2.5 rounded-lg text-sm transition-colors"
            >
              Cancelar
            </button>
          )}
        </div>
      </div>

      {/* Table */}
      <div className="bg-white rounded-2xl border border-[#e2e8f0] shadow-sm overflow-hidden">
        <div className="px-6 py-4 border-b border-[#f1f5f9] flex items-center justify-between">
          <div>
            <h2 className="text-base font-semibold text-[#1a202c]">Gestión de Clientes</h2>
            <p className="text-xs text-[#718096] mt-0.5">{clients.length} cliente{clients.length !== 1 ? "s" : ""} registrado{clients.length !== 1 ? "s" : ""}</p>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="bg-[#f8fafc]">
                <th className="text-left text-xs font-semibold text-[#718096] uppercase tracking-wide px-6 py-3">Nombre del Cliente</th>
                <th className="text-left text-xs font-semibold text-[#718096] uppercase tracking-wide px-4 py-3">Tipo</th>
                <th className="text-left text-xs font-semibold text-[#718096] uppercase tracking-wide px-4 py-3">Usuarios Asociados</th>
                <th className="text-right text-xs font-semibold text-[#718096] uppercase tracking-wide px-6 py-3">Acciones</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#f1f5f9]">
              {loading && (
                <tr>
                  <td colSpan={4} className="text-center text-sm text-[#9ca3af] py-12">
                    Cargando clientes...
                  </td>
                </tr>
              )}
              {!loading && clients.length === 0 && (
                <tr>
                  <td colSpan={4} className="text-center text-sm text-[#9ca3af] py-12">
                    No hay clientes registrados.
                  </td>
                </tr>
              )}
              {clients.map(c => (
                <tr key={c.id} className={`hover:bg-[#f8fafc] transition-colors ${editId === c.id ? "bg-[#f0f7ff]" : ""}`}>
                  <td className="px-6 py-4">
                    <p className="text-sm font-medium text-[#1a202c]">{c.nombre}</p>
                    <p className="text-xs text-[#9ca3af]">{c.correo}</p>
                  </td>
                  <td className="px-4 py-4">
                    <span className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium ${c.tipo === "Jurídica" ? "bg-purple-100 text-purple-700" : "bg-sky-100 text-sky-700"}`}>
                      {c.tipo}
                    </span>
                  </td>
                  <td className="px-4 py-4">
                    {c.usuarios.length > 0
                      ? <span className="text-sm text-[#374151]">{c.usuarios.map(usuarioLabel).join(", ")}</span>
                      : <span className="text-xs text-[#9ca3af]">—</span>
                    }
                  </td>
                  <td className="px-6 py-4">
                    <div className="flex items-center justify-end gap-2">
                      <button
                        onClick={() => handleEdit(c)}
                        className="flex items-center gap-1.5 text-xs font-medium text-[#1a7eff] bg-[#e8f1ff] hover:bg-[#d0e4ff] px-3 py-1.5 rounded-lg transition-colors"
                      >
                        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
                        Modificar
                      </button>
                      <button
                        onClick={() => setDeleteConfirm(c.id)}
                        className="flex items-center gap-1.5 text-xs font-medium text-red-600 bg-red-50 hover:bg-red-100 px-3 py-1.5 rounded-lg transition-colors"
                      >
                        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2"/></svg>
                        Borrar
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Delete modal */}
      {deleteConfirm !== null && (
        <div className="fixed inset-0 bg-black/30 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl shadow-2xl border border-[#e2e8f0] p-6 w-full max-w-sm">
            <div className="w-12 h-12 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#ef4444" strokeWidth="2.5"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2"/></svg>
            </div>
            <h3 className="text-base font-bold text-[#1a202c] text-center mb-1">¿Confirmar eliminación?</h3>
            <p className="text-sm text-[#718096] text-center mb-5">Esta acción no se puede deshacer.</p>
            <div className="flex gap-3">
              <button onClick={() => setDeleteConfirm(null)} className="flex-1 border border-[#e2e8f0] text-[#374151] hover:bg-[#f8fafc] font-medium py-2.5 rounded-lg text-sm transition-colors">Cancelar</button>
              <button onClick={() => handleDelete(deleteConfirm)} className="flex-1 bg-red-500 hover:bg-red-600 text-white font-semibold py-2.5 rounded-lg text-sm transition-colors">Eliminar</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
