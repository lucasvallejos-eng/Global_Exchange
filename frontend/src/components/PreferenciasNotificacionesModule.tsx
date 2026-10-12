import { useEffect, useState } from "react";
import {
  guardarPreferencias,
  obtenerPreferencias,
  type PreferenciasNotificaciones,
} from "../lib/notificacionesApi";

// Suscripciones: qué notificaciones de la campanita quiere recibir el usuario.
// Compras, ventas y cambios de cotización se combinan libremente; en las
// cotizaciones se puede seguir solo algunas divisas.

type Estado = Omit<PreferenciasNotificaciones, "monedasDisponibles">;

function Interruptor({
  activo,
  onCambio,
  titulo,
  descripcion,
}: {
  activo: boolean;
  onCambio: (activo: boolean) => void;
  titulo: string;
  descripcion: string;
}) {
  return (
    <label className="flex cursor-pointer items-start justify-between gap-4 rounded-2xl border border-[#e2e8f0] bg-white p-4 hover:bg-[#f8fafc]">
      <span>
        <span className="block font-semibold text-[#0f172a]">{titulo}</span>
        <span className="mt-0.5 block text-sm text-[#64748b]">{descripcion}</span>
      </span>
      <span className="relative mt-1 inline-flex shrink-0">
        <input type="checkbox" checked={activo} onChange={(e) => onCambio(e.target.checked)} className="peer sr-only" />
        <span className="h-6 w-11 rounded-full bg-slate-300 transition-colors peer-checked:bg-[#1a7eff] peer-focus-visible:ring-2 peer-focus-visible:ring-[#1a7eff]/40" />
        <span className="absolute left-0.5 top-0.5 h-5 w-5 rounded-full bg-white shadow transition-transform peer-checked:translate-x-5" />
      </span>
    </label>
  );
}

