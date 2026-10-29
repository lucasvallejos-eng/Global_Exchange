import { useEffect, useMemo, useState } from "react";

import { reporteGanancias, type FiltrosReporte, type Ganancias, type Totales } from "../lib/reportesApi";

// Tablero de control de ganancias (administrador y analista cambiario).
// Los números los calcula el backend sobre las operaciones pagadas; acá solo
// se eligen el período y cómo agrupar los días para que el gráfico se lea.

const AZUL = "#1a7eff";

const formatPyg = (value: number) =>
  new Intl.NumberFormat("es-PY", { maximumFractionDigits: 0 }).format(value);

const formatCompacto = (value: number) =>
  new Intl.NumberFormat("es-PY", { notation: "compact", maximumFractionDigits: 1 }).format(value);

// Fecha local en AAAA-MM-DD (toISOString la daría en UTC y de noche cambia el día).
const aTexto = (fecha: Date) =>
  `${fecha.getFullYear()}-${String(fecha.getMonth() + 1).padStart(2, "0")}-${String(fecha.getDate()).padStart(2, "0")}`;

const deTexto = (texto: string) => {
  const [anio, mes, dia] = texto.split("-").map(Number);
  return new Date(anio, mes - 1, dia);
};

type Periodo = "7" | "30" | "90" | "anio" | "todo";

const PERIODOS: { id: Periodo; texto: string }[] = [
  { id: "7", texto: "7 días" },
  { id: "30", texto: "30 días" },
  { id: "90", texto: "90 días" },
  { id: "anio", texto: "Este año" },
  { id: "todo", texto: "Todo" },
];

function filtrosDe(periodo: Periodo): FiltrosReporte {
  const hoy = new Date();
  if (periodo === "todo") return {};
  if (periodo === "anio") return { desde: `${hoy.getFullYear()}-01-01`, hasta: aTexto(hoy) };
  const desde = new Date(hoy);
  desde.setDate(hoy.getDate() - (Number(periodo) - 1));
  return { desde: aTexto(desde), hasta: aTexto(hoy) };
}

type Punto = { clave: string; etiqueta: string; ganancia: number; operaciones: number };

/** Junta los días en semanas o meses cuando son demasiados para una columna cada uno. */
function agrupar(porDia: Ganancias["porDia"]): { puntos: Punto[]; unidad: string } {
  const unidad = porDia.length > 200 ? "mes" : porDia.length > 45 ? "semana" : "día";
  const grupos = new Map<string, Punto>();
  porDia.forEach((dia) => {
    const fecha = deTexto(dia.fecha);
    let clave = dia.fecha;
    let etiqueta = fecha.toLocaleDateString("es-PY", { day: "2-digit", month: "2-digit" });
    if (unidad === "mes") {
      clave = dia.fecha.slice(0, 7);
      etiqueta = fecha.toLocaleDateString("es-PY", { month: "short", year: "2-digit" });
    } else if (unidad === "semana") {
      const lunes = new Date(fecha);
      lunes.setDate(fecha.getDate() - ((fecha.getDay() + 6) % 7));
      clave = aTexto(lunes);
      etiqueta = `Sem. ${lunes.toLocaleDateString("es-PY", { day: "2-digit", month: "2-digit" })}`;
    }
    const grupo = grupos.get(clave) ?? { clave, etiqueta, ganancia: 0, operaciones: 0 };
    grupo.ganancia += dia.ganancia;
    grupo.operaciones += dia.operaciones;
    grupos.set(clave, grupo);
  });
  return { puntos: [...grupos.values()], unidad };
}

/** Marcas redondas para el eje (0, 50.000, 100.000...) que cubren de `min` a `max`. */
function marcas(min: number, max: number): number[] {
  if (min === max) return [0, 1];
  const bruto = (max - min) / 4;
  const potencia = 10 ** Math.floor(Math.log10(bruto));
  const paso = [1, 2, 2.5, 5, 10].map((m) => m * potencia).find((p) => p >= bruto) ?? bruto;
  const lista: number[] = [];
  for (let valor = Math.floor(min / paso) * paso; valor <= Math.ceil(max / paso) * paso + paso / 2; valor += paso) {
    lista.push(Math.round(valor));
  }
  return lista;
}

