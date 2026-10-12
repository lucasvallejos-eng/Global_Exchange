"""Integración con Stripe (modo test): tarjetas y cobros.

Todo lo que habla con Stripe pasa por acá, así el resto del sistema no conoce
la librería y los tests pueden reemplazar estas funciones.

- **Tarjetas:** se cargan en el navegador con Stripe Elements. El número y el
  CVV nunca llegan a nuestro backend: Stripe devuelve un ``PaymentMethod``
  (``pm_...``) y de él solo guardamos marca, últimos 4 dígitos y vencimiento.
- **Cobros:** un ``PaymentIntent`` confirmado con la tarjeta guardada. Si el
  banco pide 3D Secure, el cobro queda en ``requiere_accion`` y el navegador
  completa la verificación con el ``client_secret``; después se vuelve a
  consultar a Stripe con ``verificar_cobro``.

No hay webhooks: el estado del pago se consulta a Stripe en el momento.
"""
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

import stripe
from django.conf import settings

from .models import CuentaStripe

# Monedas sin centavos para Stripe: el monto se manda tal cual (PYG incluido).
# Las demás van en centavos. https://docs.stripe.com/currencies#zero-decimal
MONEDAS_SIN_DECIMALES = {
    "BIF", "CLP", "DJF", "GNF", "JPY", "KMF", "KRW", "MGA", "PYG",
    "RWF", "UGX", "VND", "VUV", "XAF", "XOF", "XPF",
}


class PagoRechazado(Exception):
    """El cobro no se pudo hacer. El mensaje se puede mostrar al usuario."""


@dataclass
class Cobro:
    """Resultado de un cobro. ``estado``: ``aprobado`` o ``requiere_accion``."""

    id: str
    estado: str
    client_secret: str


def habilitado():
    return bool(settings.STRIPE_SECRET_KEY and settings.STRIPE_PUBLISHABLE_KEY)


def _cliente_stripe():
    if not habilitado():
        raise PagoRechazado("Los pagos con tarjeta no están configurados (faltan las claves de Stripe).")
    return stripe.StripeClient(settings.STRIPE_SECRET_KEY)


def monto_en_unidad_minima(monto, moneda_codigo):
    """El monto en la unidad que espera Stripe (centavos, o entero si no tiene)."""
    monto = Decimal(monto)
    if moneda_codigo.upper() not in MONEDAS_SIN_DECIMALES:
        monto *= 100
    return int(monto.quantize(Decimal("1"), ROUND_HALF_UP))


def customer_de(usuario):
    """El Customer de Stripe del usuario; lo crea la primera vez."""
    cuenta = CuentaStripe.objects.filter(usuario=usuario).first()
    if cuenta:
        return cuenta.customer_id
    customer = _cliente_stripe().v1.customers.create(params={
        "email": usuario.email or None,
        "name": usuario.get_full_name() or usuario.get_username(),
        "metadata": {"usuario_id": str(usuario.pk), "username": usuario.get_username()},
    })
    CuentaStripe.objects.create(usuario=usuario, customer_id=customer.id)
    return customer.id


def preparar_tarjeta(usuario):
    """Crea un SetupIntent para cargar una tarjeta. Devuelve su ``client_secret``."""
    setup = _cliente_stripe().v1.setup_intents.create(params={
        "customer": customer_de(usuario),
        "payment_method_types": ["card"],
        "usage": "off_session",
    })
    return setup.client_secret


def tarjeta_registrada(usuario, setup_intent_id):
    """Lee la tarjeta que el navegador guardó con el SetupIntent.

    Verifica que el SetupIntent sea del Customer de este usuario y que haya
    terminado bien, para que nadie registre una tarjeta ajena.

    Returns:
        dict: ``payment_method_id``, ``marca``, ``ultimos4``, ``vencimiento`` (MM/YY).
    """
    cliente = _cliente_stripe()
    setup = cliente.v1.setup_intents.retrieve(setup_intent_id)
    if setup.customer != customer_de(usuario) or setup.status != "succeeded":
        raise PagoRechazado("No se pudo verificar la tarjeta. Intentá cargarla de nuevo.")
    metodo = cliente.v1.payment_methods.retrieve(setup.payment_method)
    tarjeta = metodo.card
    return {
        "payment_method_id": metodo.id,
        "marca": tarjeta.brand.capitalize(),
        "ultimos4": tarjeta.last4,
        "vencimiento": f"{tarjeta.exp_month:02d}/{tarjeta.exp_year % 100:02d}",
    }


def desvincular_tarjeta(payment_method_id):
    """Saca la tarjeta del Customer en Stripe (ya no se puede cobrar con ella)."""
    try:
        _cliente_stripe().v1.payment_methods.detach(payment_method_id)
    except stripe.StripeError:
        pass  # Si ya no existía en Stripe, no hay nada que desvincular.


def cobrar(medio_pago, monto, moneda_codigo, descripcion, metadata=None):
    """Cobra ``monto`` en ``moneda_codigo`` a la tarjeta guardada en ``medio_pago``.

    Raises:
        PagoRechazado: si el medio no es una tarjeta de Stripe o el banco la rechaza.
    """
    if not medio_pago.stripe_payment_method_id:
        raise PagoRechazado("Ese medio de pago no es una tarjeta habilitada para cobrar.")
    try:
        intento = _cliente_stripe().v1.payment_intents.create(params={
            "amount": monto_en_unidad_minima(monto, moneda_codigo),
            "currency": moneda_codigo.lower(),
            "customer": customer_de(medio_pago.usuario),
            "payment_method": medio_pago.stripe_payment_method_id,
            "payment_method_types": ["card"],
            "confirm": True,
            "description": descripcion,
            "metadata": {k: str(v) for k, v in (metadata or {}).items()},
        })
    except stripe.CardError as error:
        raise PagoRechazado(f"La tarjeta fue rechazada: {error.user_message or 'sin detalle'}") from error
    except stripe.StripeError as error:
        raise PagoRechazado(f"No se pudo procesar el pago con Stripe: {error.user_message or error}") from error
    return _cobro(intento)


def verificar_cobro(payment_intent_id, monto, moneda_codigo):
    """Consulta a Stripe un cobro que quedó esperando 3D Secure.

    Verifica también monto y moneda: el navegador manda el id, y no se puede
    confiar en que sea el del cobro que corresponde.

    Raises:
        PagoRechazado: si no coincide o la verificación falló.
    """
    try:
        intento = _cliente_stripe().v1.payment_intents.retrieve(payment_intent_id)
    except stripe.StripeError as error:
        raise PagoRechazado("No se encontró el pago en Stripe.") from error
    if (intento.amount != monto_en_unidad_minima(monto, moneda_codigo)
            or intento.currency != moneda_codigo.lower()):
        raise PagoRechazado("El pago no corresponde a esta operación.")
    cobro = _cobro(intento)
    if cobro.estado != "aprobado":
        raise PagoRechazado("El pago no se completó (la verificación del banco no se aprobó).")
    return cobro


def cancelar_cobro(payment_intent_id):
    """Cancela en Stripe un cobro que no se completó, para que no quede
    colgado. Si ya no se puede cancelar (por ejemplo, ya se aprobó), no hace nada."""
    try:
        _cliente_stripe().v1.payment_intents.cancel(payment_intent_id)
    except (stripe.StripeError, PagoRechazado):
        pass


def _cobro(intento):
    if intento.status == "succeeded":
        return Cobro(intento.id, "aprobado", intento.client_secret)
    if intento.status == "requires_action":
        return Cobro(intento.id, "requiere_accion", intento.client_secret)
    raise PagoRechazado("La tarjeta fue rechazada.")
