import { useCallback, useEffect, useRef, useState } from "react";
import { EVENTO_NOTIFICACIONES } from "../lib/api";
import {
  listarNotificaciones,
  marcarLeidas,
  type Notificacion,
  type TipoNotificacion,
} from "../lib/notificacionesApi";

// Cada cuánto se consulta al backend si hay notificaciones nuevas. Además se
// consulta al volver a la pestaña y después de cada operación (EVENTO_NOTIFICACIONES).
const REFRESCO_MS = 15000;
const DURACION_AVISO_MS = 5000;

const ESTILO: Record<TipoNotificacion, { punto: string; icono: string; fondo: string }> = {
  OPERACION_EXITOSA: { punto: "bg-green-500", icono: "M20 6 9 17l-5-5", fondo: "bg-green-50 text-green-600" },
  OPERACION_FALLIDA: { punto: "bg-red-500", icono: "M18 6 6 18M6 6l12 12", fondo: "bg-red-50 text-red-600" },
  COTIZACION: { punto: "bg-[#1a7eff]", icono: "M3 17l6-6 4 4 8-8M14 7h7v7", fondo: "bg-[#eaf3ff] text-[#1a7eff]" },
};

function haceCuanto(fecha: string): string {
  const segundos = Math.max(0, Math.round((Date.now() - new Date(fecha).getTime()) / 1000));
  if (segundos < 60) return "recién";
  const minutos = Math.round(segundos / 60);
  if (minutos < 60) return `hace ${minutos} min`;
  const horas = Math.round(minutos / 60);
  if (horas < 24) return `hace ${horas} h`;
  return new Date(fecha).toLocaleDateString("es-PY", { day: "2-digit", month: "2-digit", year: "numeric" });
}

function Icono({ tipo }: { tipo: TipoNotificacion }) {
  return (
    <span className={`mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-full ${ESTILO[tipo].fondo}`}>
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
        <path d={ESTILO[tipo].icono} />
      </svg>
    </span>
  );
}

/**
 * Campanita de la barra superior: contador de no leídas, lista desplegable y
 * un aviso emergente cuando llega una notificación nueva.
 */
