import { useEffect, useState } from "react";

import type { TipoOperacion } from "../lib/operacionesApi";
import {
  listarReservas,
  listarTerminales,
  reservarEnTerminal,
  type Reserva,
  type TerminalDisponible,
} from "../lib/terminalApi";
import { useTasas } from "../lib/useTasas";

// Terminal de autoservicio: el cliente reserva una compra o venta y recibe un
// código; después va a la terminal, lo ingresa y deposita los billetes. Si la
// cotización cambia antes, la terminal cancela la operación sin cobrar.

const formatMonto = (valor: number, moneda: string) =>
  `${new Intl.NumberFormat("es-PY", { maximumFractionDigits: moneda === "PYG" ? 0 : 2 }).format(valor)} ${moneda}`;

const claseCampo =
  "w-full rounded-xl border border-[#dbe3ee] bg-[#f8fafc] px-3 py-2.5 text-sm text-[#1f2937] outline-none focus:border-[#1a7eff]";
const claseEtiqueta = "mb-2 block text-xs font-semibold uppercase tracking-[0.12em] text-[#64748b]";

const colorEstado: Record<Reserva["estado"], string> = {
  ESPERANDO: "bg-yellow-100 text-yellow-700",
  COMPLETADA: "bg-green-100 text-green-700",
  CANCELADA: "bg-red-100 text-red-700",
};

