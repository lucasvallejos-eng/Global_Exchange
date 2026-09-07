import { useMemo, useState } from "react";

type TransactionType = "Compra" | "Venta";
type TransactionStatus = "Finalizada" | "Pendiente" | "Rechazada" | "Cancelada por Usuario";

type Transaction = {
  id: string;
  tipo: TransactionType;
  estado: TransactionStatus;
  fecha: string;
  monto: number;
  moneda: string;
  detalle: string;
};

const INITIAL_TRANSACTIONS: Transaction[] = [
  {
    id: "TX-1001",
    tipo: "Compra",
    estado: "Finalizada",
    fecha: "2026-09-01T14:30:00",
    monto: 574280,
    moneda: "BRL",
    detalle: "Cambio a PYG",
  },
  {
    id: "TX-1002",
    tipo: "Venta",
    estado: "Pendiente",
    fecha: "2026-09-01T08:00:00",
    monto: 135000,
    moneda: "USD",
    detalle: "Cobro en PYG",
  },
  {
    id: "TX-1003",
    tipo: "Compra",
    estado: "Rechazada",
    fecha: "2026-08-29T09:15:00",
    monto: 320000,
    moneda: "EUR",
    detalle: "Cambio a PYG",
  },
  {
    id: "TX-1004",
    tipo: "Venta",
    estado: "Finalizada",
    fecha: "2026-08-15T06:40:00",
    monto: 250000,
    moneda: "USD",
    detalle: "Acreditación",
  },
  {
    id: "TX-1005",
    tipo: "Compra",
    estado: "Pendiente",
    fecha: "2026-08-31T18:45:00",
    monto: 760000,
    moneda: "USD",
    detalle: "Cambio a PYG",
  },
];

const formatDateTime = (dateStr: string) =>
  new Date(dateStr).toLocaleString("es-PY", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });

const formatCurrency = (value: number) =>
  new Intl.NumberFormat("es-PY", {
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(value);

const esCancelable = (fechaTransaccion: string, estadoActual: TransactionStatus) => {
  if (estadoActual === "Rechazada" || estadoActual === "Cancelada por Usuario") return false;

  const fechaTx = new Date(fechaTransaccion);
  const ahora = new Date();
  const diferenciaHoras = (ahora.getTime() - fechaTx.getTime()) / (1000 * 60 * 60);

  return diferenciaHoras < 24;
};

export default function HistorialTransaccionesModule() {
  const [transactions, setTransactions] = useState<Transaction[]>(INITIAL_TRANSACTIONS);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [toast, setToast] = useState<string | null>(null);

  const rows = useMemo(() => transactions, [transactions]);

  const handleCancel = (id: string) => {
    setTransactions((current) =>
      current.map((tx) =>
        tx.id === id ? { ...tx, estado: "Cancelada por Usuario" } : tx,
      ),
    );

    setToast(`Transacción ${id} cancelada exitosamente.`);
    setSelectedId(null);
    setTimeout(() => setToast(null), 2400);
  };

  return (
    <div className="space-y-6">
      <div className="rounded-3xl border border-[#dbe3ee] bg-white p-6 shadow-sm">
        <div className="mb-5">
          <p className="text-sm font-medium text-[#64748b]">Historial</p>
          <h2 className="text-2xl font-bold tracking-tight text-[#0f172a]">Transacciones</h2>
        </div>

        <div className="overflow-hidden rounded-2xl border border-[#e2e8f0]">
          <table className="min-w-full border-collapse bg-white text-left text-sm text-[#1f2937]">
            <thead className="bg-[#f8fafc] text-[#475569]">
              <tr>
                <th className="px-4 py-3 font-semibold">Transacción</th>
                <th className="px-4 py-3 font-semibold">Estado</th>
                <th className="px-4 py-3 font-semibold">Fecha y Hora</th>
                <th className="px-4 py-3 font-semibold text-right">Monto</th>
                <th className="px-4 py-3 font-semibold text-center">Acciones</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((transaction) => {
                const canCancel = esCancelable(transaction.fecha, transaction.estado);
                const isPending = transaction.estado === "Pendiente";

                return (
                  <tr key={transaction.id} className="border-t border-[#edf2f7] bg-white hover:bg-[#f8fafc]">
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-3">
                        <span
                          className={`inline-flex rounded-full px-2.5 py-1 text-xs font-semibold ${
                            transaction.tipo === "Compra"
                              ? "bg-[#eaf3ff] text-[#1a7eff]"
                              : "bg-[#eefcf3] text-[#16a34a]"
                          }`}
                        >
                          {transaction.tipo}
                        </span>
                        <span className="font-medium text-[#0f172a]">{transaction.id}</span>
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className={`inline-flex items-center rounded-full px-2.5 py-1 text-xs font-semibold ${
                          transaction.estado === "Finalizada"
                            ? "bg-green-100 text-green-700"
                            : transaction.estado === "Pendiente"
                              ? "bg-yellow-100 text-yellow-700"
                              : transaction.estado === "Rechazada"
                                ? "bg-gray-200 text-gray-700"
                                : "bg-red-100 text-red-700"
                        }`}
                      >
                        {transaction.estado}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-[#374151]">{formatDateTime(transaction.fecha)}</td>
                    <td className="px-4 py-3 text-right font-semibold text-[#0f172a]">
                      {formatCurrency(transaction.monto)} {transaction.moneda}
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex justify-center">
                        {canCancel ? (
                          <button
                            onClick={() => setSelectedId(transaction.id)}
                            className="rounded-lg bg-red-50 px-3 py-1.5 text-xs font-semibold text-red-600 hover:bg-red-100"
                          >
                            Cancelar Transacción
                          </button>
                        ) : (
                          <span className="text-xs font-medium text-[#9ca3af]">
                            {isPending ? "Plazo vencido" : "No disponible"}
                          </span>
                        )}
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {selectedId && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 p-4">
          <div className="w-full max-w-md rounded-2xl bg-white p-6 shadow-2xl">
            <h3 className="text-xl font-bold text-[#0f172a]">¿Desea cancelar esta transacción?</h3>
            <p className="mt-3 text-sm text-[#64748b]">
              Esta operación fue realizada hace menos de 24 horas. Al confirmar, la transacción pasará a estado Cancelada.
            </p>

            <div className="mt-6 flex justify-end gap-3">
              <button
                onClick={() => setSelectedId(null)}
                className="rounded-xl border border-[#dbe3ee] bg-white px-4 py-2 text-sm font-semibold text-[#475569] hover:bg-[#f8fafc]"
              >
                Volver
              </button>
              <button
                onClick={() => handleCancel(selectedId)}
                className="rounded-xl bg-red-600 px-4 py-2 text-sm font-semibold text-white hover:bg-red-700"
              >
                Confirmar Cancelación
              </button>
            </div>
          </div>
        </div>
      )}

      {toast && (
        <div className="fixed bottom-6 right-6 z-[60] rounded-xl bg-[#0f172a] px-4 py-3 text-sm font-medium text-white shadow-lg">
          {toast}
        </div>
      )}
    </div>
  );
}