const ANCHO = 720;
const ALTO = 260;
const MARGEN = { izquierda: 56, derecha: 12, arriba: 12, abajo: 28 };

function GraficoGanancia({ puntos, unidad }: { puntos: Punto[]; unidad: string }) {
  const [activo, setActivo] = useState<number | null>(null);

  const valores = puntos.map((p) => p.ganancia);
  const eje = marcas(Math.min(0, ...valores), Math.max(0, ...valores));
  const [minimo, maximo] = [eje[0], eje[eje.length - 1]];
  const altoUtil = ALTO - MARGEN.arriba - MARGEN.abajo;
  const anchoUtil = ANCHO - MARGEN.izquierda - MARGEN.derecha;
  const y = (valor: number) => MARGEN.arriba + ((maximo - valor) / (maximo - minimo)) * altoUtil;
  const banda = anchoUtil / puntos.length;
  // Columnas finas: nunca llenan la banda, y entre vecinas quedan 2px de aire.
  const grosor = Math.max(1, Math.min(24, banda - 2));
  // Pocas etiquetas en el eje: las demás se leen pasando el mouse.
  const cada = Math.max(1, Math.ceil(puntos.length / 7));

  const columna = (indice: number, valor: number) => {
    const x = MARGEN.izquierda + indice * banda + (banda - grosor) / 2;
    const base = y(0);
    const punta = y(valor);
    // Punta redondeada, base recta sobre la línea de cero.
    const radio = Math.min(4, grosor / 2, Math.abs(punta - base));
    const haciaBase = valor >= 0 ? radio : -radio;
    return [
      `M ${x} ${base}`,
      `L ${x} ${punta + haciaBase}`,
      `Q ${x} ${punta} ${x + radio} ${punta}`,
      `L ${x + grosor - radio} ${punta}`,
      `Q ${x + grosor} ${punta} ${x + grosor} ${punta + haciaBase}`,
      `L ${x + grosor} ${base} Z`,
    ].join(" ");
  };

  const punto = activo !== null ? puntos[activo] : null;

  return (
    <div className="relative" onMouseLeave={() => setActivo(null)}>
      <svg viewBox={`0 0 ${ANCHO} ${ALTO}`} className="w-full" role="img"
           aria-label={`Ganancia por ${unidad}, en guaraníes`}>
        {eje.map((valor) => (
          <g key={valor}>
            <line x1={MARGEN.izquierda} x2={ANCHO - MARGEN.derecha} y1={y(valor)} y2={y(valor)}
                  stroke={valor === 0 ? "#94a3b8" : "#e2e8f0"} strokeWidth={1} />
            <text x={MARGEN.izquierda - 8} y={y(valor) + 4} textAnchor="end" fontSize={11} fill="#64748b">
              {formatCompacto(valor)}
            </text>
          </g>
        ))}
        {puntos.map((p, indice) => (
          <g key={p.clave}>
            {p.ganancia !== 0 && (
              <path d={columna(indice, p.ganancia)} fill={AZUL} opacity={activo === null || activo === indice ? 1 : 0.45} />
            )}
            {indice % cada === 0 && (
              <text x={MARGEN.izquierda + indice * banda + banda / 2} y={ALTO - 8} textAnchor="middle" fontSize={11} fill="#64748b">
                {p.etiqueta}
              </text>
            )}
            {/* Zona de hover: toda la banda, no solo la columna. */}
            <rect x={MARGEN.izquierda + indice * banda} y={MARGEN.arriba} width={banda} height={altoUtil}
                  fill="transparent" onMouseEnter={() => setActivo(indice)} />
          </g>
        ))}
      </svg>
      {punto && activo !== null && (
        <div
          className="pointer-events-none absolute z-10 -translate-x-1/2 rounded-lg border border-[#e2e8f0] bg-white px-3 py-2 text-xs shadow-md"
          style={{ left: `${((MARGEN.izquierda + activo * banda + banda / 2) / ANCHO) * 100}%`, top: 0 }}
        >
          <p className="font-semibold text-[#0f172a]">{punto.etiqueta}</p>
          <p className="text-[#475569]">Ganancia: {formatPyg(punto.ganancia)} PYG</p>
          <p className="text-[#475569]">Operaciones: {punto.operaciones}</p>
        </div>
      )}
    </div>
  );
}

