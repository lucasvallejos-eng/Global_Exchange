"""Arma y crea las notificaciones. Toda la redacción de los avisos vive acá.

Las demás apps llaman a estas funciones cuando pasa algo:

- ``operaciones.servicios``: compras y ventas de la web.
- ``caja.api``: compras y ventas en ventanilla.
- ``notificaciones.senales``: cambios de cotización.

Los montos se escriben como en Paraguay: punto para los miles y coma para los
decimales (74.000 PYG, 10,5 USD).
"""
from decimal import Decimal

from django.contrib.auth import get_user_model

from .models import Notificacion, PreferenciaNotificaciones

Categoria = PreferenciaNotificaciones.Categoria


def formatear_numero(valor):
    """10 -> "10", 1250.5 -> "1.250,5", 74000 -> "74.000"."""
    valor = Decimal(valor).normalize()
    if valor == valor.to_integral():
        valor = valor.quantize(Decimal("1"))
    texto = f"{valor:,f}"
    return texto.replace(",", "_").replace(".", ",").replace("_", ".")


def describir_medio(medio):
    """Cómo se nombra un medio de pago en los avisos."""
    if medio is None:
        return None
    if medio.stripe_payment_method_id:
        return f"{medio.alias} ({medio.banco_o_proveedor} •••• {medio.numero_cuenta_o_tarjeta})"
    if medio.tipo:
        return f"{medio.alias} ({medio.get_tipo_display()})"
    return medio.alias


def _interesados(usuarios, categoria, moneda=None):
    """Los usuarios (sin repetir) que según sus preferencias quieren este aviso."""
    destinatarios = {u.pk: u for u in usuarios if u is not None}
    preferencias = {
        p.usuario_id: p
        for p in PreferenciaNotificaciones.objects.filter(usuario_id__in=destinatarios).prefetch_related("monedas")
    }
    return [
        u for pk, u in destinatarios.items()
        if pk not in preferencias or preferencias[pk].acepta(categoria, moneda)
    ]


def notificar(usuarios, tipo, titulo, mensaje, datos=None, categoria=None, moneda=None):
    """Crea la misma notificación para cada usuario que la quiera recibir.

    ``categoria`` (compra, venta o cotización) se compara con las
    preferencias de cada uno; sin categoría, le llega a todos.
    """
    destinatarios = (
        _interesados(usuarios, categoria, moneda) if categoria
        else {u.pk: u for u in usuarios if u is not None}.values()
    )
    return Notificacion.objects.bulk_create([
        Notificacion(usuario=u, tipo=tipo, titulo=titulo, mensaje=mensaje, datos=datos or {})
        for u in destinatarios
    ])


# --- Operaciones de la web -----------------------------------------------------

def _nombre(tipo):
    return "Compra" if tipo == "COMPRA" else "Venta"


def operacion_web_exitosa(transaccion, usuario):
    """La compra o venta de la web quedó pagada."""
    moneda = transaccion.moneda.codigo
    divisa = f"{formatear_numero(transaccion.monto_divisa)} {moneda}"
    total = f"{formatear_numero(transaccion.total_guaranies)} PYG"
    medio = describir_medio(transaccion.medio_pago) or transaccion.medio_pago_descripcion or None
    con_tarjeta = bool(transaccion.stripe_payment_intent_id)
    if transaccion.tipo == "COMPRA":
        mensaje = f"Compraste {divisa} por {total}"
        mensaje += f", cobrados a {medio}." if con_tarjeta else (f". Medio de pago: {medio}." if medio else ".")
    else:
        mensaje = f"Vendiste {divisa}; vas a recibir {total}."
        if con_tarjeta:
            mensaje += f" Se cobraron {divisa} a {medio}."
        elif medio:
            mensaje += f" Medio: {medio}."
    mensaje += f" Operación #{transaccion.pk}."
    notificar(
        [usuario], Notificacion.Tipo.OPERACION_EXITOSA, f"{_nombre(transaccion.tipo)} exitosa", mensaje,
        {"operacionId": transaccion.pk, "origen": "web", "tipo": transaccion.tipo, "moneda": moneda,
         "montoDivisa": float(transaccion.monto_divisa), "totalGuaranies": float(transaccion.total_guaranies),
         "medioPago": medio},
        categoria=transaccion.tipo,
    )


def operacion_web_fallida(usuario, tipo, moneda, monto_divisa, motivo, operacion_id=None):
    """La compra o venta de la web no se pudo completar.

    ``operacion_id`` es None cuando la operación ni siquiera quedó registrada
    (por ejemplo, la tarjeta se rechazó al confirmar).
    """
    mensaje = f"No se pudo completar la {_nombre(tipo).lower()} de {formatear_numero(monto_divisa)} {moneda}. Motivo: {motivo}"
    if operacion_id:
        mensaje += f" Operación #{operacion_id}."
    notificar(
        [usuario], Notificacion.Tipo.OPERACION_FALLIDA, f"{_nombre(tipo)} fallida", mensaje,
        {"operacionId": operacion_id, "origen": "web", "tipo": tipo, "moneda": moneda,
         "montoDivisa": float(monto_divisa), "motivo": motivo},
        categoria=tipo,
    )


