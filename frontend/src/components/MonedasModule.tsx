import { useEffect, useMemo, useState } from "react";
import {
  actualizarMoneda,
  crearMoneda,
  listarMonedas,
  type Moneda,
} from "../lib/monedasApi";

type CurrencyState = "Activo" | "Inactivo";

type CurrencyRow = {
  id: number;
  name: string;
  code: string;
  state: CurrencyState;
  buyRate: number;
  sellRate: number;
};

/** Pasa una moneda de la API a la fila que dibuja la tabla. */
function aFila(moneda: Moneda): CurrencyRow {
  return {
    id: moneda.id,
    name: moneda.nombre,
    code: moneda.codigo,
    state: moneda.activo ? "Activo" : "Inactivo",
    buyRate: moneda.precioCompra ?? 0,
    sellRate: moneda.precioVenta ?? 0,
  };
}

const formatPyg = (value: number) =>
  new Intl.NumberFormat("es-PY", {
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(value);

export default function MonedasModule() {
  const [rows, setRows] = useState<CurrencyRow[]>([]);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [cargando, setCargando] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [toast, setToast] = useState<string | null>(null);

  const selectedRow = useMemo(
    () => rows.find((row) => row.id === selectedId) ?? null,
    [rows, selectedId],
  );

  const avisar = (mensaje: string) => {
    setToast(mensaje);
    setTimeout(() => setToast(null), 2600);
  };

  /** Trae las monedas del backend y deja seleccionada la primera. */
  const recargar = async (idPreferido?: number) => {
    try {
      const monedas = await listarMonedas();
      const filas = monedas.map(aFila);
      setRows(filas);
      setSelectedId((actual) => idPreferido ?? actual ?? filas[0]?.id ?? null);
    } catch (e) {
      avisar(e instanceof Error ? e.message : "No se pudieron cargar las monedas.");
    } finally {
      setCargando(false);
    }
  };

  useEffect(() => {
    void recargar();
    // Solo al montar: despues se recarga a mano tras cada alta o edicion.
  }, []);

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

  const handleToggleState = async (id: number) => {
    const fila = rows.find((row) => row.id === id);
    if (!fila) return;
    try {
      await actualizarMoneda(id, { activo: fila.state !== "Activo" });
      await recargar(id);
      avisar("Estado actualizado correctamente.");
    } catch (e) {
      avisar(e instanceof Error ? e.message : "No se pudo actualizar el estado.");
    }
  };

  const handleSave = async () => {
    if (!formData.name || !formData.code || !formData.buyRate || !formData.sellRate) {
      avisar("Completa todos los campos para continuar.");
      return;
    }

    const datos = {
      nombre: formData.name,
      codigo: formData.code,
      simbolo: formData.code,
      activo: formData.state === "Activo",
      precioCompra: Number(formData.buyRate),
      precioVenta: Number(formData.sellRate),
    };

    try {
      if (isEditing && selectedRow) {
        // El codigo identifica la moneda y no se cambia al editar.
        const { codigo, ...sinCodigo } = datos;
        await actualizarMoneda(selectedRow.id, sinCodigo);
        await recargar(selectedRow.id);
        avisar("Cotizacion actualizada correctamente.");
      } else {
        const creada = await crearMoneda(datos);
        await recargar(creada.id);
        avisar("Moneda agregada correctamente.");
      }
      setShowForm(false);
    } catch (e) {
      // Incluye el mensaje de RN10 cuando la venta no supera a la compra.
      avisar(e instanceof Error ? e.message : "No se pudo guardar la moneda.");
    }
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
