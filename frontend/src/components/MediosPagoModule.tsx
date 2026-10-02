import { useEffect, useState } from "react";
import {
  actualizarMedioPago,
  borrarMedioPago,
  crearMedioPago,
  listarMediosPago,
  actualizarTipoMedioPago,
  type MedioPago,
  type TipoMedioPago,
} from "../lib/mediosPagoApi";

type Props = { adminMode?: boolean };
type FormState = Record<string, string> & { tipo: string; alias: string };
const EMPTY: FormState = { tipo: "", alias: "" };

const fields: Record<string, { key: string; label: string; type?: string }[]> = {
  TARJETA_CREDITO: [
    { key: "nombreTitular", label: "Nombre del titular" },
    { key: "aliasTarjeta", label: "Alias de tarjeta" },
    { key: "numeroTarjeta", label: "Número de tarjeta" },
    { key: "fechaVencimiento", label: "Vencimiento (MM/YY)" },
    { key: "codigoSeguridad", label: "Código de seguridad", type: "password" },
  ],
  TRANSFERENCIA: [
    { key: "numeroCuentaOrigen", label: "Cuenta origen" },
    { key: "bancoOrigen", label: "Banco origen" },
    { key: "titularOrigen", label: "Titular origen" },
    { key: "numeroCuentaDestino", label: "Cuenta destino" },
    { key: "bancoDestino", label: "Banco destino" },
    { key: "titularDestino", label: "Titular destino" },
  ],
  BILLETERA_DIGITAL: [
    { key: "plataforma", label: "Plataforma" },
    { key: "identificadorCuenta", label: "CVU, alias, email o número" },
    { key: "titular", label: "Titular" },
  ],
};