# --- Caja ----------------------------------------------------------------------

def _caja_nombre(tipo):
    return "Compra en caja" if tipo == "compra" else "Venta en caja"


def _categorias_caja(tipo):
    """(categoría para el cajero, categoría para el dueño de la tarjeta).

    Cuando la casa compra divisa, el cliente la vende, y al revés.
    """
    if tipo == "compra":
        return Categoria.COMPRA, Categoria.VENTA
    return Categoria.VENTA, Categoria.COMPRA


def operacion_caja_exitosa(cajero, tipo, obj, forma_pago_texto, medio=None, importe_tarjeta=None):
    """Compra o venta de caja registrada. ``tipo``: "compra" o "venta".

    El cajero recibe el resultado. Si se cobró con la tarjeta de un cliente,
    el dueño de la tarjeta recibe el aviso del cobro (``importe_tarjeta``).
    """
    moneda = obj.moneda.codigo
    divisa = f"{formatear_numero(obj.monto_divisa)} {moneda}"
    total = f"{formatear_numero(obj.monto_local_total)} PYG"
    datos = {"operacionCajaId": obj.pk, "origen": "caja", "tipo": tipo.upper(), "moneda": moneda,
             "montoDivisa": float(obj.monto_divisa), "totalGuaranies": float(obj.monto_local_total),
             "medioPago": forma_pago_texto}
    accion = "Compraste" if tipo == "compra" else "Vendiste"
    del_cajero, del_duenio = _categorias_caja(tipo)
    notificar(
        [cajero], Notificacion.Tipo.OPERACION_EXITOSA, f"{_caja_nombre(tipo)} exitosa",
        f"{accion} {divisa} a {obj.cliente.nombre} por {total}. Medio de pago: {forma_pago_texto}. "
        f"Operación de caja #{obj.pk}.",
        datos, categoria=del_cajero,
    )
    if medio is not None and medio.usuario_id != getattr(cajero, "pk", None):
        notificar(
            [medio.usuario], Notificacion.Tipo.OPERACION_EXITOSA, "Cobro con tu tarjeta en caja",
            f"Se cobraron {importe_tarjeta} a {describir_medio(medio)} por una "
            f"{'venta' if tipo == 'compra' else 'compra'} de {divisa} en ventanilla "
            f"a nombre de {obj.cliente.nombre}.",
            datos, categoria=del_duenio,
        )


def operacion_caja_fallida(cajero, tipo, cliente, moneda_codigo, monto_divisa, motivo, medio=None):
    """Compra o venta de caja que no se registró porque el cobro con tarjeta falló."""
    divisa = f"{formatear_numero(monto_divisa)} {moneda_codigo}"
    datos = {"origen": "caja", "tipo": tipo.upper(), "moneda": moneda_codigo,
             "montoDivisa": float(monto_divisa), "motivo": motivo}
    del_cajero, del_duenio = _categorias_caja(tipo)
    notificar(
        [cajero], Notificacion.Tipo.OPERACION_FALLIDA, f"{_caja_nombre(tipo)} fallida",
        f"No se pudo registrar la {_caja_nombre(tipo).lower()} de {divisa} a {cliente.nombre}. Motivo: {motivo}",
        datos, categoria=del_cajero,
    )
    if medio is not None and medio.usuario_id != getattr(cajero, "pk", None):
        notificar(
            [medio.usuario], Notificacion.Tipo.OPERACION_FALLIDA, "Cobro rechazado en caja",
            f"No se pudo cobrar con {describir_medio(medio)} una operación de {divisa} en ventanilla "
            f"a nombre de {cliente.nombre}. Motivo: {motivo}",
            datos, categoria=del_duenio,
        )


# --- Cotizaciones --------------------------------------------------------------

def cotizacion_cambiada(historial):
    """Avisa a los usuarios activos que siguen esa divisa, menos a quien hizo el cambio."""
    moneda = historial.moneda.codigo
    partes = []
    if historial.precio_compra_anterior != historial.precio_compra_nuevo:
        partes.append(f"compra {formatear_numero(historial.precio_compra_anterior)} → {formatear_numero(historial.precio_compra_nuevo)}")
    if historial.precio_venta_anterior != historial.precio_venta_nuevo:
        partes.append(f"venta {formatear_numero(historial.precio_venta_anterior)} → {formatear_numero(historial.precio_venta_nuevo)}")
    if not partes:
        return
    usuarios = get_user_model().objects.filter(is_active=True)
    if historial.administrador_id:
        usuarios = usuarios.exclude(pk=historial.administrador_id)
    notificar(
        usuarios, Notificacion.Tipo.COTIZACION, f"Cambió la cotización de {moneda}",
        f"Nueva cotización de {historial.moneda.nombre} ({moneda}): {', '.join(partes)} PYG.",
        {"moneda": moneda,
         "precioCompra": float(historial.precio_compra_nuevo), "precioVenta": float(historial.precio_venta_nuevo)},
        categoria=Categoria.COTIZACION, moneda=moneda,
    )
