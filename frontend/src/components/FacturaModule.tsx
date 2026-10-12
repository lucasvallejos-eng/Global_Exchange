import { useEffect, useMemo, useState } from "react";

import {
  actualizarFactura,
  listarFacturas,
  reintentarFactura,
  urlDescarga,
  type EstadoFactura,
  type Factura,
} from "../lib/facturasApi";

const formatPyg = (value: number) =>
  new Intl.NumberFormat("es-PY", {
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(value);

const formatFecha = (iso: string) => new Date(iso).toLocaleDateString("es-PY");

const estadoColors: Record<EstadoFactura, string> = {
  SIMULADA: "bg-slate-100 text-slate-600",
  ENVIADA: "bg-yellow-100 text-yellow-700",
  SIN_CONFIRMAR: "bg-yellow-100 text-yellow-700",
  APROBADA: "bg-green-100 text-green-700",
  ERROR: "bg-red-100 text-red-700",
  RECHAZADA: "bg-red-100 text-red-700",
  CANCELADA: "bg-red-100 text-red-700",
};

const ESTADOS: { valor: EstadoFactura; texto: string }[] = [
  { valor: "APROBADA", texto: "Aprobada" },
  { valor: "ENVIADA", texto: "Enviada" },
  { valor: "SIMULADA", texto: "Simulada" },
  { valor: "RECHAZADA", texto: "Rechazada" },
  { valor: "ERROR", texto: "No se pudo emitir" },
  { valor: "SIN_CONFIRMAR", texto: "Sin confirmar" },
  { valor: "CANCELADA", texto: "Cancelada" },
];

export default function FacturaModule() {
  const [facturas, setFacturas] = useState<Factura[]>([]);
  const [emision, setEmision] = useState<"real" | "simulada">("simulada");
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState("");
  const [search, setSearch] = useState("");
  const [estadoFilter, setEstadoFilter] = useState<"Todos" | EstadoFactura>("Todos");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [page, setPage] = useState(1);
  const pageSize = 10;

  useEffect(() => {
    listarFacturas()
      .then((datos) => {
        setFacturas(datos.facturas);
        setEmision(datos.emision);
      })
      .catch((e: Error) => setError(e.message))
      .finally(() => setCargando(false));
  }, []);

  const filteredFacturas = useMemo(() => {
    const texto = search.toLowerCase();
    return facturas.filter((factura) => {
      const matchesSearch =
        factura.numero.toLowerCase().includes(texto) || factura.cliente.toLowerCase().includes(texto);
      const matchesEstado = estadoFilter === "Todos" || factura.estado === estadoFilter;

      // Las dos en AAAA-MM-DD: se comparan como texto.
      const facturaDate = factura.fecha.slice(0, 10);
      const fromOk = !dateFrom || facturaDate >= dateFrom;
      const toOk = !dateTo || facturaDate <= dateTo;

      return matchesSearch && matchesEstado && fromOk && toOk;
    });
  }, [dateFrom, dateTo, estadoFilter, facturas, search]);

  const totalPages = Math.max(1, Math.ceil(filteredFacturas.length / pageSize));
  const safePage = Math.min(page, totalPages);

  const paginatedFacturas = filteredFacturas.slice((safePage - 1) * pageSize, safePage * pageSize);

  // El archivo lo baja el backend de Factura Segura: acá solo se abre el enlace.
  const handleDownload = (formato: "kude" | "xml", factura: Factura) => {
    window.open(urlDescarga(factura.id, formato), "_blank");
  };

  const reemplazar = (pedido: Promise<Factura>) => {
    setError("");
    pedido
      .then((nueva) => setFacturas((lista) => lista.map((f) => (f.id === nueva.id ? nueva : f))))
      .catch((e: Error) => setError(e.message));
  };

  return (
    <div className="space-y-6">
      <div className="rounded-3xl border border-[#dbe3ee] bg-white p-6 shadow-sm">
        <div className="mb-5">
          <p className="text-sm font-medium text-[#64748b]">Facturación</p>
          <h2 className="text-2xl font-bold tracking-tight text-[#0f172a]">Facturas</h2>
          {emision === "simulada" && (
            <p className="mt-1 text-sm text-[#64748b]">
              La emisión está apagada: las facturas quedan simuladas y no gastan números.
            </p>
          )}
          {error && <p className="mt-2 text-sm font-medium text-red-600">{error}</p>}
        </div>

        <div className="mb-5 grid gap-3 lg:grid-cols-[1.4fr_0.8fr_1fr_1fr]">
          <label className="block">
            <span className="mb-2 block text-xs font-semibold uppercase tracking-[0.12em] text-[#64748b]">
              Buscar factura
            </span>
            <input
              value={search}
              onChange={(event) => {
                setSearch(event.target.value);
                setPage(1);
              }}
              placeholder="001-003-0000382 o cliente"
              className="w-full rounded-xl border border-[#dbe3ee] bg-[#f8fafc] px-3 py-2.5 text-sm text-[#1f2937] outline-none focus:border-[#1a7eff]"
            />
          </label>

          <label className="block">
            <span className="mb-2 block text-xs font-semibold uppercase tracking-[0.12em] text-[#64748b]">
              Estado
            </span>
            <select
              value={estadoFilter}
              onChange={(event) => {
                setEstadoFilter(event.target.value as "Todos" | EstadoFactura);
                setPage(1);
              }}
              className="w-full rounded-xl border border-[#dbe3ee] bg-[#f8fafc] px-3 py-2.5 text-sm text-[#1f2937] outline-none focus:border-[#1a7eff]"
            >
              <option value="Todos">Todos</option>
              {ESTADOS.map((estado) => (
                <option key={estado.valor} value={estado.valor}>{estado.texto}</option>
              ))}
            </select>
          </label>

          <label className="block">
            <span className="mb-2 block text-xs font-semibold uppercase tracking-[0.12em] text-[#64748b]">
              Desde
            </span>
            <input
              type="date"
              value={dateFrom}
              onChange={(event) => {
                setDateFrom(event.target.value);
                setPage(1);
              }}
              className="w-full rounded-xl border border-[#dbe3ee] bg-[#f8fafc] px-3 py-2.5 text-sm text-[#1f2937] outline-none focus:border-[#1a7eff]"
            />
          </label>

          <label className="block">
            <span className="mb-2 block text-xs font-semibold uppercase tracking-[0.12em] text-[#64748b]">
              Hasta
            </span>
            <input
              type="date"
              value={dateTo}
              onChange={(event) => {
                setDateTo(event.target.value);
                setPage(1);
              }}
              className="w-full rounded-xl border border-[#dbe3ee] bg-[#f8fafc] px-3 py-2.5 text-sm text-[#1f2937] outline-none focus:border-[#1a7eff]"
            />
          </label>
        </div>

        {filteredFacturas.length === 0 ? (
          <div className="flex min-h-[220px] items-center justify-center rounded-2xl border border-dashed border-[#dbe3ee] bg-[#f8fafc]">
            <div className="text-center">
              <p className="text-lg font-semibold text-[#0f172a]">
                {cargando ? "Cargando facturas..." : "Aún no hay facturas. Se genera una por cada operación pagada."}
              </p>
            </div>
          </div>
        ) : (
          <>
            <div className="overflow-hidden rounded-2xl border border-[#e2e8f0]">
              <table className="min-w-full border-collapse bg-white text-left text-sm text-[#1f2937]">
                <thead className="bg-[#f8fafc] text-[#475569]">
                  <tr>
                    <th className="px-4 py-3 font-semibold">Número de Factura</th>
                    <th className="px-4 py-3 font-semibold">Cliente</th>
                    <th className="px-4 py-3 font-semibold">Estado de Factura</th>
                    <th className="px-4 py-3 font-semibold">Fecha</th>
                    <th className="px-4 py-3 text-right font-semibold">Monto en PYG</th>
                    <th className="px-4 py-3 text-center font-semibold">Acciones / Descarga</th>
                  </tr>
                </thead>
                <tbody>
                  {paginatedFacturas.map((factura) => (
                    <tr key={factura.id} className="border-t border-[#edf2f7] bg-white hover:bg-[#f8fafc]">
                      <td className="px-4 py-3 font-medium text-[#0f172a]">{factura.numero}</td>
                      <td className="px-4 py-3 text-[#475569]">
                        {factura.cliente}
                        <span className="block text-xs text-[#94a3b8]">{factura.operacion}</span>
                      </td>
                      <td className="px-4 py-3">
                        <span
                          title={factura.detalle ?? undefined}
                          className={`inline-flex rounded-full px-2.5 py-1 text-xs font-semibold ${estadoColors[factura.estado]}`}
                        >
                          {factura.estadoTexto}
                        </span>
                        {factura.detalle && factura.estado !== "APROBADA" && (
                          <span className="mt-1 block max-w-[260px] text-xs text-[#94a3b8]">{factura.detalle}</span>
                        )}
                      </td>
                      <td className="px-4 py-3 text-[#475569]">{formatFecha(factura.fecha)}</td>
                      <td className="px-4 py-3 text-right font-medium text-[#0f172a]">
                        {formatPyg(factura.monto)} PYG
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex justify-center gap-2">
                          {factura.descargable && (
                            <>
                              <button
                                onClick={() => handleDownload("kude", factura)}
                                className="rounded-lg bg-[#eaf3ff] px-3 py-1.5 text-xs font-semibold text-[#1a7eff] hover:bg-[#dfeeff]"
                              >
                                PDF
                              </button>
                              <button
                                onClick={() => handleDownload("xml", factura)}
                                className="rounded-lg bg-[#eef2ff] px-3 py-1.5 text-xs font-semibold text-[#4f46e5] hover:bg-[#e0e7ff]"
                              >
                                XML
                              </button>
                              <button
                                onClick={() => reemplazar(actualizarFactura(factura.id))}
                                className="rounded-lg bg-[#f1f5f9] px-3 py-1.5 text-xs font-semibold text-[#475569] hover:bg-[#e2e8f0]"
                              >
                                Consultar estado
                              </button>
                            </>
                          )}
                          {factura.sePuedeEmitir && (
                            <button
                              onClick={() => reemplazar(reintentarFactura(factura.id))}
                              className="rounded-lg bg-[#eaf3ff] px-3 py-1.5 text-xs font-semibold text-[#1a7eff] hover:bg-[#dfeeff]"
                            >
                              {factura.estado === "SIMULADA" ? "Emitir" : "Reintentar"}
                            </button>
                          )}
                          {!factura.descargable && !factura.sePuedeEmitir && (
                            <span className="text-xs text-[#94a3b8]">Sin archivos</span>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className="mt-5 flex items-center justify-between gap-3">
              <p className="text-sm text-[#64748b]">
                Mostrando {paginatedFacturas.length} de {filteredFacturas.length} facturas
              </p>

              <div className="flex items-center gap-2">
                <button
                  onClick={() => setPage((prev) => Math.max(1, prev - 1))}
                  disabled={safePage === 1}
                  className="rounded-lg border border-[#dbe3ee] bg-white px-3 py-1.5 text-sm font-medium text-[#374151] disabled:cursor-not-allowed disabled:opacity-50"
                >
                  Anterior
                </button>

                <div className="flex items-center gap-1">
                  {Array.from({ length: totalPages }, (_, index) => index + 1).map((pageNumber) => (
                    <button
                      key={pageNumber}
                      onClick={() => setPage(pageNumber)}
                      className={`h-8 w-8 rounded-lg text-sm font-semibold ${
                        pageNumber === safePage ? "bg-[#1a7eff] text-white" : "bg-[#f8fafc] text-[#374151]"
                      }`}
                    >
                      {pageNumber}
                    </button>
                  ))}
                </div>

                <button
                  onClick={() => setPage((prev) => Math.min(totalPages, prev + 1))}
                  disabled={safePage === totalPages}
                  className="rounded-lg border border-[#dbe3ee] bg-white px-3 py-1.5 text-sm font-medium text-[#374151] disabled:cursor-not-allowed disabled:opacity-50"
                >
                  Siguiente
                </button>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