export default function NotificacionesCampana({ onConfigurar }: { onConfigurar: () => void }) {
  const [notificaciones, setNotificaciones] = useState<Notificacion[]>([]);
  const [noLeidas, setNoLeidas] = useState(0);
  const [abierta, setAbierta] = useState(false);
  // Las que estaban sin leer al abrir el panel: se resaltan aunque al abrir se marquen leídas.
  const [resaltadas, setResaltadas] = useState<Set<number>>(new Set());
  const [aviso, setAviso] = useState<{ notificacion: Notificacion; extra: number } | null>(null);
  // Id más alto ya visto. null hasta la primera carga, para no avisar lo viejo al entrar.
  const ultimoId = useRef<number | null>(null);
  const contenedor = useRef<HTMLDivElement>(null);

  const cargar = useCallback(async () => {
    try {
      const datos = await listarNotificaciones();
      setNotificaciones(datos.notificaciones);
      setNoLeidas(datos.noLeidas);
      const maximo = datos.notificaciones.reduce((max, n) => Math.max(max, n.id), 0);
      if (ultimoId.current !== null) {
        const nuevas = datos.notificaciones.filter((n) => n.id > (ultimoId.current ?? 0) && !n.leida);
        if (nuevas.length > 0) setAviso({ notificacion: nuevas[0], extra: nuevas.length - 1 });
      }
      ultimoId.current = Math.max(ultimoId.current ?? 0, maximo);
    } catch {
      // Sin conexión o sesión vencida: se reintenta en la próxima consulta.
    }
  }, []);

  useEffect(() => {
    void cargar();
    const intervalo = window.setInterval(() => void cargar(), REFRESCO_MS);
    const alVolver = () => {
      if (document.visibilityState === "visible") void cargar();
    };
    const alOperar = () => void cargar();
    document.addEventListener("visibilitychange", alVolver);
    window.addEventListener(EVENTO_NOTIFICACIONES, alOperar);
    return () => {
      window.clearInterval(intervalo);
      document.removeEventListener("visibilitychange", alVolver);
      window.removeEventListener(EVENTO_NOTIFICACIONES, alOperar);
    };
  }, [cargar]);

  // El aviso emergente se va solo.
  useEffect(() => {
    if (!aviso) return;
    const temporizador = window.setTimeout(() => setAviso(null), DURACION_AVISO_MS);
    return () => window.clearTimeout(temporizador);
  }, [aviso]);

  // Cerrar el panel al hacer clic afuera.
  useEffect(() => {
    if (!abierta) return;
    const alHacerClic = (evento: MouseEvent) => {
      if (contenedor.current && !contenedor.current.contains(evento.target as Node)) setAbierta(false);
    };
    document.addEventListener("mousedown", alHacerClic);
    return () => document.removeEventListener("mousedown", alHacerClic);
  }, [abierta]);

  // Al abrir, las que se están viendo se marcan como leídas.
  const abrir = () => {
    if (abierta) return setAbierta(false);
    setAbierta(true);
    setAviso(null);
    const sinLeer = notificaciones.filter((n) => !n.leida).map((n) => n.id);
    setResaltadas(new Set(sinLeer));
    if (sinLeer.length === 0) return;
    setNotificaciones((lista) => lista.map((n) => ({ ...n, leida: true })));
    void marcarLeidas(sinLeer).then(({ noLeidas: restantes }) => setNoLeidas(restantes)).catch(() => undefined);
  };

  const marcarTodas = () => {
    setNotificaciones((lista) => lista.map((n) => ({ ...n, leida: true })));
    setNoLeidas(0);
    void marcarLeidas().catch(() => undefined);
  };

  return (
    <div ref={contenedor} className="relative">
      <button
        onClick={abrir}
        aria-label={noLeidas > 0 ? `Notificaciones: ${noLeidas} sin leer` : "Notificaciones"}
        className="relative rounded-lg p-2 text-[#6b7280] transition-colors hover:bg-[#f0f4f8]"
      >
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9" /><path d="M13.73 21a2 2 0 0 1-3.46 0" /></svg>
        {noLeidas > 0 && (
          <span className="absolute -right-0.5 -top-0.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-red-500 px-1 text-[10px] font-bold text-white">
            {noLeidas > 9 ? "9+" : noLeidas}
          </span>
        )}
      </button>

      {abierta && (
        <div className="absolute right-0 top-full z-50 mt-2 w-[22rem] max-w-[calc(100vw-2rem)] overflow-hidden rounded-2xl border border-[#e2e8f0] bg-white shadow-2xl">
          <div className="flex items-center justify-between border-b border-[#edf2f7] px-4 py-3">
            <p className="font-semibold text-[#0f172a]">Notificaciones</p>
            <div className="flex items-center gap-3">
              {notificaciones.some((n) => !n.leida) && (
                <button onClick={marcarTodas} className="text-xs font-semibold text-[#1a7eff]">Marcar todas como leídas</button>
              )}
              <button
                onClick={() => { setAbierta(false); onConfigurar(); }}
                title="Elegir qué notificaciones recibir"
                aria-label="Preferencias de notificaciones"
                className="rounded-lg p-1 text-[#64748b] hover:bg-[#f0f4f8] hover:text-[#0f172a]"
              >
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="3" /><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z" /></svg>
              </button>
            </div>
          </div>
          <div className="max-h-[28rem] overflow-y-auto">
            {notificaciones.length === 0 && (
              <p className="px-4 py-8 text-center text-sm text-[#64748b]">
                No tenés notificaciones.{" "}
                <button onClick={() => { setAbierta(false); onConfigurar(); }} className="font-semibold text-[#1a7eff]">Elegir qué recibir</button>
              </p>
            )}
            {notificaciones.map((n) => (
              <div key={n.id} className={`flex gap-3 border-b border-[#f1f5f9] px-4 py-3 ${resaltadas.has(n.id) ? "bg-[#f8fbff]" : ""}`}>
                <Icono tipo={n.tipo} />
                <div className="min-w-0 flex-1">
                  <div className="flex items-start justify-between gap-2">
                    <p className="text-sm font-semibold text-[#0f172a]">{n.titulo}</p>
                    {resaltadas.has(n.id) && <span className={`mt-1.5 h-2 w-2 shrink-0 rounded-full ${ESTILO[n.tipo].punto}`} />}
                  </div>
                  <p className="mt-0.5 text-sm text-[#475569]">{n.mensaje}</p>
                  <p className="mt-1 text-xs text-[#94a3b8]">{haceCuanto(n.fecha)}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {aviso && (
        <div
          role="status"
          className="fixed bottom-6 right-6 z-[60] flex w-[22rem] max-w-[calc(100vw-3rem)] gap-3 rounded-2xl border border-[#e2e8f0] bg-white p-4 shadow-2xl"
        >
          <Icono tipo={aviso.notificacion.tipo} />
          <div className="min-w-0 flex-1">
            <p className="text-sm font-semibold text-[#0f172a]">{aviso.notificacion.titulo}</p>
            <p className="mt-0.5 text-sm text-[#475569]">{aviso.notificacion.mensaje}</p>
            {aviso.extra > 0 && <p className="mt-1 text-xs text-[#64748b]">y {aviso.extra} notificación(es) más en la campanita</p>}
          </div>
          <button onClick={() => setAviso(null)} aria-label="Cerrar aviso" className="self-start text-[#94a3b8] hover:text-[#475569]">✕</button>
        </div>
      )}
    </div>
  );
}
