import { useState } from "react";
import { BASE_RATES, ClientType, getAppliedRate, getClientTypeBadge } from "../lib/clientRates";

type MonedaCotizacion = {
  code: keyof typeof BASE_RATES | "PYG";
  name: string;
  icon: string;
};

const COTIZACIONES: MonedaCotizacion[] = [
  { code: "USD", name: "Dólar", icon: "💵" },
  { code: "EUR", name: "Euro", icon: "💶" },
  { code: "BRL", name: "Real Brasileño", icon: "💸" },
  { code: "PYG", name: "Guaraní", icon: "₲" },
];

const formatPyg = (value: number) =>
  new Intl.NumberFormat("es-PY", {
    minimumFractionDigits: value < 100 ? 2 : 0,
    maximumFractionDigits: value < 100 ? 2 : 0,
  }).format(value);

export default function CotizacionesModule({ userType }: { userType: ClientType }) {
  const [selectedCode, setSelectedCode] = useState<string>("USD");

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
              {getClientTypeBadge(userType)}
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
              {COTIZACIONES.map((currency) => {
                const code = currency.code as keyof typeof BASE_RATES | "PYG";
                const venta = code === "PYG" ? 1 : getAppliedRate(code, "venta", userType);
                const compra = code === "PYG" ? 1 : getAppliedRate(code, "compra", userType);

                return (
                  <tr
                    key={currency.code}
                    onClick={() => setSelectedCode(currency.code)}
                    className={`cursor-pointer border-t border-[#edf2f7] transition ${
                      selectedCode === currency.code ? "bg-[#f0f7ff]" : "bg-white hover:bg-[#f8fafc]"
                    }`}
                  >
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-3">
                        <span className="text-xl">{currency.icon}</span>
                        <div>
                          <div className="font-medium text-[#0f172a]">{currency.name}</div>
                          <div className="text-xs text-[#64748b]">{currency.code}</div>
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
