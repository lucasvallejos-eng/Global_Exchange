import { useEffect, useMemo, useState } from "react";

import {
  actualizarFactura,
  consultarTalonario,
  listarFacturas,
  reintentarFactura,
  urlDescarga,
  type EstadoFactura,
  type Factura,
  type TalonarioInfo,
} from "../lib/facturasApi";
import type { User } from "../types";

interface Props {
  user: User;
}

const formatPyg = (value: number) =>
  new Intl.NumberFormat("es-PY", {
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(value);

const formatFecha = (iso: string) => new Date(iso).toLocaleDateString("es-PY");

const estadoColors: Record<EstadoFactura, string> = {
  SIMULADA: "bg-amber-100 text-amber-700",
  ENVIADA: "bg-yellow-100 text-yellow-700",
  SIN_CONFIRMAR: "bg-yellow-100 text-yellow-700",
  APROBADA: "bg-green-100 text-green-700",
  ERROR: "bg-red-100 text-red-700",
  RECHAZADA: "bg-red-100 text-red-700",
  CANCELADA: "bg-red-100 text-red-700",
};

const estadoCliente: Record<EstadoFactura, string> = {
  SIMULADA: "En Espera",
  ENVIADA: "Emitida",
  SIN_CONFIRMAR: "En Espera",
  APROBADA: "Emitida",
  ERROR: "Pendiente de emisión",
  RECHAZADA: "Pendiente de emisión",
  CANCELADA: "Cancelada",
};

const estadoClienteColors: Record<EstadoFactura, string> = {
  SIMULADA: "bg-amber-100 text-amber-700",
  ENVIADA: "bg-amber-100 text-amber-700",
  SIN_CONFIRMAR: "bg-amber-100 text-amber-700",
  APROBADA: "bg-green-100 text-green-700",
  ERROR: "bg-amber-100 text-amber-700",
  RECHAZADA: "bg-amber-100 text-amber-700",
  CANCELADA: "bg-slate-100 text-slate-600",
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

export default function FacturaModule({ user }: Props) {
  const esAdministrador = user.role === "administrador";
  const [facturas, setFacturas] = useState<Factura[]>([]);
  const [talonario, setTalonario] = useState<TalonarioInfo | null>(null);
  const [emision, setEmision] = useState<"real" | "simulada">("simulada");
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState("");
  const [search, setSearch] = useState("");
  const [estadoFilter, setEstadoFilter] = useState<"Todos" | EstadoFactura>("Todos");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [page, setPage] = useState(1);
  const pageSize = 10;

  const cargarTalonario = () => {
    consultarTalonario()
      .then((info) => setTalonario(info))
      .catch(() => {});
  };

  useEffect(() => {
    listarFacturas()
      .then((datos) => {
        setFacturas(datos.facturas);
        setEmision(datos.emision);
        if (datos.talonario) {
          setTalonario(datos.talonario);
        } else if (datos.facturasDisponibles !== undefined && datos.siguienteFactura) {
          setTalonario({
            disponibles: datos.facturasDisponibles,
            siguiente: datos.siguienteFactura,
            agotado: datos.facturasDisponibles === 0,
          });
        } else if (esAdministrador) {
          cargarTalonario();
        }
      })
      .catch((e: Error) => setError(e.message))
      .finally(() => setCargando(false));
  }, [esAdministrador]);

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
      .then((nueva) => {
        setFacturas((lista) => lista.map((f) => (f.id === nueva.id ? nueva : f)));
        if (esAdministrador) {
          cargarTalonario();
        }
      })
      .catch((e: Error) => setError(e.message));
  };

  return (
    <div className="space-y-6">
      <div className="rounded-3xl border border-[#dbe3ee] bg-white p-6 shadow-sm">
        <div className="mb-6 flex flex-col justify-between gap-4 sm:flex-row sm:items-start">
          <div>
            <p className="text-sm font-medium text-[#64748b]">Facturación</p>
            <h2 className="text-2xl font-bold tracking-tight text-[#0f172a]">Facturas</h2>
            <p className="mt-1 text-sm text-[#64748b]">
              {emision === "simulada"
                ? "La emisión está apagada: las facturas quedan simuladas y no gastan números."
                : "La emisión está prendida: cada factura se emite cuando el administrador toca Emitir."}
            </p>
            {error && <p className="mt-2 text-sm font-medium text-red-600">{error}</p>}
          </div>

          {/* Indicador de Talonario y Secuencia en tiempo real en la esquina superior derecha */}
          {esAdministrador && talonario && (
            <div
              className={`flex items-center gap-3.5 rounded-2xl border px-4 py-3 shadow-xs transition-colors sm:min-w-[310px] ${
                talonario.agotado || talonario.disponibles === 0
                  ? "border-red-200 bg-red-50/90 text-red-950"
                  : talonario.disponibles <= 3
                  ? "border-amber-200 bg-amber-50/90 text-amber-950"
                  : "border-[#dbe3ee] bg-[#f8fafc] text-[#0f172a]"
              }`}
            >
              <div
                className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-xl ${
                  talonario.agotado || talonario.disponibles === 0
                    ? "bg-red-100 text-red-600"
                    : talonario.disponibles <= 3
                    ? "bg-amber-100 text-amber-600"
                    : "bg-blue-50 text-[#1a7eff]"
                }`}
              >
                <svg
                  className="h-5 w-5"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                  strokeWidth="2"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                  />
                </svg>
              </div>

              <div className="flex-1">
                <div className="flex items-center justify-between gap-2">
                  <span className="text-[11px] font-semibold uppercase tracking-wider text-[#64748b]">
                    Talonario SIFEN
                  </span>
                  <span
                    className={`inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-bold ${
                      talonario.agotado || talonario.disponibles === 0
                        ? "bg-red-200 text-red-800"
                        : talonario.disponibles <= 3
                        ? "bg-amber-200 text-amber-800"
                        : "bg-emerald-100 text-emerald-800"
                    }`}
                  >
                    {talonario.agotado || talonario.disponibles === 0
                      ? "Agotado"
                      : talonario.disponibles <= 3
                      ? "Stock Bajo"
                      : "Disponible"}
                  </span>
                </div>

                <div className="mt-1 flex items-baseline justify-between gap-3">
                  <div>
                    <span className="block text-[11px] text-[#64748b]">Próxima factura</span>
                    <span className="font-mono text-sm font-bold tracking-tight text-[#0f172a]">
                      {talonario.siguiente}
                    </span>
                  </div>

                  <div className="text-right">
                    <span className="block text-[11px] text-[#64748b]">Disponibles</span>
                    <span
                      className={`text-sm font-extrabold ${
                        talonario.agotado || talonario.disponibles === 0
                          ? "text-red-600"
                          : talonario.disponibles <= 3
                          ? "text-amber-600"
                          : "text-[#1a7eff]"
                      }`}
                    >
                      {talonario.disponibles}{" "}
                      <span className="text-[11px] font-normal text-[#64748b]">
                        {talonario.disponibles === 1 ? "folio" : "folios"}
                      </span>
                    </span>
                  </div>
                </div>
              </div>
            </div>
          )}
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
                    <th className="px-4 py-3 text-center font-semibold">
                      {esAdministrador ? "Gestión / Descarga" : "Acciones"}
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {paginatedFacturas.map((factura) => (
                    <tr key={factura.id} className="border-t border-[#edf2f7] bg-white hover:bg-[#f8fafc]">
                      <td className="px-4 py-3 font-medium text-[#0f172a]">{factura.numero}</td>
                      <td className="px-4 py-3 text-[#475569]">
                        {factura.cliente}
                        <span className="block text-xs text-[#94a3b8]">
                          {factura.operacion} · {factura.referencia}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <span
                          title={factura.detalle ?? undefined}
                          className={`inline-flex rounded-full px-2.5 py-1 text-xs font-semibold ${
                            esAdministrador ? estadoColors[factura.estado] : estadoClienteColors[factura.estado]
                          }`}
                        >
                          {esAdministrador ? factura.estadoTexto : estadoCliente[factura.estado]}
                        </span>
                        {esAdministrador && factura.detalle && factura.estado !== "APROBADA" && (
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
                          {esAdministrador && factura.sePuedeEmitir && (
                            <button
                              onClick={() => reemplazar(reintentarFactura(factura.id))}
                              className="rounded-lg bg-[#eaf3ff] px-3 py-1.5 text-xs font-semibold text-[#1a7eff] hover:bg-[#dfeeff]"
                            >
                              {factura.estado === "SIMULADA" ? "Emitir Directamente" : "Reintentar Emisión"}
                            </button>
                          )}
                          {!factura.descargable && !factura.sePuedeEmitir && (
                            <span className="text-xs italic text-[#94a3b8]">
                              {esAdministrador ? "Sin acciones disponibles" : "Factura en proceso de emisión"}
                            </span>
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
