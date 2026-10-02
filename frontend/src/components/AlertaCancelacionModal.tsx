import type { Operacion } from "../lib/operacionesApi";

const formatCurrency = (value: number) =>
  new Intl.NumberFormat("es-PY", { minimumFractionDigits: 0, maximumFractionDigits: 0 }).format(value);

/**
 * Alerta para cuando una operación se cancela sola porque la cotización
 * cambió antes del pago. El cliente no hizo nada mal, así que hay que decirle
 * qué pasó, que no se le cobró, y darle el camino para volver a operar con la
 * cotización nueva ("Volver a operar" crea una operación nueva con los mismos
 * datos, que el backend calcula con la tasa de ahora).
 */
export default function AlertaCancelacionModal({
  operacion,
  procesando,
  onReintentar,
  onCerrar,
}: {
  operacion: Operacion;
  procesando: boolean;
  onReintentar: () => void;
  onCerrar: () => void;
}) {
  const precio = operacion.tipo === "COMPRA" ? "precio de venta" : "precio de compra";
  const sinCotizacion = operacion.tasaBaseNueva === null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 px-4">
      <div role="alertdialog" aria-labelledby="alerta-cancelacion-titulo" className="w-full max-w-xl rounded-2xl bg-white p-6 shadow-2xl">
        <div className="mb-4 inline-flex rounded-full bg-amber-100 px-3 py-1 text-xs font-semibold text-amber-800">
          Operación #{operacion.id} cancelada
        </div>
        <h3 id="alerta-cancelacion-titulo" className="text-2xl font-bold text-[#0f172a]">
          La cotización cambió antes del pago
        </h3>
        <p className="mt-3 text-sm text-[#475569]">No se te cobró nada.</p>

        <div className="mt-5 rounded-2xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
          {sinCotizacion ? (
            <p>{operacion.moneda} se quedó sin cotización vigente: por ahora no se puede operar con esta moneda.</p>
          ) : (
            <p>
              El {precio} de {operacion.moneda} pasó de{" "}
              <strong>{formatCurrency(operacion.tasaBase)}</strong> a{" "}
              <strong>{formatCurrency(operacion.tasaBaseNueva ?? 0)}</strong> PYG.
            </p>
          )}
        </div>

        {!sinCotizacion && (
          <p className="mt-5 text-sm text-[#475569]">
            Podés volver a operar con la cotización actual: vas a ver el cálculo nuevo antes de confirmar.
          </p>
        )}

        <div className="mt-6 flex justify-end gap-3">
          <button
            onClick={onCerrar}
            disabled={procesando}
            className="rounded-xl border border-[#dbe3ee] bg-white px-4 py-2.5 text-sm font-semibold text-[#374151] hover:bg-[#f8fafc]"
          >
            Cerrar
          </button>
          {!sinCotizacion && (
            <button
              onClick={onReintentar}
              disabled={procesando}
              className="rounded-xl bg-[#1a7eff] px-4 py-2.5 text-sm font-semibold text-white hover:bg-[#146be7] disabled:bg-slate-300"
            >
              {procesando ? "Calculando..." : "Volver a operar con la cotización actual"}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
