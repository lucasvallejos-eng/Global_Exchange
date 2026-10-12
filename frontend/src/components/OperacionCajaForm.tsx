import { useEffect, useState } from "react";
import { getClientPreferredRate, listClients, type TasaPreferencial } from "../lib/clientesApi";
import {
  listarDenominacionesPorMoneda,
  registrarCompraCaja,
  registrarVentaCaja,
  type CajaMoneda,
  type OperacionCajaEntrada,
} from "../lib/cajaApi";
import { listarMediosPago, type TipoMedioPago } from "../lib/mediosPagoApi";
import { completarVerificacion, tarjetasDelCliente, type TarjetaCliente } from "../lib/pagosApi";
import { useTasas } from "../lib/useTasas";
import type { Client } from "../types";

type Props = { tipo: "compra" | "venta" };

// El medio de cobro elegido: "efectivo", "tipo:<clave>" (venta sin tarjeta,
// queda registrado como texto) o "tarjeta:<id>" (se cobra con Stripe).
const EFECTIVO = "efectivo";
// En la venta, el efectivo se manda como tipo de pago: el backend lo usa para
// sumar los guaraníes al cajón en el arqueo.
const EFECTIVO_VENTA = "EFECTIVO";

const formatNumber = (value: number) =>
  new Intl.NumberFormat("es-PY", { maximumFractionDigits: 0 }).format(value);