export default function MediosPagoModule({ adminMode = false }: Props) {
  const [medios, setMedios] = useState<MedioPago[]>([]);
  const [tipos, setTipos] = useState<TipoMedioPago[]>([]);
  const [form, setForm] = useState<FormState>(EMPTY);
  const [editando, setEditando] = useState<number | null>(null);
  const [modal, setModal] = useState(false);
  const [toast, setToast] = useState<string | null>(null);

  const avisar = (mensaje: string) => {
    setToast(mensaje);
    setTimeout(() => setToast(null), 2800);
  };
  const recargar = async () => {
    try {
      const data = await listarMediosPago();
      setMedios(data.medios);
      setTipos(data.tipos);
    } catch (error) {
      avisar(error instanceof Error ? error.message : "No se pudieron cargar los métodos.");
    }
  };
  useEffect(() => { void recargar(); }, []);

  const abrir = (medio?: MedioPago) => {
    if (!medio) {
      setEditando(null);
      setForm({ ...EMPTY });
    } else {
      setEditando(medio.id);
      setForm({ tipo: medio.tipo, alias: medio.alias, ...medio.detalle });
    }
    setModal(true);
  };
  const guardar = async () => {
    if (!form.tipo || !form.alias.trim()) return avisar("Tipo y alias son obligatorios.");
    try {
      if (editando === null) await crearMedioPago(form);
      else await actualizarMedioPago(editando, form);
      setModal(false);
      await recargar();
      avisar("Método de pago guardado.");
    } catch (error) {
      avisar(error instanceof Error ? error.message : "No se pudo guardar.");
    }
  };
  const eliminar = async (medio: MedioPago) => {
    if (!window.confirm(`¿Eliminar «${medio.alias}»?`)) return;
    await borrarMedioPago(medio.id);
    await recargar();
  };
  const cambiarEstado = async (medio: MedioPago) => {
    try {
      await actualizarMedioPago(medio.id, { tipo: medio.tipo, alias: medio.alias, activo: !medio.activo });
      await recargar();
    } catch (error) {
      avisar(error instanceof Error ? error.message : "No se pudo cambiar el estado.");
    }
  };
  const cambiarTipo = async (tipo: TipoMedioPago) => {
    try {
      const actualizado = await actualizarTipoMedioPago(tipo.valor, !tipo.activo);
      setTipos((actuales) => actuales.map((item) => item.valor === actualizado.valor ? actualizado : item));
      avisar(`Categoría ${actualizado.activo ? "activada" : "desactivada"}.`);
    } catch (error) {
      avisar(error instanceof Error ? error.message : "No se pudo cambiar el estado.");
    }
  };

  return (
    <div className="rounded-3xl border border-[#dbe3ee] bg-white p-6 shadow-sm">
      <div className="mb-5 flex items-center justify-between gap-3">
        <div><p className="text-sm font-medium text-[#64748b]">{adminMode ? "Administración" : "Configuración"}</p><h2 className="text-2xl font-bold text-[#0f172a]">Métodos de pago</h2></div>
        {!adminMode && <button onClick={() => abrir()} className="rounded-xl bg-[#1a7eff] px-4 py-2.5 text-sm font-semibold text-white">Agregar método</button>}
      </div>
      {adminMode ? (
      <div className="overflow-x-auto rounded-2xl border border-[#e2e8f0]">
        <table className="min-w-full text-left text-sm"><thead className="bg-[#f8fafc]"><tr><th className="px-4 py-3">Categoría global</th><th className="px-4 py-3">Estado</th><th className="px-4 py-3">Acción</th></tr></thead>
          <tbody>{tipos.map((tipo) => <tr key={tipo.valor} className="border-t border-[#edf2f7]">
            <td className="px-4 py-3 font-medium">{tipo.texto}</td>
            <td className="px-4 py-3">{tipo.activo ? "Activo" : "Inactivo"}</td>
            <td className="px-4 py-3"><button onClick={() => void cambiarTipo(tipo)} className={`rounded-full px-3 py-1 text-xs font-semibold ${tipo.activo ? "bg-green-100 text-green-700" : "bg-slate-200 text-slate-600"}`}>{tipo.activo ? "Desactivar" : "Activar"}</button></td>
          </tr>)}</tbody>
        </table>
      </div>
      ) : (
      <div className="overflow-x-auto rounded-2xl border border-[#e2e8f0]">
        <table className="min-w-full text-left text-sm"><thead className="bg-[#f8fafc]"><tr><th className="px-4 py-3">Tipo</th><th className="px-4 py-3">Alias</th><th className="px-4 py-3">Usuario</th><th className="px-4 py-3">Estado</th><th className="px-4 py-3">Acciones</th></tr></thead>
          <tbody>{medios.map((medio) => <tr key={medio.id} className="border-t border-[#edf2f7]">
            <td className="px-4 py-3">{medio.tipoTexto}</td><td className="px-4 py-3 font-medium">{medio.alias}</td><td className="px-4 py-3">{medio.usuario}</td>
            <td className="px-4 py-3"><button onClick={() => adminMode && cambiarEstado(medio)} disabled={!adminMode} className={`rounded-full px-2.5 py-1 text-xs font-semibold ${medio.activo ? "bg-green-100 text-green-700" : "bg-slate-200 text-slate-600"}`}>{medio.activo ? "Activo" : "Inactivo"}</button></td>
            <td className="px-4 py-3">{!adminMode && <><button onClick={() => abrir(medio)} className="mr-2 text-xs font-semibold text-[#1a7eff]">Modificar</button><button onClick={() => void eliminar(medio)} className="text-xs font-semibold text-red-600">Eliminar</button></>}</td>
          </tr>)}</tbody>
        </table>
      </div>
      )}
      {modal && <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 px-4"><div className="max-h-[90vh] w-full max-w-lg overflow-y-auto rounded-2xl bg-white p-6">
        <h3 className="text-xl font-bold">Método de pago</h3>
        <div className="mt-4 grid gap-3">
          <select value={form.tipo} onChange={(e) => setForm({ tipo: e.target.value, alias: "", })} className="rounded-xl border px-3 py-2.5"><option value="">Seleccionar tipo</option>{tipos.filter((tipo) => tipo.activo).map((tipo) => <option key={tipo.valor} value={tipo.valor}>{tipo.texto}</option>)}</select>
          <input value={form.alias} onChange={(e) => setForm({ ...form, alias: e.target.value })} placeholder="Alias del método" className="rounded-xl border px-3 py-2.5" />
          {(fields[form.tipo] ?? []).map((field) => <input key={field.key} type={field.type ?? "text"} value={form[field.key] ?? ""} onChange={(e) => setForm({ ...form, [field.key]: e.target.value })} placeholder={field.label} className="rounded-xl border px-3 py-2.5" />)}
        </div>
        <div className="mt-5 flex justify-end gap-3"><button onClick={() => setModal(false)} className="rounded-xl border px-4 py-2">Cancelar</button><button onClick={() => void guardar()} className="rounded-xl bg-[#1a7eff] px-4 py-2 font-semibold text-white">Guardar</button></div>
      </div></div>}
      {toast && <div className="fixed bottom-6 right-6 z-[60] rounded-xl bg-[#0f172a] px-4 py-3 text-sm text-white">{toast}</div>}
    </div>
  );
}
