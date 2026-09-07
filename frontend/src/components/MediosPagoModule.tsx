import { useState } from "react";
import { getPaymentMethods, PaymentMethodOption, setPaymentMethods } from "../lib/paymentMethods";

const emptyForm = { id: "", medio: "", estado: "Activo" as "Activo" | "Inactivo" };

export default function MediosPagoModule() {
  const [methods, setMethods] = useState<PaymentMethodOption[]>(() => getPaymentMethods());
  const [toast, setToast] = useState<string | null>(null);
  const [modalOpen, setModalOpen] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [form, setForm] = useState(emptyForm);

  const persistAndNotify = (nextMethods: PaymentMethodOption[], message: string) => {
    setMethods(nextMethods);
    setPaymentMethods(nextMethods);
    setToast(message);
    setTimeout(() => setToast(null), 2600);
  };

  const openAddModal = () => {
    setForm({ ...emptyForm, id: "", medio: "", estado: "Activo" });
    setIsEditing(false);
    setModalOpen(true);
  };

  const openEditModal = (method: PaymentMethodOption) => {
    setForm({ id: method.id, medio: method.medio, estado: method.estado });
    setIsEditing(true);
    setModalOpen(true);
  };

  const closeModal = () => {
    setModalOpen(false);
    setForm(emptyForm);
    setIsEditing(false);
  };

  const handleSave = () => {
    const name = form.medio.trim();
    if (!name) {
      setToast("El nombre del medio de pago no puede estar vacío.");
      setTimeout(() => setToast(null), 2600);
      return;
    }

    if (isEditing && form.id) {
      const nextMethods = methods.map((method) =>
        method.id === form.id ? { ...method, medio: name, estado: form.estado } : method,
      );

      persistAndNotify(nextMethods, `El medio de pago ${name} se actualizó correctamente.`);
    } else {
      const newMethod: PaymentMethodOption = {
        id: crypto.randomUUID(),
        medio: name,
        estado: form.estado,
      };

      const nextMethods = [...methods, newMethod];
      persistAndNotify(nextMethods, `El medio de pago ${name} se agregó correctamente.`);
    }

    closeModal();
  };

  const handleDelete = (id: string) => {
    const target = methods.find((method) => method.id === id);
    const nextMethods = methods.filter((method) => method.id !== id);
    persistAndNotify(nextMethods, `El medio de pago ${target?.medio ?? "seleccionado"} fue eliminado.`);
    closeModal();
  };

  const handleToggle = (id: string, mediumName: string) => {
    const nextMethods = methods.map((method) =>
      method.id === id
        ? { ...method, estado: method.estado === "Activo" ? "Inactivo" : "Activo" }
        : method,
    );

    persistAndNotify(nextMethods, `El medio de pago ${mediumName} ha sido cambiado a ${nextMethods.find((method) => method.id === id)?.estado ?? "Activo"}.`);
  };

  return (
    <div className="space-y-6">
      <div className="rounded-3xl border border-[#dbe3ee] bg-white p-6 shadow-sm">
        <div className="mb-5 flex items-center justify-between gap-4">
          <div>
            <p className="text-sm font-medium text-[#64748b]">Administración</p>
            <h2 className="text-2xl font-bold tracking-tight text-[#0f172a]">Medios de Pago</h2>
          </div>
          <button
            onClick={openAddModal}
            className="rounded-xl bg-[#1a7eff] px-4 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-[#176ae6]"
          >
            Agregar
          </button>
        </div>

        <div className="overflow-hidden rounded-2xl border border-[#e2e8f0]">
          <table className="min-w-full border-collapse bg-white text-left text-sm text-[#1f2937]">
            <thead className="bg-[#f8fafc] text-[#475569]">
              <tr>
                <th className="px-4 py-3 font-semibold">Medios de Pago</th>
                <th className="px-4 py-3 font-semibold">Estado</th>
                <th className="px-4 py-3 text-center font-semibold">Acciones</th>
              </tr>
            </thead>
            <tbody>
              {methods.map((method) => (
                <tr key={method.id} className="border-t border-[#edf2f7] bg-white hover:bg-[#f8fafc]">
                  <td className="px-4 py-3 font-medium text-[#0f172a]">{method.medio}</td>
                  <td className="px-4 py-3">
                    <span
                      className={`inline-flex items-center rounded-full px-2.5 py-1 text-xs font-semibold ${
                        method.estado === "Activo"
                          ? "bg-green-100 text-green-700"
                          : "bg-red-100 text-red-700"
                      }`}
                    >
                      {method.estado}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex justify-center gap-2">
                      <button
                        onClick={() => openEditModal(method)}
                        className="rounded-lg bg-[#eaf3ff] px-3 py-1.5 text-xs font-semibold text-[#1a7eff] transition hover:bg-[#dfeeff]"
                      >
                        Modificar
                      </button>
                      <button
                        onClick={() => handleToggle(method.id, method.medio)}
                        className={`rounded-lg px-3 py-1.5 text-xs font-semibold transition ${
                          method.estado === "Activo"
                            ? "bg-[#eaf3ff] text-[#1a7eff] hover:bg-[#dfeeff]"
                            : "bg-[#fef2f2] text-red-600 hover:bg-[#fee2e2]"
                        }`}
                      >
                        {method.estado === "Activo" ? "Desactivar" : "Activar"}
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
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/35 p-4">
          <div className="w-full max-w-md rounded-2xl border border-[#e2e8f0] bg-white p-6 shadow-2xl">
            <div className="mb-4">
              <p className="text-sm font-medium text-[#64748b]">{isEditing ? "Editar" : "Agregar"}</p>
              <h3 className="text-xl font-bold text-[#0f172a]">Medio de pago</h3>
            </div>

            <div className="space-y-4">
              <div>
                <label className="mb-1 block text-sm font-medium text-[#374151]">Nombre</label>
                <input
                  value={form.medio}
                  onChange={(e) => setForm((prev) => ({ ...prev, medio: e.target.value }))}
                  className="w-full rounded-xl border border-[#dbe3ee] bg-[#f8fafc] px-3 py-2.5 text-sm text-[#0f172a] outline-none transition focus:border-[#1a7eff]"
                  placeholder="Ej: Efectivo, Cheque, etc."
                />
              </div>

              <div>
                <label className="mb-1 block text-sm font-medium text-[#374151]">Estado</label>
                <select
                  value={form.estado}
                  onChange={(e) => setForm((prev) => ({ ...prev, estado: e.target.value as "Activo" | "Inactivo" }))}
                  className="w-full rounded-xl border border-[#dbe3ee] bg-[#f8fafc] px-3 py-2.5 text-sm text-[#0f172a] outline-none transition focus:border-[#1a7eff]"
                >
                  <option value="Activo">Activo</option>
                  <option value="Inactivo">Inactivo</option>
                </select>
              </div>
            </div>

            <div className="mt-6 flex items-center justify-between gap-3">
              {isEditing && (
                <button
                  onClick={() => handleDelete(form.id)}
                  className="rounded-xl border border-red-200 bg-red-50 px-3 py-2 text-sm font-semibold text-red-600 hover:bg-red-100"
                >
                  Borrar
                </button>
              )}

              <div className="ml-auto flex gap-3">
                <button
                  onClick={closeModal}
                  className="rounded-xl border border-[#dbe3ee] bg-white px-3 py-2 text-sm font-semibold text-[#475569] hover:bg-[#f8fafc]"
                >
                  Cancelar
                </button>
                <button
                  onClick={handleSave}
                  className="rounded-xl bg-[#1a7eff] px-3 py-2 text-sm font-semibold text-white hover:bg-[#176ae6]"
                >
                  Guardar
                </button>
              </div>
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