export default function OperacionCajaForm({ tipo }: Props) {
  const [clientes, setClientes] = useState<Client[]>([]);
  const [tipos, setTipos] = useState<TipoMedioPago[]>([]);
  const [monedasCaja, setMonedasCaja] = useState<CajaMoneda[]>([]);
  const [clienteId, setClienteId] = useState("");
  const [moneda, setMoneda] = useState("");
  const [monto, setMonto] = useState("");
  const [tipoPago, setTipoPago] = useState("");
  const [mensaje, setMensaje] = useState<string | null>(null);
  const [tarjetas, setTarjetas] = useState<TarjetaCliente[]>([]);
  const [enviando, setEnviando] = useState(false);
  const [preferencial, setPreferencial] = useState<TasaPreferencial | null>(null);
  const { tasas, codigos, cargando } = useTasas();

  useEffect(() => {
    listClients().then(setClientes).catch(() => setClientes([]));
    if (tipo === "venta") {
      listarMediosPago()
        .then(({ tipos: disponibles }) => setTipos(disponibles.filter((t) => t.activo)))
        .catch(() => setTipos([]));
      listarDenominacionesPorMoneda()
        .then((monedas) => setMonedasCaja(monedas.filter((m) => !m.esLocal)))
        .catch(() => setMonedasCaja([]));
    }
  }, [tipo]);

  useEffect(() => {
    if (!clienteId) {
      setPreferencial(null);
      setTarjetas([]);
      return;
    }
    getClientPreferredRate(Number(clienteId)).then(setPreferencial).catch(() => setPreferencial(null));
    // Tarjetas que los usuarios del cliente cargaron en Stripe.
    tarjetasDelCliente(clienteId).then(setTarjetas).catch(() => setTarjetas([]));
  }, [clienteId]);

  // Si se cambia de cliente, una tarjeta del cliente anterior ya no vale.
  useEffect(() => {
    if (tipoPago.startsWith("tarjeta:") && !tarjetas.some((t) => `tarjeta:${t.id}` === tipoPago)) {
      setTipoPago(tipo === "compra" ? EFECTIVO : "");
    }
  }, [tarjetas, tipoPago, tipo]);

  useEffect(() => {
    if (tipo === "venta" && monedasCaja.length > 0) {
      if (!moneda || !monedasCaja.some((m) => m.codigo === moneda)) {
        const primeraValida = monedasCaja.find((m) => m.tieneDenominaciones);
        if (primeraValida) {
          setMoneda(primeraValida.codigo);
        } else if (monedasCaja.length > 0) {
          setMoneda(monedasCaja[0].codigo);
        }
      }
    } else {
      if (!moneda && codigos.length) setMoneda(codigos[0]);
    }
    if (!clienteId && clientes.length) setClienteId(String(clientes[0].id));
    if (tipo === "compra" && !tipoPago) setTipoPago(EFECTIVO);
    if (tipo === "venta" && !tipoPago) setTipoPago(`tipo:${EFECTIVO_VENTA}`);
  }, [clienteId, clientes, codigos, tipoPago, tipos, moneda, tipo, monedasCaja]);

  const tasaBase = tasas[moneda]?.[tipo === "compra" ? "compra" : "venta"] ?? 0;
  const porcentaje = Number(preferencial?.porcentajePreferencial ?? 0);
  const tasa = tipo === "compra" ? tasaBase * (1 + porcentaje / 100) : tasaBase * (1 - porcentaje / 100);
  const total = (Number(monto) || 0) * tasa;

  const monedaSeleccionada = tipo === "venta" ? monedasCaja.find((m) => m.codigo === moneda) : null;
  const sinDenominaciones =
    tipo === "venta" &&
    monedasCaja.length > 0 &&
    (!monedaSeleccionada || !monedaSeleccionada.tieneDenominaciones);

  const tarjetaElegida = tarjetas.find((t) => `tarjeta:${t.id}` === tipoPago);
  // Con tarjeta: en la venta se cobra el total en guaraníes; en la compra, la
  // divisa que entrega el cliente (no entra al cajón, no cuenta en el arqueo).
  const montoACobrar = tipo === "venta" ? `${formatNumber(total)} PYG` : `${monto || 0} ${moneda}`;

  const registrar = (datos: OperacionCajaEntrada) =>
    tipo === "compra" ? registrarCompraCaja(datos) : registrarVentaCaja(datos);

  const enviar = async () => {
    setEnviando(true);
    try {
      if (!clienteId || !moneda || !(Number(monto) > 0)) throw new Error("Complete cliente, moneda y monto.");
      if (tipo === "venta" && sinDenominaciones) {
        throw new Error("La moneda seleccionada no posee denominaciones registradas.");
      }
      if (!tipoPago) throw new Error("Seleccione un medio de pago.");
      const datos: OperacionCajaEntrada = { cliente_id: clienteId, moneda, monto_divisa: Number(monto) };
      if (tarjetaElegida) datos.medio_pago_id = tarjetaElegida.id;
      else if (tipoPago.startsWith("tipo:")) datos.tipo_pago = tipoPago.slice("tipo:".length);

      let respuesta = await registrar(datos);
      if (respuesta.pagoPendiente) {
        // El banco pidió 3D Secure: el cliente lo completa y se reenvía la
        // operación con el pago ya verificado.
        await completarVerificacion(respuesta.pagoPendiente.clientSecret);
        respuesta = await registrar({ ...datos, payment_intent_id: respuesta.pagoPendiente.paymentIntentId });
      }
      setMensaje(
        respuesta.pagoConTarjeta
          ? `Operación registrada: se cobraron ${montoACobrar} a la tarjeta.`
          : "Operación registrada correctamente.",
      );
      setMonto("");
    } catch (error) {
      setMensaje(error instanceof Error ? error.message : "No se pudo registrar la operación.");
    } finally {
      setEnviando(false);
    }
  };

  return (
    <div className="rounded-3xl border border-[#dbe3ee] bg-white p-6 shadow-sm">
      <p className="text-sm font-medium text-[#64748b]">{tipo === "compra" ? "Compra de divisas" : "Venta de divisas"}</p>
      <h2 className="text-2xl font-bold tracking-tight text-[#0f172a]">{tipo === "compra" ? "Ingreso de divisas" : "Salida de divisas"}</h2>
      <div className="mt-6 grid gap-4 md:grid-cols-2">
        <label className="block">
          <span className="mb-2 block text-sm font-medium">Cliente</span>
          <select value={clienteId} onChange={(event) => setClienteId(event.target.value)} className="w-full rounded-xl border bg-[#f8fafc] px-3 py-2.5">
            <option value="">Seleccione un cliente</option>
            {clientes.map((cliente) => (
              <option key={cliente.id} value={cliente.id}>{cliente.nombre}</option>
            ))}
          </select>
        </label>
        <label className="block">
          <span className="mb-2 block text-sm font-medium">Moneda</span>
          <select
            value={moneda}
            onChange={(event) => setMoneda(event.target.value)}
            disabled={cargando}
            className="w-full rounded-xl border bg-[#f8fafc] px-3 py-2.5"
          >
            {tipo === "venta" && monedasCaja.length > 0
              ? monedasCaja.map((m) => (
                  <option key={m.id} value={m.codigo} disabled={!m.tieneDenominaciones}>
                    {m.nombre} {!m.tieneDenominaciones ? "(Sin Denominaciones)" : `(${m.codigo})`}
                  </option>
                ))
              : codigos.map((codigo) => (
                  <option key={codigo} value={codigo}>{codigo}</option>
                ))}
          </select>
        </label>
        <label className="block">
          <span className="mb-2 block text-sm font-medium">Monto a {tipo === "compra" ? "comprar" : "vender"}</span>
          <input type="number" min="0" step="0.01" value={monto} onChange={(event) => setMonto(event.target.value)} className="w-full rounded-xl border bg-[#f8fafc] px-3 py-2.5" />
        </label>
        <label className="block">
          <span className="mb-2 block text-sm font-medium">Medio de pago</span>
          <select value={tipoPago} onChange={(event) => setTipoPago(event.target.value)} className="w-full rounded-xl border bg-[#f8fafc] px-3 py-2.5">
            {tipo === "compra" ? (
              <option value={EFECTIVO}>Efectivo</option>
            ) : (
              <>
                <option value={`tipo:${EFECTIVO_VENTA}`}>Efectivo</option>
                {tipos.map((t) => (
                  <option key={t.valor} value={`tipo:${t.valor}`}>{t.texto}</option>
                ))}
              </>
            )}
            {tarjetas.length > 0 && (
              <optgroup label="Cobrar con tarjeta del cliente (Stripe)">
                {tarjetas.map((t) => (
                  <option key={t.id} value={`tarjeta:${t.id}`}>{t.nombre} · {t.titular}</option>
                ))}
              </optgroup>
            )}
          </select>
          {tarjetaElegida && (
            <span className="mt-2 block text-xs text-[#1a7eff]">Se cobrarán {montoACobrar} a la tarjeta al registrar.</span>
          )}
        </label>
      </div>
      <div className="mt-5 rounded-2xl border border-[#dbe3ee] bg-[#f0f7ff] p-4">
        <p className="text-sm text-[#64748b]">Categoría: {preferencial?.categoria ?? "Sin categoría"} · Preferencial: {porcentaje.toFixed(2)}%</p>
        {porcentaje > 0 && <span className="mt-1 inline-block rounded-full bg-emerald-100 px-2 py-1 text-xs font-semibold text-emerald-700">Tasa preferencial aplicada</span>}
        <p className="mt-2 text-sm text-[#64748b]">Cotización aplicada</p>
        <p className="font-semibold">1 {moneda} = {formatNumber(tasa)} PYG</p>
        <p className="mt-1 text-2xl font-bold text-[#1a7eff]">{formatNumber(total)} PYG</p>
      </div>
      <button
        onClick={() => void enviar()}
        disabled={sinDenominaciones || enviando}
        className="mt-5 rounded-xl bg-[#1a7eff] px-4 py-2.5 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:opacity-50"
      >
        {enviando ? "Procesando..." : `Registrar ${tipo}`}
      </button>
      {mensaje && <p className="mt-4 rounded-xl bg-[#f8fafc] px-3 py-2 text-sm text-[#475569]">{mensaje}</p>}
    </div>
  );
}
