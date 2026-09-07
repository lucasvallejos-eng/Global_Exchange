import { useState } from "react";

type ClienteTipo = "Minorista" | "Mayorista" | "VIP" | "Preferencial";

type ClientePorcentaje = {
  id: number;
  tipo: ClienteTipo;
  venta: number;
  compra: number;
  descripcion: string;
};

const INITIAL_ROWS: ClientePorcentaje[] = [
  { id: 1, tipo: "Minorista", venta: 0, compra: 0, descripcion: "Precio de mercado base sin variación." },
  { id: 2, tipo: "Mayorista", venta: -2, compra: 2, descripcion: "Descuento preferencial para volumen de compra." },
  { id: 3, tipo: "VIP", venta: -5, compra: 4, descripcion: "Beneficio exclusivo para clientes premium." },
  { id: 4, tipo: "Preferencial", venta: -1.5, compra: 1, descripcion: "Condiciones promocionales del mes." },
];

export default function PorcentajesModule() {
  const [rows, setRows] = useState<ClientePorcentaje[]>(INITIAL_ROWS);
  const [selectedId, setSelectedId] = useState<number>(INITIAL_ROWS[0].id);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [toast, setToast] = useState<string | null>(null);

  const selectedRow = rows.find((row) => row.id === selectedId) ?? rows[0];

  const [formData, setFormData] = useState({
    tipo: selectedRow.tipo,
    venta: String(selectedRow.venta),
    compra: String(selectedRow.compra),
    descripcion: selectedRow.descripcion,
  });

  const openEdit = (row: ClientePorcentaje) => {
    setSelectedId(row.id);
    setFormData({
      tipo: row.tipo,
      venta: String(row.venta),
      compra: String(row.compra),
      descripcion: row.descripcion,
    });
    setIsModalOpen(true);
  };

  const handleSave = () => {
    setRows((prev) =>
      prev.map((row) =>
        row.id === selectedId
          ? {
              ...row,
              tipo: formData.tipo,
              venta: Number(formData.venta),
              compra: Number(formData.compra),
              descripcion: formData.descripcion,
            }
          : row,
      ),
    );

    setToast(`Porcentajes actualizados correctamente para la categoría ${formData.tipo}.`);
    setIsModalOpen(false);
    setTimeout(() => setToast(null), 2400);
  };

  return (
    <div className="space-y-6">
      <div className="rounded-3xl border border-[#dbe3ee] bg-white p-6 shadow-sm">
        <div className="mb-5">
          <p className="text-sm font-medium text-[#64748b]">Administración</p>
          <h2 className="text-2xl font-bold tracking-tight text-[#0f172a]">Márgenes y porcentajes</h2>
        </div>

        <div className="overflow-hidden rounded-2xl border border-[#e2e8f0]">
          <table className="min-w-full border-collapse bg-white text-left text-sm text-[#1f2937]">
            <thead className="bg-[#f8fafc] text-[#475569]">
              <tr>
                <th className="px-4 py-3 font-semibold">Tipo de Cliente</th>
                <th className="px-4 py-3 font-semibold">Porcentaje de Venta</th>
                <th className="px-4 py-3 font-semibold">Porcentaje de Compra</th>
                <th className="px-4 py-3 text-center font-semibold">Acciones</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr
                  key={row.id}
                  onClick={() => setSelectedId(row.id)}
                  className={`border-t border-[#edf2f7] transition ${selectedId === row.id ? "bg-[#f0f7ff]" : "bg-white hover:bg-[#f8fafc]"}`}
                >
                  <td className="px-4 py-3 font-medium text-[#0f172a]">{row.tipo}</td>
                  <td className="px-4 py-3 text-[#0f172a]">
                    <span className={row.venta >= 0 ? "text-green-700" : "text-red-600"}>
                      {row.venta > 0 ? "+" : ""}{row.venta}%
                    </span>
                  </td>
                  <td className="px-4 py-3 text-[#0f172a]">
                    <span className={row.compra >= 0 ? "text-green-700" : "text-red-600"}>
                      {row.compra > 0 ? "+" : ""}{row.compra}%
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex justify-center">
                      <button
                        onClick={(event) => {
                          event.stopPropagation();
                          openEdit(row);
                        }}
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
              <label className="block md:col-span-2">
                <span className="mb-2 block text-sm font-medium text-[#374151]">Tipo de Cliente</span>
                <input
                  value={formData.tipo}
                  readOnly
                  className="w-full rounded-xl border border-[#dbe3ee] bg-[#f8fafc] px-3 py-2.5 text-sm text-[#1f2937] outline-none"
                />
              </label>

              <label className="block">
                <span className="mb-2 block text-sm font-medium text-[#374151]">Margen / Porcentaje de Venta (%)</span>
                <input
                  type="number"
                  step="0.1"
                  value={formData.venta}
                  onChange={(event) => setFormData({ ...formData, venta: event.target.value })}
                  className="w-full rounded-xl border border-[#dbe3ee] bg-[#f8fafc] px-3 py-2.5 text-sm text-[#1f2937] outline-none focus:border-[#1a7eff]"
                />
              </label>

              <label className="block">
                <span className="mb-2 block text-sm font-medium text-[#374151]">Margen / Porcentaje de Compra (%)</span>
                <input
                  type="number"
                  step="0.1"
                  value={formData.compra}
                  onChange={(event) => setFormData({ ...formData, compra: event.target.value })}
                  className="w-full rounded-xl border border-[#dbe3ee] bg-[#f8fafc] px-3 py-2.5 text-sm text-[#1f2937] outline-none focus:border-[#1a7eff]"
                />
              </label>

              <label className="block md:col-span-2">
                <span className="mb-2 block text-sm font-medium text-[#374151]">Descripción / Regla explicativa</span>
                <textarea
                  value={formData.descripcion}
                  onChange={(event) => setFormData({ ...formData, descripcion: event.target.value })}
                  rows={4}
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
                Guardar Cambios
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