export default function PreferenciasNotificacionesModule() {
  const [estado, setEstado] = useState<Estado | null>(null);
  const [guardado, setGuardado] = useState<Estado | null>(null);
  const [disponibles, setDisponibles] = useState<PreferenciasNotificaciones["monedasDisponibles"]>([]);
  const [guardando, setGuardando] = useState(false);
  const [aviso, setAviso] = useState<{ tipo: "ok" | "error"; texto: string } | null>(null);

  useEffect(() => {
    obtenerPreferencias()
      .then(({ monedasDisponibles, ...resto }) => {
        setEstado(resto);
        setGuardado(resto);
        setDisponibles(monedasDisponibles);
      })
      .catch((e: unknown) => setAviso({ tipo: "error", texto: e instanceof Error ? e.message : "No se pudieron cargar tus preferencias." }));
  }, []);

  if (!estado) {
    return (
      <div className="rounded-3xl border border-[#dbe3ee] bg-white p-10 text-center text-[#64748b] shadow-sm">
        {aviso?.texto ?? "Cargando..."}
      </div>
    );
  }

  const cambiar = (cambios: Partial<Estado>) => {
    setEstado({ ...estado, ...cambios });
    setAviso(null);
  };
  const todasLasMonedas = estado.monedas.length === 0;
  const alternarMoneda = (codigo: string) => {
    const elegidas = new Set(estado.monedas);
    if (elegidas.has(codigo)) elegidas.delete(codigo);
    else elegidas.add(codigo);
    // Marcar todas una por una equivale a "todas".
    cambiar({ monedas: elegidas.size === disponibles.length ? [] : [...elegidas].sort() });
  };
  const sinCambios = JSON.stringify(estado) === JSON.stringify(guardado);
  const nada = !estado.compras && !estado.ventas && !estado.cotizaciones;

  const guardar = async () => {
    setGuardando(true);
    try {
      const { monedasDisponibles: _, ...resto } = await guardarPreferencias(estado);
      setEstado(resto);
      setGuardado(resto);
      setAviso({ tipo: "ok", texto: "Preferencias guardadas." });
    } catch (e) {
      setAviso({ tipo: "error", texto: e instanceof Error ? e.message : "No se pudieron guardar." });
    } finally {
      setGuardando(false);
    }
  };

  return (
    <div className="rounded-3xl border border-[#dbe3ee] bg-white p-6 shadow-sm">
      <div className="mb-6">
        <p className="text-sm font-medium text-[#64748b]">Suscripciones</p>
        <h2 className="text-2xl font-bold tracking-tight text-[#0f172a]">Preferencias de notificaciones</h2>
        <p className="mt-1 text-sm text-[#64748b]">Elegí qué avisos querés recibir en la campanita. Podés combinarlos como quieras.</p>
      </div>

      <div className="grid gap-3 md:grid-cols-3">
        <Interruptor
          activo={estado.compras}
          onCambio={(compras) => cambiar({ compras })}
          titulo="Compras"
          descripcion="Compras exitosas (con medio de pago y valor) y fallidas (con el motivo)."
        />
        <Interruptor
          activo={estado.ventas}
          onCambio={(ventas) => cambiar({ ventas })}
          titulo="Ventas"
          descripcion="Ventas exitosas (con medio de pago y valor) y fallidas (con el motivo)."
        />
        <Interruptor
          activo={estado.cotizaciones}
          onCambio={(cotizaciones) => cambiar({ cotizaciones })}
          titulo="Cotizaciones"
          descripcion="Cuando cambia el precio de compra o venta de una divisa."
        />
      </div>

      {estado.cotizaciones && disponibles.length > 0 && (
        <div className="mt-5 rounded-2xl border border-[#e2e8f0] bg-[#f8fafc] p-4">
          <p className="font-semibold text-[#0f172a]">¿De qué divisas?</p>
          <div className="mt-3 flex flex-wrap gap-2">
            <button
              onClick={() => cambiar({ monedas: [] })}
              className={`rounded-full px-3 py-1.5 text-sm font-semibold ${todasLasMonedas ? "bg-[#1a7eff] text-white" : "border border-[#dbe3ee] bg-white text-[#374151]"}`}
            >
              Todas
            </button>
            {disponibles.map((moneda) => {
              const elegida = estado.monedas.includes(moneda.codigo);
              return (
                <button
                  key={moneda.codigo}
                  onClick={() => alternarMoneda(moneda.codigo)}
                  title={moneda.nombre}
                  className={`rounded-full px-3 py-1.5 text-sm font-semibold ${elegida ? "bg-[#1a7eff] text-white" : "border border-[#dbe3ee] bg-white text-[#374151]"}`}
                >
                  {moneda.codigo}
                </button>
              );
            })}
          </div>
          <p className="mt-2 text-xs text-[#64748b]">
            {todasLasMonedas ? "Recibís los cambios de todas las divisas." : `Solo: ${estado.monedas.join(", ")}.`}
          </p>
        </div>
      )}

      {nada && (
        <p className="mt-5 rounded-xl border border-yellow-200 bg-yellow-50 px-4 py-3 text-sm text-yellow-800">
          Con todo desactivado no vas a recibir ninguna notificación.
        </p>
      )}

      {aviso && (
        <p className={`mt-5 rounded-xl border px-4 py-3 text-sm ${aviso.tipo === "ok" ? "border-green-200 bg-green-50 text-green-700" : "border-red-200 bg-red-50 text-red-700"}`}>
          {aviso.texto}
        </p>
      )}

      <div className="mt-6 flex justify-end">
        <button
          onClick={() => void guardar()}
          disabled={guardando || sinCambios}
          className="rounded-xl bg-[#1a7eff] px-5 py-2.5 text-sm font-semibold text-white hover:bg-[#146be7] disabled:cursor-not-allowed disabled:bg-slate-300"
        >
          {guardando ? "Guardando..." : "Guardar preferencias"}
        </button>
      </div>
    </div>
  );
}
