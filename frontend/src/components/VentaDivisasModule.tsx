import { useEffect, useMemo, useState } from "react";
import { ClientType, getAppliedRate } from "../lib/clientRates";
import { useTasas } from "../lib/useTasas";
import { etiquetaMedioPago, listarMediosPago, type MedioPago } from "../lib/mediosPagoApi";
import { cancelarOperacion, crearOperacion, pagarOperacion, type Operacion } from "../lib/operacionesApi";

type AccountType = "Cuenta Corriente" | "Caja de Ahorro" | "Billetera Digital";
type TransferTarget = "propia" | "tercero";

const formatCurrency = (value: number) =>
  new Intl.NumberFormat("es-PY", {
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(value);

export default function VentaDivisasModule({
  userType,
  descuentoCompra,
  clienteId,
}: {
  userType: ClientType;
  descuentoCompra: number;
  // Cliente a nombre del cual se opera (RN02). null si el usuario no tiene ninguno.
  clienteId: string | null;
}) {
  const [amount, setAmount] = useState("100");
  const [currency, setCurrency] = useState<string>("");
  const [bank, setBank] = useState("Banco Itaú");
  const [accountNumber, setAccountNumber] = useState("");
  const [accountType, setAccountType] = useState<AccountType>("Caja de Ahorro");
  const [target, setTarget] = useState<TransferTarget>("propia");
  const [holderName, setHolderName] = useState("");
  const [holderDocument, setHolderDocument] = useState("");
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  // La operación ya creada en el backend (pendiente), con el cálculo real.
  const [operacion, setOperacion] = useState<Operacion | null>(null);
  const [procesando, setProcesando] = useState(false);
  const [savedMethods, setSavedMethods] = useState<MedioPago[]>([]);
  const [paymentMethod, setPaymentMethod] = useState("nuevo");

  useEffect(() => {
    void listarMediosPago()
      .then(({ medios }) => setSavedMethods(medios.filter((medio) => medio.activo)))
      .catch(() => setSavedMethods([]));
  }, []);

  useEffect(() => {
    if (savedMethods.length > 0 && paymentMethod === "nuevo") {
      setPaymentMethod(String(savedMethods[0].id));
    }
  }, [paymentMethod, savedMethods]);

  // Cotizaciones reales de la base, en vez de una tabla fija.
  const { tasas, codigos, cargando } = useTasas();

  useEffect(() => {
    if (!currency && codigos.length > 0) setCurrency(codigos[0]);
  }, [codigos, currency]);

  const tasa = tasas[currency] ?? { compra: 0, venta: 0 };

  const numericAmount = Number.parseFloat(amount) || 0;
  const baseRate = tasa.compra;
  const conversionRate = getAppliedRate(tasa, "compra", descuentoCompra);
  const totalToReceive = numericAmount * conversionRate;
  const isNewPaymentMethod = paymentMethod === "nuevo";
  const selectedMethod = savedMethods.find((medio) => String(medio.id) === paymentMethod);

  const summaryTarget = useMemo(() => {
    if (target === "propia") {
      return `Cuenta ${bank} - ${accountType} N° ${accountNumber || "XXXX1234"} a nombre de ${holderName || "Usuario logueado"}`;
    }

    return `Cuenta ${bank} - ${accountType} N° ${accountNumber || "XXXX1234"} a nombre de ${holderName || "Destinatario"}`;
  }, [accountNumber, accountType, bank, holderName, target]);

  const mensajeDeError = (error: unknown, porDefecto: string) =>
    error instanceof Error ? error.message : porDefecto;

  // "Vender" crea la operación pendiente en el backend, que calcula la tasa
  // y la comisión. El modal muestra ese cálculo.
  const handleVender = async () => {
    if (!clienteId) return;
    setSuccessMessage(null);
    setErrorMessage(null);
    setProcesando(true);
    try {
      const nueva = await crearOperacion({
        clienteId,
        tipo: "VENTA",
        moneda: currency,
        monto: numericAmount,
        medioPagoId: isNewPaymentMethod ? null : selectedMethod?.id ?? null,
      });
      setOperacion(nueva);
      setIsModalOpen(true);
    } catch (error) {
      setErrorMessage(mensajeDeError(error, "No se pudo crear la operación."));
    } finally {
      setProcesando(false);
    }
  };

  // Al confirmar, el backend vuelve a mirar la cotización: si cambió,
  // cancela la operación en vez de completarla.
  const handleConfirm = async () => {
    if (!operacion) return;
    setProcesando(true);
    try {
      const resultado = await pagarOperacion(operacion.id);
      if (resultado.estado === "PAGADA") {
        setSuccessMessage(`Venta #${resultado.id} confirmada: vas a recibir ${formatCurrency(resultado.totalGuaranies)} PYG.`);
      } else {
        setErrorMessage(resultado.motivoCancelacion ?? "La operación fue cancelada.");
      }
    } catch (error) {
      setErrorMessage(mensajeDeError(error, "No se pudo confirmar la venta."));
    } finally {
      setProcesando(false);
      setIsModalOpen(false);
      setOperacion(null);
    }
  };

  // Cerrar el modal sin confirmar cancela la operación, para que no quede
  // pendiente para siempre.
  const handleCancelar = async () => {
    if (operacion) await cancelarOperacion(operacion.id).catch(() => undefined);
    setOperacion(null);
    setIsModalOpen(false);
  };

  return (
    <div className="space-y-6">
      <div className="rounded-3xl border border-[#dbe3ee] bg-white p-6 shadow-sm">
        <div className="mb-6">
          <p className="text-sm font-medium text-[#64748b]">Venta de divisas</p>
          <h2 className="text-2xl font-bold tracking-tight text-[#0f172a]">Cobro en Guaraníes</h2>
        </div>

        <div className="grid gap-5 md:grid-cols-[1.5fr_0.8fr]">
          <label className="block">
            <span className="mb-2 block text-sm font-medium text-[#374151]">Monto a vender</span>
            <div className="flex overflow-hidden rounded-xl border border-[#dbe3ee] bg-[#f8fafc] focus-within:border-[#1a7eff]">
              <input
                type="number"
                min="0"
                step="0.01"
                value={amount}
                onChange={(event) => setAmount(event.target.value)}
                className="w-full bg-transparent px-4 py-3 text-lg font-semibold text-[#0f172a] outline-none"
                placeholder="100"
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
            <p className="text-xs uppercase tracking-[0.18em] text-[#64748b]">Tasa de compra aplicada</p>
            <p className="mt-2 text-lg font-bold text-[#0f172a]">1 {currency} = {formatCurrency(conversionRate)} PYG</p>
            <p className="mt-1 text-xs text-[#64748b]">Base: {formatCurrency(baseRate)} PYG • {userType}</p>
          </div>
        </div>

        <div className="mt-5 rounded-2xl border border-[#dbe3ee] bg-[#f0f7ff] p-4">
          <p className="text-sm text-[#64748b]">Monto a recibir en PYG</p>
          <p className="mt-1 text-2xl font-bold text-[#1a7eff]">{formatCurrency(totalToReceive)} PYG</p>
        </div>

        <div className="mt-8 rounded-2xl border border-[#dbe3ee] bg-[#f8fafc] p-5">
          <h3 className="text-lg font-semibold text-[#0f172a]">Datos para la acreditación</h3>
          <label className="mt-4 block">
            <span className="mb-2 block text-sm font-medium text-[#374151]">Método de acreditación</span>
            <select value={paymentMethod} onChange={(event) => setPaymentMethod(event.target.value)} className="w-full rounded-xl border border-[#dbe3ee] bg-white px-3 py-2.5 text-sm">
              {savedMethods.map((medio) => <option key={medio.id} value={medio.id}>{etiquetaMedioPago(medio)}</option>)}
              <option value="nuevo">Agregar nuevo método de pago...</option>
            </select>
          </label>
          {!isNewPaymentMethod && selectedMethod && (
            <p className="mt-3 rounded-xl border border-green-200 bg-green-50 px-3 py-2 text-sm text-green-700">
              Se utilizarán los datos guardados de «{etiquetaMedioPago(selectedMethod)}».
            </p>
          )}
          {isNewPaymentMethod && <div className="mt-4 grid gap-4 md:grid-cols-2">
          <div className="mt-4 grid gap-4 md:grid-cols-2">
            <label className="block">
              <span className="mb-2 block text-sm font-medium text-[#374151]">Banco / Entidad financiera</span>
              <select
                value={bank}
                onChange={(event) => setBank(event.target.value)}
                className="w-full rounded-xl border border-[#dbe3ee] bg-white px-3 py-2.5 text-sm text-[#1f2937] outline-none focus:border-[#1a7eff]"
              >
                <option value="Banco Itaú">Banco Itaú</option>
                <option value="Banco GNB">Banco GNB</option>
                <option value="Banco Continental">Banco Continental</option>
                <option value="Billetera Personal">Billetera Personal</option>
              </select>
            </label>

            <label className="block">
              <span className="mb-2 block text-sm font-medium text-[#374151]">Número de cuenta / identificador</span>
              <input
                value={accountNumber}
                onChange={(event) => setAccountNumber(event.target.value)}
                placeholder="XXXX1234"
                className="w-full rounded-xl border border-[#dbe3ee] bg-white px-3 py-2.5 text-sm text-[#1f2937] outline-none focus:border-[#1a7eff]"
              />
            </label>

            <label className="block">
              <span className="mb-2 block text-sm font-medium text-[#374151]">Tipo de cuenta</span>
              <select
                value={accountType}
                onChange={(event) => setAccountType(event.target.value as AccountType)}
                className="w-full rounded-xl border border-[#dbe3ee] bg-white px-3 py-2.5 text-sm text-[#1f2937] outline-none focus:border-[#1a7eff]"
              >
                <option value="Cuenta Corriente">Cuenta Corriente</option>
                <option value="Caja de Ahorro">Caja de Ahorro</option>
                <option value="Billetera Digital">Billetera Digital</option>
              </select>
            </label>

            <div className="flex items-end">
              <div className="w-full rounded-xl border border-[#dbe3ee] bg-white p-2.5">
                <p className="text-xs uppercase tracking-[0.15em] text-[#64748b]">Destino</p>
                <div className="mt-2 flex items-center gap-3">
                  <button
                    type="button"
                    onClick={() => setTarget("propia")}
                    className={`rounded-lg px-3 py-1.5 text-xs font-semibold ${
                      target === "propia" ? "bg-[#1a7eff] text-white" : "bg-[#edf4ff] text-[#1a7eff]"
                    }`}
                  >
                    Mi propia cuenta
                  </button>
                  <button
                    type="button"
                    onClick={() => setTarget("tercero")}
                    className={`rounded-lg px-3 py-1.5 text-xs font-semibold ${
                      target === "tercero" ? "bg-[#1a7eff] text-white" : "bg-[#edf4ff] text-[#1a7eff]"
                    }`}
                  >
                    Tercero
                  </button>
                </div>
              </div>
            </div>

            <label className="block md:col-span-2">
              <span className="mb-2 block text-sm font-medium text-[#374151]">Titular de la cuenta</span>
              <input
                value={holderName}
                onChange={(event) => setHolderName(event.target.value)}
                placeholder={target === "propia" ? "Nombre del usuario logueado" : "Nombre completo del destinatario"}
                className="w-full rounded-xl border border-[#dbe3ee] bg-white px-3 py-2.5 text-sm text-[#1f2937] outline-none focus:border-[#1a7eff]"
              />
            </label>

            <label className="block md:col-span-2">
              <span className="mb-2 block text-sm font-medium text-[#374151]">Documento de identidad / RUC</span>
              <input
                value={holderDocument}
                onChange={(event) => setHolderDocument(event.target.value)}
                placeholder={target === "propia" ? "CI / RUC del usuario" : "CI / RUC del destinatario"}
                className="w-full rounded-xl border border-[#dbe3ee] bg-white px-3 py-2.5 text-sm text-[#1f2937] outline-none focus:border-[#1a7eff]"
              />
            </label>
          </div>
          </div>}
        </div>

        {successMessage && (
          <div className="mt-6 rounded-xl border border-green-200 bg-green-50 px-4 py-3 text-sm font-medium text-green-700">
            {successMessage}
          </div>
        )}

        {errorMessage && (
          <div className="mt-6 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm font-medium text-red-700">
            {errorMessage}
          </div>
        )}

        {!clienteId && (
          <p className="mt-6 text-sm text-[#64748b]">
            Tu usuario no está asociado a ningún cliente: por ahora solo podés consultar tasas.
          </p>
        )}

        <div className="mt-8 flex justify-end">
          <button
            onClick={() => void handleVender()}
            disabled={!clienteId || numericAmount <= 0 || procesando}
            className="rounded-xl bg-[#1a7eff] px-6 py-3 text-sm font-semibold text-white shadow-sm transition hover:bg-[#146be7] disabled:cursor-not-allowed disabled:bg-slate-300"
          >
            {procesando && !isModalOpen ? "Calculando..." : "Vender"}
          </button>
        </div>
      </div>

      {isModalOpen && operacion && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 px-4">
          <div className="w-full max-w-xl rounded-2xl bg-white p-6 shadow-2xl">
            <h3 className="text-2xl font-bold text-[#0f172a]">¿Desea confirmar la venta de divisas?</h3>

            <div className="mt-5 space-y-3 rounded-2xl border border-[#e2e8f0] bg-[#f8fafc] p-4 text-sm text-[#374151]">
              <div className="flex items-center justify-between gap-4">
                <span className="text-[#64748b]">Monto a entregar / vender</span>
                <span className="font-semibold text-[#0f172a]">{operacion.montoDivisa} {operacion.moneda}</span>
              </div>
              <div className="flex items-center justify-between gap-4">
                <span className="text-[#64748b]">Tasa de cambio aplicada</span>
                <span className="font-semibold text-[#0f172a]">1 {operacion.moneda} = {formatCurrency(operacion.tasaAplicada)} PYG</span>
              </div>
              <div className="flex items-center justify-between gap-4">
                <span className="text-[#64748b]">Cliente</span>
                <span className="font-semibold text-[#0f172a]">{operacion.cliente.nombre} ({userType})</span>
              </div>
              <div className="flex items-center justify-between gap-4">
                <span className="text-[#64748b]">Subtotal</span>
                <span className="font-semibold text-[#0f172a]">{formatCurrency(operacion.montoGuaranies)} PYG</span>
              </div>
              <div className="flex items-center justify-between gap-4">
                <span className="text-[#64748b]">Comisión ({operacion.porcentajeComision} %)</span>
                <span className="font-semibold text-[#0f172a]">− {formatCurrency(operacion.comision)} PYG</span>
              </div>
              <div className="flex items-center justify-between gap-4">
                <span className="text-[#64748b]">Total a recibir</span>
                <span className="font-semibold text-[#0f172a]">{formatCurrency(operacion.totalGuaranies)} PYG</span>
              </div>
              <div className="flex items-start justify-between gap-4">
                <span className="text-[#64748b]">Cuenta de destino</span>
                <span className="max-w-xs text-right font-semibold text-[#0f172a]">{selectedMethod ? etiquetaMedioPago(selectedMethod) : summaryTarget}</span>
              </div>
            </div>

            <p className="mt-5 text-sm text-[#475569]">
              Verifique que los datos de la cuenta bancaria sean correctos. La acreditación se procesará una vez confirmada la operación. Presione Confirmar para finalizar.
            </p>

            <div className="mt-6 flex justify-end gap-3">
              <button
                onClick={() => void handleCancelar()}
                disabled={procesando}
                className="rounded-xl border border-[#dbe3ee] bg-white px-4 py-2.5 text-sm font-semibold text-[#374151] hover:bg-[#f8fafc]"
              >
                Cancelar
              </button>
              <button
                onClick={() => void handleConfirm()}
                disabled={procesando}
                className="rounded-xl bg-[#1a7eff] px-4 py-2.5 text-sm font-semibold text-white hover:bg-[#146be7] disabled:bg-slate-300"
              >
                {procesando ? "Procesando..." : "Confirmar Venta"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
