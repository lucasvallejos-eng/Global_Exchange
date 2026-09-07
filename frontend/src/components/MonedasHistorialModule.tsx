import { useEffect, useMemo, useState } from "react";
import { listarHistorial } from "../lib/cotizacionesApi";
import { useTasas } from "../lib/useTasas";

type ChartMode = "Línea" | "Vela";
type RangeOption = "1D" | "5D" | "1M" | "6M" | "YTD" | "1A" | "5A" | "MÁX";


const RANGE_OPTIONS: RangeOption[] = ["1D", "5D", "1M", "6M", "YTD", "1A", "5A", "MÁX"];

const formatPyg = (value: number) =>
  new Intl.NumberFormat("es-PY", {
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(value);

const formatDate = (dateStr: string) =>
  new Date(dateStr).toLocaleDateString("es-PY", {
    day: "numeric",
    month: "long",
    year: "numeric",
  });

export default function MonedasHistorialModule() {
  const [currency, setCurrency] = useState<string>("");
  const [range, setRange] = useState<RangeOption>("1A");

  // Las monedas disponibles y el historial salen de la base.
  const { codigos } = useTasas();
  const [baseSeries, setBaseSeries] = useState<{ date: string; label: string; value: number }[]>([]);
  const [cargando, setCargando] = useState(true);

  useEffect(() => {
    if (!currency && codigos.length > 0) setCurrency(codigos[0]);
  }, [codigos, currency]);

  useEffect(() => {
    if (!currency) return;
    let vigente = true;
    setCargando(true);

    listarHistorial(currency)
      .then((cotizaciones) => {
        if (!vigente) return;
        // El grafico va de la mas vieja a la mas nueva; la API las manda al reves.
        const serie = [...cotizaciones].reverse().map((c) => {
          const fecha = new Date(c.fecha);
          return {
            date: c.fecha,
            label: fecha.toLocaleDateString("es-PY", { month: "short", year: "numeric" }),
            value: c.precioVenta,
          };
        });
        setBaseSeries(serie);
      })
      .catch(() => {
        if (vigente) setBaseSeries([]);
      })
      .finally(() => {
        if (vigente) setCargando(false);
      });

    return () => {
      vigente = false;
    };
  }, [currency]);

  const filteredData = useMemo(() => {
    if (range === "MÁX") return baseSeries;
    if (range === "1A") return baseSeries.slice(-12);
    if (range === "5A") return baseSeries;
    if (range === "YTD") return baseSeries.slice(-8);
    if (range === "6M") return baseSeries.slice(-6);
    if (range === "1M") return baseSeries.slice(-4);
    if (range === "5D") return baseSeries.slice(-5);
    if (range === "1D") return baseSeries.slice(-2);
    return baseSeries.slice(-12);
  }, [baseSeries, range]);

  const chartPoints = useMemo(() => {
    const values = filteredData.map((point) => point.value);
    const minValue = Math.min(...values);
    const maxValue = Math.max(...values);
    const padding = Math.max((maxValue - minValue) * 0.15, 100);

    return filteredData.map((point, index) => {
      const x = (index / Math.max(filteredData.length - 1, 1)) * 100;
      const y = 100 - ((point.value - (minValue - padding)) / Math.max(maxValue - minValue + padding * 2, 1)) * 100;
      return { ...point, x, y };
    });
  }, [filteredData]);

  const lastPoint = chartPoints[chartPoints.length - 1];
  const firstPoint = chartPoints[0];
  const linePath = chartPoints
    .map((point, index) => `${index === 0 ? "M" : "L"}${point.x},${point.y}`)
    .join(" ");

  const priceDelta = firstPoint && lastPoint ? ((lastPoint.value - firstPoint.value) / firstPoint.value) * 100 : 0;

  const yTicks = [0, 25, 50, 75, 100].map((tick) => {
    const value = (100 - tick) / 100;
    const min = Math.min(...filteredData.map((point) => point.value));
    const max = Math.max(...filteredData.map((point) => point.value));
    const padding = Math.max((max - min) * 0.15, 100);
    const tickValue = max - (value * (max - min + padding * 2)) + padding;
    return { tick, value: tickValue };
  });

  return (
    <div className="space-y-6">
      <div className="rounded-3xl border border-[#dbe3ee] bg-white p-6 shadow-sm">
        <div className="mb-5 flex flex-col gap-4 xl:flex-row xl:items-center xl:justify-between">
          <div>
            <p className="text-sm font-medium text-[#64748b]">Historial de Monedas</p>
            <h2 className="text-2xl font-bold tracking-tight text-[#0f172a]">Cotizaciones históricas</h2>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <label className="flex items-center gap-2 rounded-xl border border-[#dbe3ee] bg-[#f8fafc] px-3 py-2">
              <span className="text-xs font-semibold uppercase tracking-[0.12em] text-[#64748b]">Moneda</span>
              <select
                value={currency}
                onChange={(e) => setCurrency(e.target.value)}
                className="bg-transparent text-sm font-semibold text-[#0f172a] outline-none"
              >
                {codigos.map((option) => (
                  <option key={option} value={option}>{option}</option>
                ))}
              </select>
            </label>
          </div>
        </div>

        <div className="overflow-hidden rounded-2xl border border-[#e2e8f0] bg-[#f8fafc] p-4">
          <div className="mb-3 flex items-center justify-between gap-4">
            <div>
              <p className="text-xs uppercase tracking-[0.12em] text-[#64748b]">Valor actual</p>
              <h3 className="mt-2 text-3xl font-bold text-[#0f172a]">{formatPyg(lastPoint?.value ?? 0)} PYG</h3>
            </div>
            <div className="rounded-full bg-[#eaf3ff] px-3 py-1.5 text-sm font-semibold text-[#1a7eff]">
              {priceDelta >= 0 ? "+" : ""}{priceDelta.toFixed(1)}%
            </div>
          </div>

          <div className="relative h-[360px] w-full overflow-hidden rounded-xl border border-[#dbe3ee] bg-gradient-to-br from-[#f8fafc] via-white to-[#f0f7ff]">
            <div className="absolute inset-y-0 left-0 flex w-16 flex-col justify-between py-4 pl-2 text-[10px] font-medium text-[#64748b]">
              {yTicks.map((tick) => (
                <span key={tick.tick}>{formatPyg(Math.round(tick.value))}</span>
              ))}
            </div>

            <div className="absolute bottom-0 left-16 right-0 top-0">
              <svg viewBox="0 0 100 100" preserveAspectRatio="none" className="h-full w-full">
                {[0, 25, 50, 75, 100].map((y) => (
                  <line key={y} x1="0" y1={y} x2="100" y2={y} stroke="#dfeaf7" strokeWidth="0.35" />
                ))}
                {[0, 20, 40, 60, 80, 100].map((x) => (
                  <line key={x} x1={x} y1="0" x2={x} y2="100" stroke="#dfeaf7" strokeWidth="0.25" />
                ))}

                <path d={linePath} fill="none" stroke="#1a7eff" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round" />

                {chartPoints.map((point, index) => (
                  <g key={point.date}>
                    <circle cx={point.x} cy={point.y} r="0.9" fill="#1a7eff" />
                    {index === chartPoints.length - 1 && (
                      <>
                        <circle cx={point.x} cy={point.y} r="3" fill="#1a7eff" fillOpacity="0.18" />
                        <circle cx={point.x} cy={point.y} r="1.5" fill="#1a7eff" />
                      </>
                    )}
                  </g>
                ))}
              </svg>

              <div className="absolute inset-x-0 bottom-0 flex justify-between px-4 pb-2 text-[10px] font-medium text-[#64748b]">
                {filteredData.map((point) => (
                  <span key={point.date} className="w-0 flex-1 text-center">{point.label.replace(/\s\d{4}/, "")}</span>
                ))}
              </div>
            </div>
          </div>

          <div className="mt-4 flex flex-wrap gap-2">
            {RANGE_OPTIONS.map((option) => (
              <button
                key={option}
                onClick={() => setRange(option)}
                className={`rounded-full px-3 py-1.5 text-xs font-semibold transition ${
                  range === option
                    ? "bg-[#1a7eff] text-white shadow-sm"
                    : "bg-white text-[#475569] ring-1 ring-[#dbe3ee] hover:bg-[#f8fafc]"
                }`}
              >
                {option}
              </button>
            ))}
          </div>
        </div>

        <div className="mt-5 grid gap-3 md:grid-cols-3">
          <div className="rounded-2xl border border-[#e2e8f0] bg-white p-4">
            <p className="text-xs uppercase tracking-[0.12em] text-[#64748b]">Fecha</p>
            <p className="mt-2 text-sm font-semibold text-[#0f172a]">{formatDate(lastPoint?.date ?? new Date().toISOString())}</p>
          </div>
          <div className="rounded-2xl border border-[#e2e8f0] bg-white p-4">
            <p className="text-xs uppercase tracking-[0.12em] text-[#64748b]">Cotización</p>
            <p className="mt-2 text-sm font-semibold text-[#0f172a]">1 {currency} = {formatPyg(lastPoint?.value ?? 0)} PYG</p>
          </div>
          <div className="rounded-2xl border border-[#e2e8f0] bg-white p-4">
            <p className="text-xs uppercase tracking-[0.12em] text-[#64748b]">Rango</p>
            <p className="mt-2 text-sm font-semibold text-[#0f172a]">{range}</p>
          </div>
        </div>
      </div>
    </div>
  );
}