export default function TerminalModule({ clienteId }: { clienteId: string | null }) {
  const { codigos } = useTasas();
  const [tipo, setTipo] = useState<TipoOperacion>("COMPRA");
  const [moneda, setMoneda] = useState("");
  const [monto, setMonto] = useState("");
  const [reservas, setReservas] = useState<Reserva[]>([]);
  const [terminales, setTerminales] = useState<TerminalDisponible[]>([]);
  const [nueva, setNueva] = useState<Reserva | null>(null);
  const [error, setError] = useState("");
  const [enviando, setEnviando] = useState(false);

  const recargar = () =>
    listarReservas()
      .then((datos) => setReservas(datos.reservas))
      .catch((e: Error) => setError(e.message));

  useEffect(() => {
    recargar();
    listarTerminales().then((datos) => setTerminales(datos.terminales)).catch(() => setTerminales([]));
    // El cliente completa la operación en la terminal (otra pantalla): se refresca el estado.
    const intervalo = window.setInterval(recargar, 5000);
    return () => window.clearInterval(intervalo);
  }, []);

  useEffect(() => {
    if (!moneda && codigos.length) setMoneda(codigos[0]);
  }, [codigos, moneda]);

  const reservar = async () => {
    setError("");
    setNueva(null);
    if (!clienteId) {
      setError("Elegí uno de tus clientes arriba.");
      return;
    }
    setEnviando(true);
    try {
      const reserva = await reservarEnTerminal({ clienteId: Number(clienteId), tipo, moneda, monto: Number(monto) });
      setNueva(reserva);
      setMonto("");
      recargar();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setEnviando(false);
    }
  };

  const urlTerminal = nueva?.urlTerminal ?? reservas[0]?.urlTerminal;

  return (
    <div className="space-y-6">
      <div className="rounded-3xl border border-[#dbe3ee] bg-white p-6 shadow-sm">
        <p className="text-sm font-medium text-[#64748b]">Terminal de autoservicio</p>
        <h2 className="text-2xl font-bold tracking-tight text-[#0f172a]">Pagar con efectivo en la terminal</h2>
        <p className="mt-1 mb-5 text-sm text-[#64748b]">
          Reservá la operación y te damos un código. En la terminal lo ingresás y depositás los billetes: si comprás,
          guaraníes; si vendés, la divisa. Si la cotización cambia antes de que vayas, la operación se cancela sin
          cobrarte nada.
          {terminales.length > 0 && ` Terminales: ${terminales.map((t) => `${t.nombre}${t.ubicacion ? ` (${t.ubicacion})` : ""}`).join(", ")}.`}
        </p>

        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-[1fr_1fr_1fr_auto]">
          <label className="block">
            <span className={claseEtiqueta}>Operación</span>
            <select value={tipo} onChange={(e) => setTipo(e.target.value as TipoOperacion)} className={claseCampo}>
              <option value="COMPRA">Comprar divisa</option>
              <option value="VENTA">Vender divisa</option>
            </select>
          </label>
          <label className="block">
            <span className={claseEtiqueta}>Moneda</span>
            <select value={moneda} onChange={(e) => setMoneda(e.target.value)} className={claseCampo}>
              {codigos.map((codigo) => (
                <option key={codigo} value={codigo}>{codigo}</option>
              ))}
            </select>
          </label>
          <label className="block">
            <span className={claseEtiqueta}>Monto en divisa</span>
            <input type="number" min="1" step="1" value={monto} onChange={(e) => setMonto(e.target.value)}
                   placeholder="100" className={claseCampo} />
          </label>
          <div className="flex items-end">
            <button
              onClick={reservar}
              disabled={enviando || !monto || !moneda}
              className="rounded-xl bg-[#1a7eff] px-5 py-2.5 text-sm font-semibold text-white hover:bg-[#1569d8] disabled:cursor-not-allowed disabled:opacity-50"
            >
              {enviando ? "Reservando..." : "Reservar"}
            </button>
          </div>
        </div>
        {error && <p className="mt-3 text-sm font-medium text-red-600">{error}</p>}

        {nueva && (
          <div className="mt-5 rounded-2xl border border-[#bfdbfe] bg-[#eff6ff] p-5">
            <p className="text-sm text-[#1e3a8a]">Tu código para la terminal</p>
            <p className="my-1 text-4xl font-extrabold tracking-[0.3em] text-[#0f3d7a]">{nueva.codigo}</p>
            <p className="text-sm text-[#1e3a8a]">
              Depositás {formatMonto(nueva.deposita.monto, nueva.deposita.moneda)} y recibís{" "}
              {formatMonto(nueva.recibe.monto, nueva.recibe.moneda)} (operación #{nueva.operacion.id}).
            </p>
          </div>
        )}
        {urlTerminal && (
          <a href={urlTerminal} target="_blank" rel="noreferrer"
             className="mt-4 inline-block rounded-xl border border-[#dbe3ee] bg-white px-4 py-2 text-sm font-semibold text-[#1a7eff] hover:bg-[#f8fafc]">
            Abrir la terminal
          </a>
        )}
      </div>

      <div className="rounded-3xl border border-[#dbe3ee] bg-white p-6 shadow-sm">
        <h3 className="mb-4 text-lg font-bold text-[#0f172a]">Mis reservas</h3>
        {reservas.length === 0 ? (
          <p className="text-sm text-[#64748b]">Todavía no reservaste ninguna operación.</p>
        ) : (
          <div className="overflow-x-auto rounded-2xl border border-[#e2e8f0]">
            <table className="min-w-full border-collapse bg-white text-left text-sm text-[#1f2937]">
              <thead className="bg-[#f8fafc] text-[#475569]">
                <tr>
                  <th className="px-4 py-3 font-semibold">Código</th>
                  <th className="px-4 py-3 font-semibold">Operación</th>
                  <th className="px-4 py-3 font-semibold">Depositás</th>
                  <th className="px-4 py-3 font-semibold">Recibís</th>
                  <th className="px-4 py-3 font-semibold">Estado</th>
                </tr>
              </thead>
              <tbody>
                {reservas.map((r) => (
                  <tr key={r.codigo} className="border-t border-[#edf2f7]">
                    <td className="px-4 py-3 font-mono font-semibold tracking-widest">{r.codigo}</td>
                    <td className="px-4 py-3 text-[#475569]">
                      #{r.operacion.id} · {r.operacion.tipoTexto} · {r.operacion.cliente.nombre}
                    </td>
                    <td className="px-4 py-3 tabular-nums">{formatMonto(r.deposita.monto, r.deposita.moneda)}</td>
                    <td className="px-4 py-3 tabular-nums">
                      {r.entrega === "CUENTA" ? "Acreditado en cuenta" : formatMonto(r.recibe.monto, r.recibe.moneda)}
                    </td>
                    <td className="px-4 py-3">
                      <span className={`inline-flex rounded-full px-2.5 py-1 text-xs font-semibold ${colorEstado[r.estado]}`}>
                        {r.estadoTexto}
                      </span>
                      {r.detalle && <span className="mt-1 block max-w-[280px] text-xs text-[#94a3b8]">{r.detalle}</span>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
