import { useEffect, useState } from "react";
import { ClientType, getAppliedRate } from "../lib/clientRates";
import { useTasas } from "../lib/useTasas";
import { etiquetaMedioPago, listarMediosPago, type MedioPago } from "../lib/mediosPagoApi";


type PaymentMethod = "tarjeta" | "transferencia" | "billetera";

const formatCurrency = (value: number) =>
  new Intl.NumberFormat("es-PY", {
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(value);

export default function CompraDivisasModule({ userType, descuentoCompra }: { userType: ClientType; descuentoCompra: number }) {
  const [amount, setAmount] = useState("500");
  const [currency, setCurrency] = useState<string>("");
  const [paymentMethod, setPaymentMethod] = useState<string>("nuevo");
  const [newPaymentType, setNewPaymentType] = useState<PaymentMethod>("tarjeta");
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const [savedMethods, setSavedMethods] = useState<MedioPago[]>([]);

  useEffect(() => {
    void listarMediosPago().then(({ medios }) => setSavedMethods(medios.filter((medio) => medio.activo)))
      .catch(() => setSavedMethods([]));
  }, []);

  useEffect(() => {
    if (savedMethods.length > 0 && paymentMethod === "nuevo") setPaymentMethod(String(savedMethods[0].id));
  }, [paymentMethod, savedMethods]);

  const [cardNumber, setCardNumber] = useState("");
  const [cardHolder, setCardHolder] = useState("");
  const [expiry, setExpiry] = useState("");
  const [cvv, setCvv] = useState("");
  const [transferReceipt, setTransferReceipt] = useState<File | null>(null);
  const [walletReceipt, setWalletReceipt] = useState<File | null>(null);

  // Cotizaciones reales de la base, en vez de una tabla fija.
  const { tasas, codigos, cargando } = useTasas();

  useEffect(() => {
    if (!currency && codigos.length > 0) setCurrency(codigos[0]);
  }, [codigos, currency]);

  const tasa = tasas[currency] ?? { compra: 0, venta: 0 };

  const numericAmount = Number.parseFloat(amount) || 0;
  const baseRate = tasa.venta;
  const conversionRate = getAppliedRate(tasa, "venta", descuentoCompra);
  const totalInPyg = numericAmount * conversionRate;

  const methodLabels: Record<PaymentMethod, string> = {
    tarjeta: "Tarjeta de Crédito / Débito",
    transferencia: "Transferencia Bancaria",
    billetera: "Billetera Digital",
  };
  const isNewPaymentMethod = paymentMethod === "nuevo";
  const selectedMethod = savedMethods.find((medio) => String(medio.id) === paymentMethod);

  const handleConfirm = () => {
    setSuccessMessage("Transacción confirmada correctamente.");
    setIsModalOpen(false);
  };

  const renderPaymentFields = () => {
    if (newPaymentType === "tarjeta") {
      return (
        <div className="grid gap-4 md:grid-cols-2">
          <label className="block md:col-span-2">
            <span className="mb-2 block text-sm font-medium text-[#374151]">Número de tarjeta</span>
            <input
              value={cardNumber}
              onChange={(event) => setCardNumber(event.target.value)}
              placeholder="1234 5678 9012 3456"
              className="w-full rounded-xl border border-[#dbe3ee] bg-[#f8fafc] px-3 py-2.5 text-sm text-[#1f2937] outline-none focus:border-[#1a7eff]"
            />
          </label>
          <label className="block md:col-span-2">
            <span className="mb-2 block text-sm font-medium text-[#374151]">Nombre del titular</span>
            <input
              value={cardHolder}
              onChange={(event) => setCardHolder(event.target.value)}
              placeholder="Juan Pérez"
              className="w-full rounded-xl border border-[#dbe3ee] bg-[#f8fafc] px-3 py-2.5 text-sm text-[#1f2937] outline-none focus:border-[#1a7eff]"
            />
          </label>
          <label className="block">
            <span className="mb-2 block text-sm font-medium text-[#374151]">Fecha de vencimiento</span>
            <input
              value={expiry}
              onChange={(event) => setExpiry(event.target.value)}
              placeholder="MM/AA"
              className="w-full rounded-xl border border-[#dbe3ee] bg-[#f8fafc] px-3 py-2.5 text-sm text-[#1f2937] outline-none focus:border-[#1a7eff]"
            />
          </label>
          <label className="block">
            <span className="mb-2 block text-sm font-medium text-[#374151]">Código de seguridad (CVV)</span>
            <input
              value={cvv}
              onChange={(event) => setCvv(event.target.value)}
              placeholder="123"
              className="w-full rounded-xl border border-[#dbe3ee] bg-[#f8fafc] px-3 py-2.5 text-sm text-[#1f2937] outline-none focus:border-[#1a7eff]"
            />
          </label>
        </div>
      );
    }

    if (newPaymentType === "transferencia") {
      return (
        <div className="space-y-4">
          <div className="rounded-2xl border border-[#dbe3ee] bg-[#f8fafc] p-4 text-sm text-[#374151]">
            <p className="font-semibold text-[#1a7eff]">Global Exchange</p>
            <div className="mt-3 grid gap-2 sm:grid-cols-2">
              <div><span className="block text-[#64748b]">Banco</span><span className="font-medium">Banco Itaú</span></div>
              <div><span className="block text-[#64748b]">Número de cuenta</span><span className="font-medium">PYG - 001-2024-5489</span></div>
              <div><span className="block text-[#64748b]">RUC/CI</span><span className="font-medium">800.123.456-1</span></div>
              <div><span className="block text-[#64748b]">Titular</span><span className="font-medium">Global Exchange S.A.</span></div>
            </div>
          </div>

          <label className="block">
            <span className="mb-2 block text-sm font-medium text-[#374151]">Comprobante de pago</span>
            <div className="flex items-center gap-3 rounded-xl border border-dashed border-[#cbd5e1] bg-[#f8fafc] px-3 py-3">
              <input
                type="file"
                accept=".pdf,.jpg,.jpeg,.png"
                onChange={(event) => setTransferReceipt(event.target.files?.[0] ?? null)}
                className="hidden"
                id="transfer-proof"
              />
              <label htmlFor="transfer-proof" className="cursor-pointer rounded-lg bg-[#eaf3ff] px-3 py-2 text-xs font-semibold text-[#1a7eff]">
                Subir archivo
              </label>
              <span className="text-xs text-[#64748b]">{transferReceipt ? transferReceipt.name : "PDF, JPG o PNG"}</span>
            </div>
          </label>
        </div>
      );
    }

    return (
      <div className="space-y-4">
        <div className="rounded-2xl border border-[#dbe3ee] bg-[#f8fafc] p-4 text-sm text-[#374151]">
          <p className="font-semibold text-[#1a7eff]">Datos de la billetera</p>
          <div className="mt-3 grid gap-2 sm:grid-cols-2">
            <div><span className="block text-[#64748b]">Número de teléfono</span><span className="font-medium">+595 981 123 456</span></div>
            <div><span className="block text-[#64748b]">Cuenta</span><span className="font-medium">GE-4587-991</span></div>
          </div>
        </div>

        <label className="block">
          <span className="mb-2 block text-sm font-medium text-[#374151]">Comprobante de pago</span>
          <div className="flex items-center gap-3 rounded-xl border border-dashed border-[#cbd5e1] bg-[#f8fafc] px-3 py-3">
            <input
              type="file"
              accept=".pdf,.jpg,.jpeg,.png"
              onChange={(event) => setWalletReceipt(event.target.files?.[0] ?? null)}
              className="hidden"
              id="wallet-proof"
            />
            <label htmlFor="wallet-proof" className="cursor-pointer rounded-lg bg-[#eaf3ff] px-3 py-2 text-xs font-semibold text-[#1a7eff]">
              Subir archivo
            </label>
            <span className="text-xs text-[#64748b]">{walletReceipt ? walletReceipt.name : "PDF, JPG o PNG"}</span>
          </div>
        </label>
      </div>
    );
  };

  return (
    <div className="space-y-6">
      <div className="rounded-3xl border border-[#dbe3ee] bg-white p-6 shadow-sm">
        <div className="mb-6 flex items-center justify-between gap-4">
          <div>
            <p className="text-sm font-medium text-[#64748b]">Compra de divisas</p>
            <h2 className="text-2xl font-bold tracking-tight text-[#0f172a]">Cambio a Guaraníes</h2>
          </div>
        </div>

        <div className="grid gap-5 md:grid-cols-[1.5fr_0.8fr]">
          <label className="block">
            <span className="mb-2 block text-sm font-medium text-[#374151]">Monto a cambiar</span>
            <div className="flex overflow-hidden rounded-xl border border-[#dbe3ee] bg-[#f8fafc] focus-within:border-[#1a7eff]">
              <input
                type="number"
                min="0"
                step="0.01"
                value={amount}
                onChange={(event) => setAmount(event.target.value)}
                className="w-full bg-transparent px-4 py-3 text-lg font-semibold text-[#0f172a] outline-none"
                placeholder="500"
              />
              <select
                value={currency}
                onChange={(event) => setCurrency(event.target.value)}
                className="border-l border-[#dbe3ee] bg-white px-3 py-3 text-sm font-medium text-[#374151] outline-none"
              >
                {cargando && <option>Cargando...</option>}
                {!cargando && codigos.length === 0 && <option>Sin monedas</option>}
                {codigos.map((c) => (
                  <option key={c} value={c}>
                    {c}
                  </option>
                ))}
              </select>
            </div>
          </label>

          <div className="rounded-2xl border border-[#dbe3ee] bg-[#f8fafc] p-4">
            <p className="text-xs uppercase tracking-[0.18em] text-[#64748b]">Tasa aplicada</p>
            <p className="mt-2 text-lg font-bold text-[#0f172a]">1 {currency} = {formatCurrency(conversionRate)} PYG</p>
            <p className="mt-1 text-xs text-[#64748b]">Base: {formatCurrency(baseRate)} PYG • {userType}</p>
          </div>
        </div>

        <div className="mt-5 rounded-2xl border border-[#dbe3ee] bg-[#f0f7ff] p-4">
          <p className="text-sm text-[#64748b]">Monto equivalente en PYG</p>
          <p className="mt-1 text-2xl font-bold text-[#1a7eff]">{formatCurrency(totalInPyg)} PYG</p>
        </div>

        <div className="mt-6">
          <label className="block">
            <span className="mb-2 block text-sm font-medium text-[#374151]">Método de pago</span>
            <select
                value={paymentMethod}
                onChange={(event) => setPaymentMethod(event.target.value as PaymentMethod)}
                className="w-full rounded-xl border border-[#dbe3ee] bg-[#f8fafc] px-3 py-2.5 text-sm text-[#1f2937] outline-none focus:border-[#1a7eff]"
              >
                {savedMethods.map((medio) => (
                  <option key={medio.id} value={medio.id}>{etiquetaMedioPago(medio)}</option>
                ))}
                <option value="nuevo">Agregar nuevo método de pago...</option>
              </select>
          </label>
        </div>

        {isNewPaymentMethod && <div className="mt-6">
          <label className="mb-4 block">
            <span className="mb-2 block text-sm font-medium text-[#374151]">Tipo del nuevo método</span>
            <select value={newPaymentType} onChange={(event) => setNewPaymentType(event.target.value as PaymentMethod)} className="w-full rounded-xl border border-[#dbe3ee] bg-[#f8fafc] px-3 py-2.5 text-sm">
              <option value="tarjeta">Tarjeta de crédito</option>
              <option value="transferencia">Transferencia bancaria</option>
              <option value="billetera">Billetera digital</option>
            </select>
          </label>
          {renderPaymentFields()}
        </div>}

        {successMessage && (
          <div className="mt-6 rounded-xl border border-green-200 bg-green-50 px-4 py-3 text-sm font-medium text-green-700">
            {successMessage}
          </div>
        )}

        <div className="mt-8 flex justify-end">
          <button
            onClick={() => setIsModalOpen(true)}
            disabled={savedMethods.length === 0 && !isNewPaymentMethod}
            className="rounded-xl bg-[#1a7eff] px-6 py-3 text-sm font-semibold text-white shadow-sm transition hover:bg-[#146be7] disabled:cursor-not-allowed disabled:bg-slate-300"
          >
            Comprar
          </button>
        </div>
      </div>

      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 px-4">
          <div className="w-full max-w-xl rounded-2xl bg-white p-6 shadow-2xl">
            <h3 className="text-2xl font-bold text-[#0f172a]">¿Desea realizar la transacción de compra?</h3>

            <div className="mt-5 space-y-3 rounded-2xl border border-[#e2e8f0] bg-[#f8fafc] p-4 text-sm text-[#374151]">
              <div className="flex items-center justify-between gap-4">
                <span className="text-[#64748b]">Monto a comprar / cambiar</span>
                <span className="font-semibold text-[#0f172a]">{formatCurrency(numericAmount)} {currency}</span>
              </div>
              <div className="flex items-center justify-between gap-4">
                <span className="text-[#64748b]">Tasa de cambio aplicada</span>
                <span className="font-semibold text-[#0f172a]">1 {currency} = {formatCurrency(conversionRate)} PYG</span>
              </div>
              <div className="flex items-center justify-between gap-4">
                <span className="text-[#64748b]">Perfil del cliente</span>
                <span className="font-semibold text-[#0f172a]">{userType}</span>
              </div>
              <div className="flex items-center justify-between gap-4">
                <span className="text-[#64748b]">Total a pagar en PYG</span>
                <span className="font-semibold text-[#0f172a]">{formatCurrency(totalInPyg)} PYG</span>
              </div>
              <div className="flex items-center justify-between gap-4">
                <span className="text-[#64748b]">Método de pago</span>
                <span className="font-semibold text-[#0f172a]">{selectedMethod ? etiquetaMedioPago(selectedMethod) : "Nuevo método de pago"}</span>
              </div>
            </div>

            <p className="mt-5 text-sm text-[#475569]">Si los datos son correctos, presione Confirmar.</p>

            <div className="mt-6 flex justify-end gap-3">
              <button
                onClick={() => setIsModalOpen(false)}
                className="rounded-xl border border-[#dbe3ee] bg-white px-4 py-2.5 text-sm font-semibold text-[#374151] hover:bg-[#f8fafc]"
              >
                Cancelar
              </button>
              <button
                onClick={handleConfirm}
                className="rounded-xl bg-[#1a7eff] px-4 py-2.5 text-sm font-semibold text-white hover:bg-[#146be7]"
              >
                Confirmar
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
