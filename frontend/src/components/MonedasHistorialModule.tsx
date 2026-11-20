import { useEffect, useMemo, useState } from "react";
import { obtenerEvolucionTasas, type PuntoEvolucion, type EvolucionTasasRespuesta } from "../lib/cotizacionesApi";
import { useTasas } from "../lib/useTasas";

export type RangeOption = "1M" | "6M" | "YTD" | "1A" | "MÁX";
export type ModoPrecio = "venta" | "compra";

// Se eliminaron '1D' y '5D' por requerimiento de negocio. Rangos de análisis estándar:
const RANGE_OPTIONS: RangeOption[] = ["1M", "6M", "YTD", "1A", "MÁX"];

const formatPyg = (value: number) =>
  new Intl.NumberFormat("es-PY", {
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(value);

const formatDateShort = (dateStr: string) => {
  if (!dateStr) return "";
  const [year, month, day] = dateStr.split("T")[0].split("-");
  return `${day}/${month}/${year}`;
};

/** Extrae el valor del punto según el modo seleccionado (venta o compra). */
const getValorPunto = (p: PuntoEvolucion, modo: ModoPrecio): number =>
  modo === "venta" ? p.value : (p.compra ?? p.value);

export default function MonedasHistorialModule() {
  const [currency, setCurrency] = useState<string>("");
  const [range, setRange] = useState<RangeOption>("1M");
  const [modoPrecio, setModoPrecio] = useState<ModoPrecio>("venta");
  const [hoveredPoint, setHoveredPoint] = useState<PuntoEvolucion | null>(null);

  const { codigos } = useTasas();
  const [datosEvolucion, setDatosEvolucion] = useState<EvolucionTasasRespuesta | null>(null);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState<string>("");

  useEffect(() => {
    if (!currency && codigos.length > 0) {
      setCurrency(codigos[0]);
    }
  }, [codigos, currency]);

  useEffect(() => {
    if (!currency) return;
    let vigente = true;
    setCargando(true);
    setError("");

    obtenerEvolucionTasas(currency, range)
      .then((datos) => {
        if (!vigente) return;
        setDatosEvolucion(datos);
      })
      .catch((e: Error) => {
        if (!vigente) return;
        setError(e.message || "Error al obtener cotizaciones del backend");
      })
      .finally(() => {
        if (vigente) setCargando(false);
      });

    return () => {
      vigente = false;
    };
  }, [currency, range]);

  // Solo puntos históricos (sin proyección)
  const historico = datosEvolucion?.historico ?? [];

  // Escala del Eje Y según el modo activo (venta o compra)
  const { minVisual, maxVisual, yTicks } = useMemo(() => {
    if (historico.length === 0) {
      return { minVisual: 7000, maxVisual: 8000, yTicks: [] };
    }
    const valores = historico.map((p) => getValorPunto(p, modoPrecio));
    const minVal = Math.min(...valores);
    const maxVal = Math.max(...valores);
    const delta = Math.max(maxVal - minVal, 50);
    const padding = delta * 0.15; // 15% de margen visual superior e inferior

    const minVisual = Math.floor(minVal - padding);
    const maxVisual = Math.ceil(maxVal + padding);
    const rangoVisual = Math.max(maxVisual - minVisual, 1);

    // 5 ticks distribuidos uniformemente de MAYOR (arriba) a MENOR (abajo)
    const ticks = [0, 1, 2, 3, 4].map((i) => {
      const porcentaje = i / 4; // 0 (arriba), 0.25, 0.5, 0.75, 1 (abajo)
      const valor = maxVisual - porcentaje * rangoVisual;
      return {
        indice: i,
        valor,
        ySvg: 10 + porcentaje * 80, // coordenada SVG Y: 10% (arriba) a 90% (abajo)
      };
    });

    return { minVisual, maxVisual, yTicks: ticks };
  }, [historico, modoPrecio]);

  // Mapeo de coordenadas SVG (X de 0 a 100, Y con escala corregida)
  const puntosHistoricosSvg = useMemo(() => {
    const totalPuntos = Math.max(historico.length - 1, 1);
    const rangoVisual = Math.max(maxVisual - minVisual, 1);

    return historico.map((p, idx) => {
      const valor = getValorPunto(p, modoPrecio);
      const x = (idx / totalPuntos) * 100;
      // Inversión corregida: mayor valor -> menor Y en SVG (arriba)
      const y = 10 + ((maxVisual - valor) / rangoVisual) * 80;
      return { ...p, x, y, valorModo: valor };
    });
  }, [historico, minVisual, maxVisual, modoPrecio]);

  // Rutas SVG (línea continua para histórico)
  const pathHistorico = useMemo(() => {
    if (puntosHistoricosSvg.length === 0) return "";
    return puntosHistoricosSvg
      .map((p, i) => `${i === 0 ? "M" : "L"} ${p.x.toFixed(2)} ${p.y.toFixed(2)}`)
      .join(" ");
  }, [puntosHistoricosSvg]);

  // Área sombreada bajo la curva
  const areaHistorico = useMemo(() => {
    if (puntosHistoricosSvg.length === 0) return "";
    const first = puntosHistoricosSvg[0];
    const last = puntosHistoricosSvg[puntosHistoricosSvg.length - 1];
    return `${pathHistorico} L ${last.x.toFixed(2)} 95 L ${first.x.toFixed(2)} 95 Z`;
  }, [pathHistorico, puntosHistoricosSvg]);

  const ultimoPuntoHist = puntosHistoricosSvg[puntosHistoricosSvg.length - 1];
  const primerPuntoHist = puntosHistoricosSvg[0];

  const variacionHistorica = useMemo(() => {
    if (!primerPuntoHist || !ultimoPuntoHist || primerPuntoHist.valorModo === 0) return 0;
    return ((ultimoPuntoHist.valorModo - primerPuntoHist.valorModo) / primerPuntoHist.valorModo) * 100;
  }, [primerPuntoHist, ultimoPuntoHist]);

  // Etiquetas del Eje X temporal distribuidas
  const xLabels = useMemo(() => {
    if (historico.length === 0) return [];
    const cantidadLabels = 6;
    const indices = [0];
    const paso = (historico.length - 1) / (cantidadLabels - 1);
    for (let i = 1; i < cantidadLabels - 1; i++) {
      indices.push(Math.round(i * paso));
    }
    indices.push(historico.length - 1);

    return indices.map((idx) => {
      const p = historico[idx];
      const xPercent = (idx / Math.max(historico.length - 1, 1)) * 100;
      return {
        x: xPercent,
        label: p.dia || p.label,
        date: p.date,
      };
    });
  }, [historico]);

  return (
    <div className="space-y-6">
      <div className="rounded-3xl border border-[#dbe3ee] bg-white p-6 shadow-sm">
        {/* Cabecera del Panel */}
        <div className="mb-6 flex flex-col gap-4 xl:flex-row xl:items-center xl:justify-between">
          <div>
            <p className="text-sm font-medium text-[#64748b]">Evolución Financiera</p>
            <h2 className="text-2xl font-bold tracking-tight text-[#0f172a]">
              Gráfico de Evolución de Tasas
            </h2>
            <p className="mt-1 text-xs text-[#64748b]">
              Tasas históricas reales registradas en la casa de cambio.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            {/* Selector de Moneda */}
            <label className="flex items-center gap-2 rounded-xl border border-[#dbe3ee] bg-[#f8fafc] px-3.5 py-2">
              <span className="text-xs font-semibold uppercase tracking-[0.12em] text-[#64748b]">
                Moneda
              </span>
              <select
                value={currency}
                onChange={(e) => setCurrency(e.target.value)}
                className="bg-transparent text-sm font-semibold text-[#0f172a] outline-none cursor-pointer"
              >
                {codigos.map((cod) => (
                  <option key={cod} value={cod}>
                    {cod}
                  </option>
                ))}
              </select>
            </label>

            {/* Toggle Compra / Venta */}
            <div className="flex items-center rounded-xl border border-[#dbe3ee] bg-[#f8fafc] p-1 gap-1">
              <button
                onClick={() => setModoPrecio("venta")}
                className={`rounded-lg px-3.5 py-1.5 text-xs font-bold transition-all ${
                  modoPrecio === "venta"
                    ? "bg-[#1a7eff] text-white shadow-sm"
                    : "text-[#64748b] hover:text-[#0f172a]"
                }`}
              >
                Venta
              </button>
              <button
                onClick={() => setModoPrecio("compra")}
                className={`rounded-lg px-3.5 py-1.5 text-xs font-bold transition-all ${
                  modoPrecio === "compra"
                    ? "bg-[#1a7eff] text-white shadow-sm"
                    : "text-[#64748b] hover:text-[#0f172a]"
                }`}
              >
                Compra
              </button>
            </div>
          </div>
        </div>

        {error && (
          <div className="mb-4 rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-700">
            {error}
          </div>
        )}

        {/* Contenedor del Gráfico */}
        <div className="overflow-hidden rounded-2xl border border-[#e2e8f0] bg-[#f8fafc] p-5">
          {/* Métricas Superiores */}
          <div className="mb-4 flex flex-wrap items-end justify-between gap-4">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.12em] text-[#64748b]">
                Cotización {modoPrecio === "venta" ? "Venta" : "Compra"} ({currency})
              </p>
              <div className="mt-1 flex items-baseline gap-3">
                <h3 className="text-3xl font-extrabold text-[#0f172a]">
                  {formatPyg(ultimoPuntoHist?.valorModo ?? 0)}{" "}
                  <span className="text-base font-semibold text-[#64748b]">PYG</span>
                </h3>
                <span
                  className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-bold ${
                    variacionHistorica >= 0
                      ? "bg-emerald-100 text-emerald-800"
                      : "bg-red-100 text-red-800"
                  }`}
                >
                  {variacionHistorica >= 0 ? "+" : ""}
                  {variacionHistorica.toFixed(2)}% en {range}
                </span>
              </div>
            </div>

            {/* Leyenda Visual */}
            <div className="flex flex-wrap items-center gap-4 text-xs font-medium text-[#64748b]">
              <div className="flex items-center gap-1.5">
                <span className="h-2.5 w-5 rounded-full bg-[#1a7eff]" />
                <span>Histórico (al {datosEvolucion?.fechaActualFormateada || "hoy"})</span>
              </div>
            </div>
          </div>

          {/* Lienzo del Gráfico (SVG con Eje Y corregido) */}
          <div className="relative h-[360px] w-full overflow-hidden rounded-xl border border-[#dbe3ee] bg-gradient-to-br from-[#f8fafc] via-white to-[#f0f7ff]">
            {cargando ? (
              <div className="flex h-full w-full items-center justify-center text-sm font-semibold text-[#64748b]">
                Cargando cotizaciones históricas del backend...
              </div>
            ) : (
              <>
                {/* EJE Y (Valores de tasa ordenados: mayor arriba, menor abajo) */}
                <div className="absolute inset-y-0 left-0 flex w-20 flex-col justify-between py-4 pl-3 text-[10px] font-semibold text-[#64748b] select-none border-r border-[#edf2f7] bg-white/60 backdrop-blur-xs z-10">
                  {yTicks.map((tick) => (
                    <span key={tick.indice} className="tabular-nums">
                      {formatPyg(Math.round(tick.valor))}
                    </span>
                  ))}
                </div>

                {/* Área de Gráfica SVG */}
                <div className="absolute inset-y-0 left-20 right-0 top-0 bottom-6">
                  <svg
                    viewBox="0 0 100 100"
                    preserveAspectRatio="none"
                    className="h-full w-full overflow-visible"
                  >
                    <defs>
                      {/* Gradiente sutil para área histórica */}
                      <linearGradient id="areaGradiente" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor="#1a7eff" stopOpacity="0.25" />
                        <stop offset="100%" stopColor="#1a7eff" stopOpacity="0.0" />
                      </linearGradient>
                    </defs>

                    {/* Grilla horizontal de fondo (alineada con los 5 ticks del eje Y) */}
                    {yTicks.map((tick) => (
                      <line
                        key={tick.indice}
                        x1="0"
                        y1={tick.ySvg}
                        x2="100"
                        y2={tick.ySvg}
                        stroke="#dfeaf7"
                        strokeWidth="0.35"
                        strokeDasharray="2 2"
                      />
                    ))}

                    {/* Grilla vertical sutil */}
                    {[0, 20, 40, 60, 80, 100].map((x) => (
                      <line
                        key={x}
                        x1={x}
                        y1="10"
                        x2={x}
                        y2="90"
                        stroke="#f1f5f9"
                        strokeWidth="0.25"
                      />
                    ))}

                    {/* Área sombreada histórica */}
                    {areaHistorico && <path d={areaHistorico} fill="url(#areaGradiente)" />}

                    {/* Línea Histórica Principal (continua) */}
                    {pathHistorico && (
                      <path
                        d={pathHistorico}
                        fill="none"
                        stroke="#1a7eff"
                        strokeWidth="1.4"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                      />
                    )}

                    {/* Puntos Históricos */}
                    {puntosHistoricosSvg.map((p, idx) => (
                      <g
                        key={`h-${idx}`}
                        className="cursor-pointer"
                        onMouseEnter={() => setHoveredPoint(p)}
                        onMouseLeave={() => setHoveredPoint(null)}
                      >
                        <circle cx={p.x} cy={p.y} r="0.9" fill="#1a7eff" />
                        {idx === puntosHistoricosSvg.length - 1 && (
                          <>
                            <circle
                              cx={p.x}
                              cy={p.y}
                              r="3.5"
                              fill="#1a7eff"
                              fillOpacity="0.2"
                              className="animate-ping"
                            />
                            <circle cx={p.x} cy={p.y} r="1.6" fill="#1a7eff" stroke="#fff" strokeWidth="0.4" />
                          </>
                        )}
                      </g>
                    ))}
                  </svg>

                  {/* Tooltip flotante al pasar el cursor */}
                  {hoveredPoint && (
                    <div
                      className="pointer-events-none absolute -top-2 z-20 -translate-x-1/2 rounded-lg border border-[#dbe3ee] bg-white px-2.5 py-1.5 shadow-md"
                      style={{
                        left: `${(historico.findIndex((p) => p.date === hoveredPoint.date) / Math.max(historico.length - 1, 1)) * 100}%`,
                      }}
                    >
                      <p className="text-[10px] font-semibold text-[#64748b]">
                        {formatDateShort(hoveredPoint.date)}
                      </p>
                      <p className="font-mono text-xs font-bold text-[#0f172a]">
                        {formatPyg(getValorPunto(hoveredPoint, modoPrecio))} PYG
                      </p>
                      <p className="text-[9px] text-[#64748b] capitalize">{modoPrecio}</p>
                    </div>
                  )}
                </div>

                {/* EJE X (Fechas dinámicas y actualizadas en la parte inferior) */}
                <div className="absolute inset-x-0 bottom-0 left-20 flex justify-between px-2 pb-1 text-[10px] font-semibold text-[#64748b] border-t border-[#edf2f7] bg-white/80">
                  {xLabels.map((lbl, idx) => (
                    <span key={idx} className="truncate">
                      {lbl.label}
                    </span>
                  ))}
                </div>
              </>
            )}
          </div>

          {/* Selector de Rango (Botones 1M, 6M, YTD, 1A, MÁX - Sin 1D ni 5D) */}
          <div className="mt-5 flex flex-wrap items-center justify-between gap-3">
            <div className="flex flex-wrap items-center gap-2">
              <span className="mr-1 text-xs font-semibold text-[#64748b]">Período:</span>
              {RANGE_OPTIONS.map((option) => (
                <button
                  key={option}
                  onClick={() => setRange(option)}
                  className={`rounded-full px-4 py-1.5 text-xs font-bold transition-all ${
                    range === option
                      ? "bg-[#1a7eff] text-white shadow-sm ring-2 ring-[#1a7eff]/30"
                      : "bg-white text-[#475569] ring-1 ring-[#dbe3ee] hover:bg-[#f8fafc] hover:text-[#0f172a]"
                  }`}
                >
                  {option}
                </button>
              ))}
            </div>

            <p className="text-xs text-[#64748b]">
              Período visualizado:{" "}
              <strong className="text-[#0f172a]">
                {datosEvolucion?.rangoFechas.inicio ?? "13/10/2026"}
              </strong>{" "}
              al{" "}
              <strong className="text-[#0f172a]">
                {datosEvolucion?.fechaActualFormateada ?? "13/11/2026"}
              </strong>
            </p>
          </div>
        </div>

        {/* Tarjetas de Resumen — 3 columnas (sin proyección) */}
        <div className="mt-5 grid gap-3 md:grid-cols-3">
          <div className="rounded-2xl border border-[#e2e8f0] bg-white p-4">
            <p className="text-xs uppercase tracking-[0.12em] text-[#64748b]">Fecha Actual</p>
            <p className="mt-2 text-sm font-bold text-[#0f172a]">
              {datosEvolucion?.fechaActualFormateada ?? "13/11/2026"}
            </p>
            <p className="mt-0.5 text-[11px] text-[#64748b]">Cierre de mercado</p>
          </div>

          <div className="rounded-2xl border border-[#e2e8f0] bg-white p-4">
            <p className="text-xs uppercase tracking-[0.12em] text-[#64748b]">Tasa Venta Vigente</p>
            <p className="mt-2 text-sm font-bold text-[#1a7eff]">
              1 {currency} = {formatPyg(datosEvolucion?.valorActual ?? 0)} PYG
            </p>
            <p className="mt-0.5 text-[11px] text-[#64748b]">Tasa activa en ventanilla</p>
          </div>

          <div className="rounded-2xl border border-[#e2e8f0] bg-white p-4">
            <p className="text-xs uppercase tracking-[0.12em] text-[#64748b]">Tasa Compra Vigente</p>
            <p className="mt-2 text-sm font-bold text-[#0f172a]">
              1 {currency} = {formatPyg(datosEvolucion?.valorCompraActual ?? 0)} PYG
            </p>
            <p className="mt-0.5 text-[11px] text-[#64748b]">Spread comercial</p>
          </div>
        </div>
      </div>
    </div>
  );
}
