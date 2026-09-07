import { useMemo, useState } from "react";

type FacturaEstado = "Pagado" | "Pendiente" | "Cancelada";

type Factura = {
  id: number;
  numero: string;
  estado: FacturaEstado;
  fecha: string;
  monto: number;
};

const FACTURAS_SEED: Factura[] = [
  { id: 1, numero: "001-001-0000123", estado: "Pagado", fecha: "12/03/2026", monto: 574280 },
  { id: 2, numero: "001-001-0000124", estado: "Pendiente", fecha: "18/03/2026", monto: 238900 },
  { id: 3, numero: "001-001-0000125", estado: "Pagado", fecha: "21/03/2026", monto: 890450 },
  { id: 4, numero: "001-001-0000126", estado: "Cancelada", fecha: "28/03/2026", monto: 321150 },
  { id: 5, numero: "001-001-0000127", estado: "Pagado", fecha: "02/04/2026", monto: 610000 },
  { id: 6, numero: "001-001-0000128", estado: "Pendiente", fecha: "06/04/2026", monto: 475500 },
  { id: 7, numero: "001-001-0000129", estado: "Pagado", fecha: "11/04/2026", monto: 990100 },
  { id: 8, numero: "001-001-0000130", estado: "Cancelada", fecha: "15/04/2026", monto: 280400 },
  { id: 9, numero: "001-001-0000131", estado: "Pagado", fecha: "18/04/2026", monto: 700320 },
  { id: 10, numero: "001-001-0000132", estado: "Pendiente", fecha: "22/04/2026", monto: 420800 },
  { id: 11, numero: "001-001-0000133", estado: "Pagado", fecha: "25/04/2026", monto: 1250000 },
  { id: 12, numero: "001-001-0000134", estado: "Pagado", fecha: "28/04/2026", monto: 655300 },
];

const formatPyg = (value: number) =>
  new Intl.NumberFormat("es-PY", {
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(value);

const estadoColors: Record<FacturaEstado, string> = {
  Pagado: "bg-green-100 text-green-700",
  Pendiente: "bg-yellow-100 text-yellow-700",
  Cancelada: "bg-red-100 text-red-700",
};

export default function FacturaModule() {
  const [facturas] = useState<Factura[]>(FACTURAS_SEED);
  const [search, setSearch] = useState("");
  const [estadoFilter, setEstadoFilter] = useState<"Todos" | FacturaEstado>("Todos");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [page, setPage] = useState(1);
  const pageSize = 10;

  const filteredFacturas = useMemo(() => {
    return facturas.filter((factura) => {
      const matchesSearch = factura.numero.toLowerCase().includes(search.toLowerCase());
      const matchesEstado = estadoFilter === "Todos" || factura.estado === estadoFilter;

      const facturaDate = factura.fecha;
      const fromOk = !dateFrom || facturaDate >= dateFrom;
      const toOk = !dateTo || facturaDate <= dateTo;

      return matchesSearch && matchesEstado && fromOk && toOk;
    });
  }, [dateFrom, dateTo, estadoFilter, facturas, search]);

  const totalPages = Math.max(1, Math.ceil(filteredFacturas.length / pageSize));
  const safePage = Math.min(page, totalPages);

  const paginatedFacturas = filteredFacturas.slice((safePage - 1) * pageSize, safePage * pageSize);

  const handleDownload = (formato: "PDF" | "XML", factura: Factura) => {
    const nombre = `${factura.numero}-${formato.toLowerCase()}`;
    const contenido = `Factura ${factura.numero}\nEstado: ${factura.estado}\nMonto: ${formatPyg(factura.monto)} PYG\nFormato: ${formato}`;
    const blob = new Blob([contenido], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${nombre}.txt`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="space-y-6">
      <div className="rounded-3xl border border-[#dbe3ee] bg-white p-6 shadow-sm">
        <div className="mb-5">
          <p className="text-sm font-medium text-[#64748b]">Facturación</p>
          <h2 className="text-2xl font-bold tracking-tight text-[#0f172a]">Facturas</h2>
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
              placeholder="001-001-0000123"
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
                setEstadoFilter(event.target.value as "Todos" | FacturaEstado);
                setPage(1);
              }}
              className="w-full rounded-xl border border-[#dbe3ee] bg-[#f8fafc] px-3 py-2.5 text-sm text-[#1f2937] outline-none focus:border-[#1a7eff]"
            >
              <option value="Todos">Todos</option>
              <option value="Pagado">Pagado</option>
              <option value="Pendiente">Pendiente</option>
              <option value="Cancelada">Cancelada</option>
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
              <p className="text-lg font-semibold text-[#0f172a]">Aún no registras facturas emitidas.</p>
            </div>
          </div>
        ) : (
          <>
            <div className="overflow-hidden rounded-2xl border border-[#e2e8f0]">
              <table className="min-w-full border-collapse bg-white text-left text-sm text-[#1f2937]">
                <thead className="bg-[#f8fafc] text-[#475569]">
                  <tr>
                    <th className="px-4 py-3 font-semibold">Número de Factura</th>
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
                      <td className="px-4 py-3">
                        <span className={`inline-flex rounded-full px-2.5 py-1 text-xs font-semibold ${estadoColors[factura.estado]}`}>
                          {factura.estado}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-[#475569]">{factura.fecha}</td>
                      <td className="px-4 py-3 text-right font-medium text-[#0f172a]">
                        {formatPyg(factura.monto)} PYG
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex justify-center gap-2">
                          <button
                            onClick={() => handleDownload("PDF", factura)}
                            className="rounded-lg bg-[#eaf3ff] px-3 py-1.5 text-xs font-semibold text-[#1a7eff] hover:bg-[#dfeeff]"
                          >
                            PDF
                          </button>
                          <button
                            onClick={() => handleDownload("XML", factura)}
                            className="rounded-lg bg-[#eef2ff] px-3 py-1.5 text-xs font-semibold text-[#4f46e5] hover:bg-[#e0e7ff]"
                          >
                            XML
                          </button>
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
