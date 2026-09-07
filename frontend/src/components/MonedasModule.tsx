import { useMemo, useState } from "react";

type CurrencyState = "Activo" | "Inactivo";

type CurrencyRow = {
  id: number;
  name: string;
  code: string;
  state: CurrencyState;
  buyRate: number;
  sellRate: number;
};

const initialRows: CurrencyRow[] = [
  { id: 1, name: "Dólar", code: "USD", state: "Activo", buyRate: 7500, sellRate: 7700 },
  { id: 2, name: "Euro", code: "EUR", state: "Activo", buyRate: 8200, sellRate: 8450 },
  { id: 3, name: "Real Brasileño", code: "BRL", state: "Inactivo", buyRate: 1148, sellRate: 1185 },
  { id: 4, name: "Yen", code: "JPY", state: "Activo", buyRate: 52, sellRate: 58 },
];

const formatPyg = (value: number) =>
  new Intl.NumberFormat("es-PY", {
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(value);

export default function MonedasModule() {
  const [rows, setRows] = useState<CurrencyRow[]>(initialRows);
  const [selectedId, setSelectedId] = useState<number | null>(initialRows[0]?.id ?? null);
  const [showForm, setShowForm] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [toast, setToast] = useState<string | null>(null);

  const selectedRow = useMemo(
    () => rows.find((row) => row.id === selectedId) ?? null,
    [rows, selectedId],
  );

  const [formData, setFormData] = useState({
    name: "",
    code: "",
    buyRate: "",
    sellRate: "",
    state: "Activo" as CurrencyState,
  });

  const openAddForm = () => {
    setIsEditing(false);
    setFormData({
      name: "",
      code: "",
      buyRate: "",
      sellRate: "",
      state: "Activo",
    });
    setShowForm(true);
  };

  const openEditForm = () => {
    if (!selectedRow) return;
    setIsEditing(true);
    setFormData({
      name: selectedRow.name,
      code: selectedRow.code,
      buyRate: String(selectedRow.buyRate),
      sellRate: String(selectedRow.sellRate),
      state: selectedRow.state,
    });
    setShowForm(true);
  };

  const handleToggleState = (id: number) => {
    setRows((prev) =>
      prev.map((row) =>
        row.id === id
          ? { ...row, state: row.state === "Activo" ? "Inactivo" : "Activo" }
          : row,
      ),
    );
    setToast("Estado actualizado correctamente.");
    setTimeout(() => setToast(null), 2200);
  };

  const handleSave = () => {
    if (!formData.name || !formData.code || !formData.buyRate || !formData.sellRate) {
      setToast("Completa todos los campos para continuar.");
      setTimeout(() => setToast(null), 2200);
      return;
    }

    if (isEditing && selectedRow) {
      setRows((prev) =>
        prev.map((row) =>
          row.id === selectedRow.id
            ? {
                ...row,
                name: formData.name,
                code: formData.code,
                buyRate: Number(formData.buyRate),
                sellRate: Number(formData.sellRate),
                state: formData.state,
              }
            : row,
        ),
      );
      setToast("Cotización actualizada correctamente.");
    } else {
      const nextId = Math.max(0, ...rows.map((row) => row.id)) + 1;
      setRows((prev) => [
        ...prev,
        {
          id: nextId,
          name: formData.name,
          code: formData.code,
          buyRate: Number(formData.buyRate),
          sellRate: Number(formData.sellRate),
          state: formData.state,
        },
      ]);
      setSelectedId(nextId);
      setToast("Moneda agregada correctamente.");
    }

    setShowForm(false);
    setTimeout(() => setToast(null), 2400);
  };

  return (
    <div className="space-y-6">
      <div className="rounded-3xl border border-[#dbe3ee] bg-white p-6 shadow-sm">
        <div className="mb-5 flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          <div>
            <p className="text-sm font-medium text-[#64748b]">Administración</p>
            <h2 className="text-2xl font-bold tracking-tight text-[#0f172a]">Monedas</h2>
          </div>

          <div className="flex flex-wrap gap-3">
            <button
              onClick={openAddForm}
              className="rounded-xl bg-[#1a7eff] px-4 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-[#146be7]"
            >
              Agregar Moneda
            </button>
            <button
              onClick={openEditForm}
              disabled={!selectedRow}
              className="rounded-xl border border-[#dbe3ee] bg-white px-4 py-2.5 text-sm font-semibold text-[#374151] hover:bg-[#f8fafc] disabled:cursor-not-allowed disabled:opacity-50"
            >
              Modificar Moneda
            </button>
          </div>
        </div>

        <div className="overflow-hidden rounded-2xl border border-[#e2e8f0]">
          <table className="min-w-full border-collapse bg-white text-left text-sm text-[#1f2937]">
            <thead className="bg-[#f8fafc] text-[#475569]">
              <tr>
                <th className="px-4 py-3 font-semibold">Moneda</th>
                <th className="px-4 py-3 font-semibold">Estado</th>
                <th className="px-4 py-3 text-right font-semibold">Tasa Compra</th>
                <th className="px-4 py-3 text-right font-semibold">Tasa Venta</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr
                  key={row.id}
                  className={`border-t border-[#edf2f7] transition ${selectedId === row.id ? "bg-[#f0f7ff]" : "bg-white hover:bg-[#f8fafc]"}`}
                  onClick={() => setSelectedId(row.id)}
                >
                  <td className="px-4 py-3">
                    <div className="font-medium text-[#0f172a]">{row.name}</div>
                    <div className="text-xs text-[#64748b]">{row.code}</div>
                  </td>
                  <td className="px-4 py-3">
                    <button
                      type="button"
                      onClick={(event) => {
                        event.stopPropagation();
                        handleToggleState(row.id);
                      }}
                      className={`inline-flex items-center gap-2 rounded-full px-3 py-1.5 text-xs font-semibold ${
                        row.state === "Activo"
                          ? "bg-green-100 text-green-700"
                          : "bg-red-100 text-red-700"
                      }`}
                    >
                      <span
                        className={`h-2.5 w-2.5 rounded-full ${
                          row.state === "Activo" ? "bg-green-500" : "bg-red-500"
                        }`}
                      />
                      {row.state}
                    </button>
                  </td>
                  <td className="px-4 py-3 text-right font-medium text-[#0f172a]">
                    {formatPyg(row.buyRate)} PYG
                  </td>
                  <td className="px-4 py-3 text-right font-medium text-[#0f172a]">
                    {formatPyg(row.sellRate)} PYG
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {showForm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 px-4">
          <div className="w-full max-w-xl rounded-2xl bg-white p-6 shadow-2xl">
            <h3 className="text-2xl font-bold text-[#0f172a]">
              {isEditing ? "Modificar moneda" : "Agregar moneda"}
            </h3>

            <div className="mt-5 grid gap-4 md:grid-cols-2">
              <label className="block md:col-span-2">
                <span className="mb-2 block text-sm font-medium text-[#374151]">Nombre de la moneda</span>
                <input
                  value={formData.name}
                  onChange={(event) => setFormData({ ...formData, name: event.target.value })}
                  className="w-full rounded-xl border border-[#dbe3ee] bg-[#f8fafc] px-3 py-2.5 text-sm text-[#1f2937] outline-none focus:border-[#1a7eff]"
                  placeholder="Dólar"
                />
              </label>

              <label className="block">
                <span className="mb-2 block text-sm font-medium text-[#374151]">Código ISO</span>
                <input
                  value={formData.code}
                  onChange={(event) => setFormData({ ...formData, code: event.target.value.toUpperCase() })}
                  className="w-full rounded-xl border border-[#dbe3ee] bg-[#f8fafc] px-3 py-2.5 text-sm text-[#1f2937] outline-none focus:border-[#1a7eff]"
                  placeholder="USD"
                />
              </label>

              <label className="block">
                <span className="mb-2 block text-sm font-medium text-[#374151]">Estado inicial</span>
                <select
                  value={formData.state}
                  onChange={(event) => setFormData({ ...formData, state: event.target.value as CurrencyState })}
                  className="w-full rounded-xl border border-[#dbe3ee] bg-[#f8fafc] px-3 py-2.5 text-sm text-[#1f2937] outline-none focus:border-[#1a7eff]"
                >
                  <option value="Activo">Activo</option>
                  <option value="Inactivo">Inactivo</option>
                </select>
              </label>

              <label className="block">
                <span className="mb-2 block text-sm font-medium text-[#374151]">Tasa de Compra</span>
                <input
                  type="number"
                  value={formData.buyRate}
                  onChange={(event) => setFormData({ ...formData, buyRate: event.target.value })}
                  className="w-full rounded-xl border border-[#dbe3ee] bg-[#f8fafc] px-3 py-2.5 text-sm text-[#1f2937] outline-none focus:border-[#1a7eff]"
                  placeholder="7500"
                />
              </label>

              <label className="block">
                <span className="mb-2 block text-sm font-medium text-[#374151]">Tasa de Venta</span>
                <input
                  type="number"
                  value={formData.sellRate}
                  onChange={(event) => setFormData({ ...formData, sellRate: event.target.value })}
                  className="w-full rounded-xl border border-[#dbe3ee] bg-[#f8fafc] px-3 py-2.5 text-sm text-[#1f2937] outline-none focus:border-[#1a7eff]"
                  placeholder="7700"
                />
              </label>
            </div>

            <div className="mt-6 flex justify-end gap-3">
              <button
                onClick={() => setShowForm(false)}
                className="rounded-xl border border-[#dbe3ee] bg-white px-4 py-2.5 text-sm font-semibold text-[#374151] hover:bg-[#f8fafc]"
              >
                Cancelar
              </button>
              <button
                onClick={handleSave}
                className="rounded-xl bg-[#1a7eff] px-4 py-2.5 text-sm font-semibold text-white hover:bg-[#146be7]"
              >
                {isEditing ? "Guardar cambios" : "Guardar moneda"}
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