function Tarjeta({ etiqueta, valor, detalle }: { etiqueta: string; valor: string; detalle?: string }) {
  return (
    <div className="rounded-2xl border border-[#e2e8f0] bg-white px-5 py-4 shadow-sm">
      <p className="text-sm font-medium text-[#64748b]">{etiqueta}</p>
      <p className="mt-1 text-2xl font-semibold text-[#0f172a]">{valor}</p>
      {detalle && <p className="mt-1 text-xs text-[#64748b]">{detalle}</p>}
    </div>
  );
}

const promedio = (totales: Totales) => (totales.operaciones ? totales.ganancia / totales.operaciones : 0);

export default function TableroGananciasModule() {
  const [periodo, setPeriodo] = useState<Periodo>("30");
  const [datos, setDatos] = useState<Ganancias | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let vigente = true;
    setError("");
    reporteGanancias(filtrosDe(periodo))
      .then((respuesta) => vigente && setDatos(respuesta))
      .catch((e: Error) => vigente && setError(e.message));
    return () => {
      vigente = false;
    };
  }, [periodo]);

  const serie = useMemo(() => agrupar(datos?.porDia ?? []), [datos]);

  // Las barras por moneda comparten escala; el cero se corre si hay pérdidas.
  const monedas = datos?.porMoneda ?? [];
  const minimo = Math.min(0, ...monedas.map((m) => m.ganancia));
  const maximo = Math.max(0, ...monedas.map((m) => m.ganancia));
  const rango = maximo - minimo || 1;
  const cero = ((0 - minimo) / rango) * 100;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="text-sm font-medium text-[#64748b]">Tablero de control</p>
          <h2 className="text-2xl font-bold tracking-tight text-[#0f172a]">Ganancias</h2>
        </div>
        <div className="flex flex-wrap gap-1 rounded-xl border border-[#dbe3ee] bg-white p-1">
          {PERIODOS.map((opcion) => (
            <button
              key={opcion.id}
              onClick={() => setPeriodo(opcion.id)}
              className={`rounded-lg px-3 py-1.5 text-sm font-semibold ${
                periodo === opcion.id ? "bg-[#1a7eff] text-white" : "text-[#475569] hover:bg-[#f1f5f9]"
              }`}
            >
              {opcion.texto}
            </button>
          ))}
        </div>
      </div>

      {error && <p className="text-sm font-medium text-red-600">{error}</p>}

      {!datos ? (
        <p className="text-sm text-[#64748b]">Cargando el tablero...</p>
      ) : (
        <>
          <div className="grid gap-4 lg:grid-cols-[1.4fr_1fr_1fr_1fr]">
            <div className="rounded-2xl border border-[#e2e8f0] bg-white px-5 py-4 shadow-sm">
              <p className="text-sm font-medium text-[#64748b]">Ganancia del período</p>
              <p className="mt-1 text-5xl font-semibold tracking-tight text-[#0f172a]">
                {formatPyg(datos.totales.ganancia)}
                <span className="ml-2 text-lg font-medium text-[#64748b]">PYG</span>
              </p>
              <p className="mt-2 text-xs text-[#64748b]">
                Comisiones {formatPyg(datos.totales.comisiones)} · Margen de cambio {formatPyg(datos.totales.margen)}
              </p>
            </div>
            <Tarjeta etiqueta="Operaciones pagadas" valor={formatPyg(datos.totales.operaciones)}
                     detalle={`${datos.porTipo.COMPRA.operaciones} compras · ${datos.porTipo.VENTA.operaciones} ventas`} />
            <Tarjeta etiqueta="Volumen operado" valor={`${formatCompacto(datos.totales.volumen)} PYG`}
                     detalle={`${formatPyg(datos.totales.volumen)} PYG`} />
            <Tarjeta etiqueta="Ganancia por operación" valor={`${formatPyg(promedio(datos.totales))} PYG`}
                     detalle="Promedio del período" />
          </div>

          <div className="rounded-3xl border border-[#dbe3ee] bg-white p-6 shadow-sm">
            <h3 className="text-base font-semibold text-[#0f172a]">Ganancia por {serie.unidad}</h3>
            <p className="mb-4 text-xs text-[#64748b]">En guaraníes, por fecha de pago.</p>
            {datos.totales.operaciones === 0 ? (
              <div className="flex min-h-[180px] items-center justify-center rounded-2xl border border-dashed border-[#dbe3ee] bg-[#f8fafc]">
                <p className="text-sm font-medium text-[#64748b]">No hay operaciones pagadas en este período.</p>
              </div>
            ) : (
              <GraficoGanancia puntos={serie.puntos} unidad={serie.unidad} />
            )}
          </div>

          <div className="grid gap-4 lg:grid-cols-[1.6fr_1fr]">
            <div className="rounded-3xl border border-[#dbe3ee] bg-white p-6 shadow-sm">
              <h3 className="mb-4 text-base font-semibold text-[#0f172a]">Ganancia por moneda</h3>
              {monedas.length === 0 ? (
                <p className="text-sm text-[#64748b]">Sin operaciones en este período.</p>
              ) : (
                <table className="w-full border-collapse text-sm text-[#1f2937]">
                  <thead className="text-left text-xs text-[#64748b]">
                    <tr>
                      <th className="pb-2 pr-4 font-medium">Moneda</th>
                      <th className="pb-2 font-medium">Ganancia (PYG)</th>
                      <th className="pb-2 text-right font-medium" />
                      <th className="pb-2 pl-4 text-right font-medium">Operaciones</th>
                      <th className="pb-2 pl-4 text-right font-medium">Volumen (PYG)</th>
                    </tr>
                  </thead>
                  <tbody>
                    {monedas.map((moneda) => (
                      <tr key={moneda.moneda} className="border-t border-[#edf2f7]">
                        <td className="py-2.5 pr-4 font-semibold text-[#0f172a]">{moneda.moneda}</td>
                        <td className="w-[35%] py-2.5">
                          <div className="relative h-4">
                            <div className="absolute inset-y-0 w-px bg-[#94a3b8]" style={{ left: `${cero}%` }} />
                            <div
                              className={`absolute inset-y-0 ${moneda.ganancia >= 0 ? "rounded-r" : "rounded-l"}`}
                              style={{
                                background: AZUL,
                                left: `${moneda.ganancia >= 0 ? cero : ((moneda.ganancia - minimo) / rango) * 100}%`,
                                width: `${(Math.abs(moneda.ganancia) / rango) * 100}%`,
                              }}
                            />
                          </div>
                        </td>
                        <td className="py-2.5 pl-3 text-right font-medium tabular-nums">{formatPyg(moneda.ganancia)}</td>
                        <td className="py-2.5 pl-4 text-right tabular-nums text-[#475569]">{moneda.operaciones}</td>
                        <td className="whitespace-nowrap py-2.5 pl-4 text-right tabular-nums text-[#475569]">{formatPyg(moneda.volumen)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>

            <div className="space-y-4">
              <Tarjeta etiqueta="Compras de clientes (la casa vende)"
                       valor={`${formatPyg(datos.porTipo.COMPRA.ganancia)} PYG`}
                       detalle={`${datos.porTipo.COMPRA.operaciones} operaciones · volumen ${formatPyg(datos.porTipo.COMPRA.volumen)} PYG`} />
              <Tarjeta etiqueta="Ventas de clientes (la casa compra)"
                       valor={`${formatPyg(datos.porTipo.VENTA.ganancia)} PYG`}
                       detalle={`${datos.porTipo.VENTA.operaciones} operaciones · volumen ${formatPyg(datos.porTipo.VENTA.volumen)} PYG`} />
            </div>
          </div>
        </>
      )}
    </div>
  );
}
