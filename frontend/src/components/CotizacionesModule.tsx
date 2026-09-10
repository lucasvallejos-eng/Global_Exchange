import { useState } from "react";
import { ClientType, getAppliedRate, getClientTypeBadge } from "../lib/clientRates";
import { useTasas } from "../lib/useTasas";

const formatPyg = (value: number) =>
  new Intl.NumberFormat("es-PY", {
    minimumFractionDigits: value < 100 ? 2 : 0,
    maximumFractionDigits: value < 100 ? 2 : 0,
  }).format(value);

export default function CotizacionesModule({ userType, descuentoCompra }: { userType: ClientType; descuentoCompra: number }) {
  const [selectedCode, setSelectedCode] = useState<string>("");
  // Las cotizaciones salen de la base, no de una tabla escrita a mano.
  const { monedas, cargando, error } = useTasas();

  return (
    <div className="space-y-6">
      <div className="rounded-3xl border border-[#dbe3ee] bg-white p-6 shadow-sm">
        <div className="mb-5 flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
          <div>
            <p className="text-sm font-medium text-[#64748b]">Cotizaciones</p>
            <h2 className="text-2xl font-bold tracking-tight text-[#0f172a]">Precios vigentes del día</h2>
          </div>
          <div className="flex items-center gap-3">
            <div className="rounded-full bg-[#edf4ff] px-3 py-1.5 text-xs font-semibold text-[#1a7eff]">
              {getClientTypeBadge(userType, descuentoCompra)}
            </div>
            <div className="rounded-full bg-[#edf4ff] px-3 py-1.5 text-xs font-semibold text-[#1a7eff]">
              Última actualización: Hoy a las 09:30 hs
            </div>
          </div>
        </div>

        <div className="overflow-hidden rounded-2xl border border-[#e2e8f0]">
          <table className="min-w-full border-collapse bg-white text-left text-sm text-[#1f2937]">
            <thead className="bg-[#f8fafc] text-[#475569]">
              <tr>
                <th className="px-4 py-3 font-semibold">Moneda</th>
                <th className="px-4 py-3 text-right font-semibold">Venta</th>
                <th className="px-4 py-3 text-right font-semibold">Compra</th>
              </tr>
            </thead>
            <tbody>
              {cargando && (
                <tr>
                  <td colSpan={3} className="px-4 py-6 text-center text-[#64748b]">
                    Cargando cotizaciones…
                  </td>
                </tr>
              )}

              {!cargando && error && (
                <tr>
                  <td colSpan={3} className="px-4 py-6 text-center text-[#c0392b]">{error}</td>
                </tr>
              )}

              {!cargando && !error && monedas.length === 0 && (
                <tr>
                  <td colSpan={3} className="px-4 py-6 text-center text-[#64748b]">
                    No hay cotizaciones cargadas todavía.
                  </td>
                </tr>
              )}

              {monedas.map((currency) => {
                const tasa = { compra: currency.precioCompra, venta: currency.precioVenta };
                const venta = getAppliedRate(tasa, "venta", descuentoCompra);
                const compra = getAppliedRate(tasa, "compra", descuentoCompra);

                return (
                  <tr
                    key={currency.codigo}
                    onClick={() => setSelectedCode(currency.codigo)}
                    className={`cursor-pointer border-t border-[#edf2f7] transition ${
                      selectedCode === currency.codigo ? "bg-[#f0f7ff]" : "bg-white hover:bg-[#f8fafc]"
                    }`}
                  >
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-3">
                        <span className="text-xl">{currency.simbolo}</span>
                        <div>
                          <div className="font-medium text-[#0f172a]">{currency.nombre}</div>
                          <div className="text-xs text-[#64748b]">{currency.codigo}</div>
                        </div>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-right font-semibold text-[#0066ff]">
                      {formatPyg(venta)} PYG
                    </td>
                    <td className="px-4 py-3 text-right font-semibold text-[#0f172a]">
                      {formatPyg(compra)} PYG
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        <div className="mt-5 flex justify-end">
          <button
            onClick={() => window.alert(`Se abrió la simulación para ${selectedCode}.`)}
            className="rounded-xl bg-[#1a7eff] px-5 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-[#146be7]"
          >
            Ir a Simulación
          </button>
        </div>
      </div>
    </div>
  );
}
