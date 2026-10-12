import { useEffect, useState } from "react";
import { ClientType, getAppliedRate } from "../lib/clientRates";
import { useTasas } from "../lib/useTasas";
import { confirmarOperacion, cotizarOperacion, type NuevaOperacion, type Operacion, type Presupuesto } from "../lib/operacionesApi";
import { etiquetaMedioPago, listarMediosPago, type MedioPago } from "../lib/mediosPagoApi";
import { completarPagoOperacion } from "../lib/pagosApi";
import AlertaCancelacionModal from "./AlertaCancelacionModal";


const formatCurrency = (value: number) =>
  new Intl.NumberFormat("es-PY", {
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(value);

export default function CompraDivisasModule({
  userType,
  descuentoCompra,
  clienteId,
}: {
  userType: ClientType;
  descuentoCompra: number;
  // Cliente a nombre del cual se opera (RN02). null si el usuario no tiene ninguno.
  clienteId: string | null;
}) {
  const [amount, setAmount] = useState("500");
  const [currency, setCurrency] = useState<string>("");
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  // Cálculo del backend que muestra el modal. La operación todavía no existe:
  // se registra recién al confirmar, así que cerrar el modal o recargar la
  // página no deja nada pendiente en el historial.
  const [operacion, setOperacion] = useState<Presupuesto | null>(null);
  // Los datos con los que se pidió ese cálculo, para confirmar exactamente eso.
  const [pedido, setPedido] = useState<NuevaOperacion | null>(null);
  const [procesando, setProcesando] = useState(false);
  // Operación que se canceló sola porque cambió la cotización (IS2GE-71).
  const [alerta, setAlerta] = useState<Operacion | null>(null);
  // Tarjetas de Stripe del usuario: con una se cobra el total en guaraníes.
  // "" = pagar por fuera (transferencia, etc.), como antes de Stripe.
  const [tarjetas, setTarjetas] = useState<MedioPago[]>([]);
  const [tarjetaId, setTarjetaId] = useState("");

  useEffect(() => {
    void listarMediosPago()
      .then(({ medios }) => {
        const conTarjeta = medios.filter((medio) => medio.activo && medio.tarjeta);
        setTarjetas(conTarjeta);
        if (conTarjeta.length > 0) setTarjetaId(String(conTarjeta[0].id));
      })
      .catch(() => setTarjetas([]));
  }, []);
  const tarjetaElegida = tarjetas.find((medio) => String(medio.id) === tarjetaId);

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

  const mensajeDeError = (error: unknown, porDefecto: string) =>
    error instanceof Error ? error.message : porDefecto;

  // "Comprar" le pide al backend el cálculo (tasa aplicada, comisión, total)
  // sin guardar nada. El modal muestra ese cálculo, no la vista previa de arriba.
  const handleComprar = async () => {
    if (!clienteId) return;
    setSuccessMessage(null);
    setErrorMessage(null);
    setProcesando(true);
    const datos: NuevaOperacion = {
      clienteId,
      tipo: "COMPRA",
      moneda: currency,
      monto: numericAmount,
      medioPagoId: tarjetaElegida?.id ?? null,
    };
    try {
      setOperacion(await cotizarOperacion(datos));
      setPedido(datos);
      setIsModalOpen(true);
    } catch (error) {
      setErrorMessage(mensajeDeError(error, "No se pudo calcular la operación."));
    } finally {
      setProcesando(false);
    }
  };

  const handleConfirm = async () => {
    if (!operacion || !pedido) return;
    setProcesando(true);
    try {
      // Recién acá se registra la operación. Si la cotización cambió desde el
      // cálculo, el backend la registra cancelada en vez de cobrarla.
      // Con tarjeta, el backend cobra en Stripe; si el banco pide 3D Secure,
      // completarPagoOperacion muestra la verificación y confirma el pago.
      const resultado = await completarPagoOperacion(
        await confirmarOperacion({ ...pedido, tasaBase: operacion.tasaBase }),
      );
      if (resultado.estado === "PAGADA") {
        setSuccessMessage(
          `Operación #${resultado.id} pagada: ${formatCurrency(resultado.totalGuaranies)} PYG` +
          (resultado.pagoConTarjeta ? " cobrados a tu tarjeta." : "."),
        );
      } else if (resultado.canceladaPorCotizacion) {
        setAlerta(resultado);
      } else {
        setErrorMessage(resultado.motivoCancelacion ?? "La operación fue cancelada.");
      }
    } catch (error) {
      setErrorMessage(mensajeDeError(error, "No se pudo completar el pago."));
    } finally {
      setProcesando(false);
      setIsModalOpen(false);
      setOperacion(null);
      setPedido(null);
    }
  };

  // Cerrar el modal sin confirmar: la operación nunca se registró, así que no
  // hay nada que cancelar en el backend.
  const handleCancelar = () => {
    setOperacion(null);
    setPedido(null);
    setIsModalOpen(false);
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

        <label className="mt-5 block">
          <span className="mb-2 block text-sm font-medium text-[#374151]">Pagar con</span>
          <select value={tarjetaId} onChange={(event) => setTarjetaId(event.target.value)} className="w-full rounded-xl border border-[#dbe3ee] bg-white px-3 py-2.5 text-sm">
            {tarjetas.map((medio) => <option key={medio.id} value={medio.id}>{etiquetaMedioPago(medio)}</option>)}
            <option value="">Otro medio (transferencia, sin cobro en línea)</option>
          </select>
          {tarjetas.length === 0 && (
            <span className="mt-2 block text-xs text-[#64748b]">Para pagar con tarjeta, cargá una en «Configuración de Datos → Métodos de pago».</span>
          )}
        </label>

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
            onClick={() => void handleComprar()}
            disabled={!clienteId || numericAmount <= 0 || procesando}
            className="rounded-xl bg-[#1a7eff] px-6 py-3 text-sm font-semibold text-white shadow-sm transition hover:bg-[#146be7] disabled:cursor-not-allowed disabled:bg-slate-300"
          >
            {procesando && !isModalOpen ? "Calculando..." : "Comprar"}
          </button>
        </div>
      </div>

      {isModalOpen && operacion && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 px-4">
          <div className="w-full max-w-xl rounded-2xl bg-white p-6 shadow-2xl">
            <h3 className="text-2xl font-bold text-[#0f172a]">¿Desea realizar la transacción de compra?</h3>

            <div className="mt-5 space-y-3 rounded-2xl border border-[#e2e8f0] bg-[#f8fafc] p-4 text-sm text-[#374151]">
              <div className="flex items-center justify-between gap-4">
                <span className="text-[#64748b]">Monto a comprar / cambiar</span>
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
                <span className="font-semibold text-[#0f172a]">+ {formatCurrency(operacion.comision)} PYG</span>
              </div>
              <div className="flex items-center justify-between gap-4">
                <span className="text-[#64748b]">Total a pagar en PYG</span>
                <span className="font-semibold text-[#0f172a]">{formatCurrency(operacion.totalGuaranies)} PYG</span>
              </div>
              <div className="flex items-center justify-between gap-4">
                <span className="text-[#64748b]">Método de pago</span>
                <span className="font-semibold text-[#0f172a]">{operacion.medioPago ?? "Sin especificar"}</span>
              </div>
            </div>

            <p className="mt-5 text-sm text-[#475569]">
              {pedido?.medioPagoId && tarjetaElegida
                ? `Al confirmar se cobrarán ${formatCurrency(operacion.totalGuaranies)} PYG a ${etiquetaMedioPago(tarjetaElegida)}. `
                : "Si los datos son correctos, presione Confirmar. "}
              Si la cotización cambia antes del pago, la operación se cancela sin cobrarle nada.
            </p>

            <div className="mt-6 flex justify-end gap-3">
              <button
                onClick={handleCancelar}
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
                {procesando ? "Procesando..." : "Confirmar"}
              </button>
            </div>
          </div>
        </div>
      )}

      {alerta && (
        <AlertaCancelacionModal
          operacion={alerta}
          procesando={procesando}
          onReintentar={() => {
            setAlerta(null);
            void handleComprar();
          }}
          onCerrar={() => setAlerta(null)}
        />
      )}
    </div>
  );
}
