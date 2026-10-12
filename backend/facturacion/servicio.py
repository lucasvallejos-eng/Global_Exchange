"""Integración con Factura Segura (facturación electrónica de la DNIT).

Todo lo que habla con Factura Segura pasa por acá, así el resto del sistema no
conoce su API y los tests pueden reemplazar ``_pedir``. La especificación es
"API de Factura Segura para ESI v01": un único recurso (``/misife00/v1/esi``)
al que se le manda ``{"operation": ..., "params": ...}`` con el token en la
cabecera ``Authentication-Token``.

**Los números de factura son pocos** (la cátedra asignó un rango de 12), así
que por defecto **no se emite nada**. Hay tres modos, según la configuración
(``backend/.env.facturasegura``):

- **Sin token:** la factura queda ``SIMULADA`` y no se llama a nadie.
- **Con token y ``FACTURA_SEGURA_EMITIR`` apagado:** se valida el documento
  con ``calcular_de``, que no genera nada ni gasta números, y la factura
  queda ``SIMULADA``.
- **Con token y ``FACTURA_SEGURA_EMITIR`` prendido:** se reserva un número
  del rango y se emite de verdad con ``generar_de``.

Qué se factura (supuestos a confirmar con la cátedra):

- **El cliente compra divisa** (la casa vende; ``iTipTra`` 5): un ítem exento
  de IVA por el monto en guaraníes y, si hay comisión, un segundo ítem gravado
  al 10 %. El total de la factura es lo que pagó el cliente.
- **El cliente vende divisa** (la casa compra; ``iTipTra`` 6): un ítem exento
  por el monto en guaraníes, con la comisión como descuento. El total es lo
  que recibió el cliente.

El receptor es siempre el **cliente** de la operación (RN02), nunca el usuario
que la cargó.
"""
import json
import urllib.error
import urllib.request
from decimal import Decimal

from django.conf import settings
from django.db import transaction as transaccion_bd
from django.utils import timezone

from clientes.models import Cliente
from operaciones.models import Transaccion

from .models import Factura

RECURSO = "/misife00/v1/esi"
ESPERA_SEGUNDOS = 20

# iTiPago del Manual Técnico del SIFEN, según el tipo de medio de pago.
EFECTIVO = "1"
TIPOS_DE_PAGO = {
    "TARJETA_CREDITO": "3",
    "TARJETA_DEBITO": "4",
    "CUENTA_BANCARIA": "5",
    "TRANSFERENCIA": "5",
    "BILLETERA_DIGITAL": "7",
}
TARJETAS = ("3", "4")
# iDenTarj: denominación de la tarjeta. 99 es "otra".
MARCAS_DE_TARJETA = {"visa": "1", "mastercard": "2", "american": "3", "amex": "3",
                     "maestro": "4", "panal": "5", "cabal": "6"}


class FacturaInvalida(Exception):
    """La factura no se puede armar con los datos que hay (falta el RUC del
    cliente, el emisor no está configurado, se acabaron los números...). No se
    llegó a llamar a Factura Segura. El mensaje se le muestra al usuario."""


class ErrorFacturaSegura(Exception):
    """Factura Segura respondió que no. El mensaje se le muestra al usuario."""


class SinConfirmar(ErrorFacturaSegura):
    """No hubo respuesta (se cortó la conexión o se venció la espera): el
    pedido pudo haberse procesado igual."""


def habilitado():
    """Si hay token: se puede llamar a Factura Segura."""
    return bool(settings.FACTURA_SEGURA_TOKEN)


def emite():
    """Si las facturas se emiten de verdad (gastan un número del rango)."""
    return habilitado() and settings.FACTURA_SEGURA_EMITIR


# --- Comunicación con Factura Segura ------------------------------------------

def _pedir(operation, params):
    """Manda una operación al recurso ESI y devuelve su lista ``results``.

    Raises:
        ErrorFacturaSegura: si responde con ``code`` negativo.
        SinConfirmar: si no se pudo saber qué respondió.
    """
    pedido = urllib.request.Request(
        settings.FACTURA_SEGURA_URL.rstrip("/") + RECURSO,
        data=json.dumps({"operation": operation, "params": params}).encode("utf-8"),
        headers={
            "accept": "application/json",
            "Content-Type": "application/json",
            "Authentication-Token": settings.FACTURA_SEGURA_TOKEN,
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(pedido, timeout=ESPERA_SEGUNDOS) as respuesta:
            cuerpo = json.load(respuesta)
    except urllib.error.HTTPError as error:
        if error.code in (401, 403):
            raise ErrorFacturaSegura(
                "Factura Segura no aceptó el token (o el usuario ESI no está autorizado)."
            ) from error
        if error.code < 500:
            raise ErrorFacturaSegura(f"Factura Segura rechazó el pedido (HTTP {error.code}).") from error
        raise SinConfirmar(f"Factura Segura falló (HTTP {error.code}).") from error
    except (OSError, ValueError) as error:  # sin conexión, espera vencida o respuesta ilegible
        raise SinConfirmar("No hubo respuesta de Factura Segura.") from error

    if cuerpo.get("code", -1) < 0:
        extra = "; ".join(
            str(valor) for resultado in cuerpo.get("results") or [] for valor in resultado.values()
        )
        descripcion = cuerpo.get("description") or "Error sin descripción"
        raise ErrorFacturaSegura(f"{descripcion} ({extra})" if extra else descripcion)
    return cuerpo.get("results") or []


def _bajar(operation, factura):
    """Descarga el KuDE o el XML de una factura emitida (``dwn_kude`` / ``dwn_xml``)."""
    ruc = settings.FACTURA_SEGURA_EMISOR["ruc"]
    pedido = urllib.request.Request(
        f"{settings.FACTURA_SEGURA_URL.rstrip('/')}{RECURSO}/{operation}/{ruc}/{factura.cdc}",
        headers={"Authentication-Token": settings.FACTURA_SEGURA_TOKEN},
    )
    try:
        with urllib.request.urlopen(pedido, timeout=ESPERA_SEGUNDOS) as respuesta:
            return respuesta.read()
    except OSError as error:
        raise ErrorFacturaSegura("No se pudo descargar el archivo de Factura Segura.") from error


# --- Armado del documento electrónico -----------------------------------------

def digito_verificador(numero):
    """Dígito verificador de un RUC paraguayo (módulo 11)."""
    total, factor = 0, 2
    for cifra in reversed(str(numero)):
        total += int(cifra) * factor
        factor = factor + 1 if factor < 11 else 2
    resto = total % 11
    return 11 - resto if resto > 1 else 0


def _texto(numero):
    """Un número como lo espera el JSON: texto, sin ceros de más ni exponente."""
    numero = Decimal(numero)
    return format(numero.quantize(Decimal(1)) if numero == numero.to_integral() else numero.normalize(), "f")


def _receptor(cliente):
    """Los campos del receptor: el cliente, con RUC (contribuyente) o cédula."""
    documento = (cliente.ruc or "").strip().replace(".", "")
    if not documento:
        raise FacturaInvalida(
            f"El cliente {cliente.nombre} no tiene RUC ni cédula cargados: "
            "sin eso no se le puede facturar."
        )
    juridica = cliente.tipo == Cliente.Tipo.JURIDICA
    comunes = {
        "cPaisRec": "PRY",
        "dNomRec": cliente.nombre,
        "dEmailRec": cliente.correo,
    }
    if "-" not in documento:
        if not documento.isdigit():
            raise FacturaInvalida(f"La cédula del cliente {cliente.nombre} tiene que ser un número.")
        # No contribuyente: se identifica con la cédula paraguaya (iTipIDRec 1).
        return {**comunes, "iNatRec": "2", "iTiOpe": "2", "iTipIDRec": "1", "dNumIDRec": documento}

    ruc, dv = (parte.strip() for parte in documento.split("-", 1))
    if not ruc.isdigit() or dv != str(digito_verificador(ruc)):
        raise FacturaInvalida(
            f"El RUC del cliente {cliente.nombre} ({documento}) no es válido: "
            "revisá el número y el dígito verificador."
        )
    return {
        **comunes,
        "iNatRec": "1",
        "iTiOpe": "1" if juridica else "2",  # B2B o B2C
        "iTiContRec": "2" if juridica else "1",
        "dRucRec": ruc,
        "dDVRec": dv,
        "iTipIDRec": "0",
        "dNumIDRec": "0",
    }


def _pago(transaccion, total):
    """El pago al contado (``gPaConEIni``), según el medio de pago de la operación."""
    medio = transaccion.medio_pago
    tipo = TIPOS_DE_PAGO.get(medio.tipo, EFECTIVO) if medio else EFECTIVO
    pago = {"iTiPago": tipo, "dMonTiPag": _texto(total), "cMoneTiPag": "PYG", "dTiCamTiPag": "1"}
    if tipo in TARJETAS:
        descripcion = f"{medio.alias} {medio.banco_o_proveedor or ''}".lower()
        pago["iDenTarj"] = next(
            (codigo for marca, codigo in MARCAS_DE_TARJETA.items() if marca in descripcion), "99"
        )
        pago["iForProPa"] = "2"  # pago electrónico (no hay POS)
    return pago


def _item(codigo, descripcion, precio, descuento=0, gravado=False):
    return {
        "dCodInt": codigo,
        "dDesProSer": descripcion,
        "cUniMed": "77",
        "dCantProSer": "1",
        "dPUniProSer": _texto(precio),
        "dDescItem": _texto(descuento),
        "dDescGloItem": "0",
        "dAntPreUniIt": "0",
        "dAntGloPreUniIt": "0",
        # 1 = gravado, 3 = exento.
        "iAfecIVA": "1" if gravado else "3",
        "dPropIVA": "100" if gravado else "0",
        "dTasaIVA": "10" if gravado else "0",
    }


def _items(t):
    """Los ítems de la factura (ver el docstring del módulo).

    Van en guaraníes y con cantidad 1: así el total coincide siempre con lo
    que se cobró, sin decimales que el guaraní no tiene.
    """
    detalle = f"{_texto(t.monto_divisa)} {t.moneda.codigo} a {_texto(t.tasa_aplicada)} Gs."
    if t.tipo == Transaccion.Tipo.COMPRA:
        items = [_item(t.moneda.codigo, f"Venta de divisa: {detalle}", t.monto_guaranies)]
        if t.comision:
            items.append(_item("COMISION", "Comisión por operación de cambio", t.comision, gravado=True))
        return items
    return [_item(t.moneda.codigo, f"Compra de divisa: {detalle}", t.monto_guaranies, descuento=t.comision)]


def armar_de(transaccion, numero):
    """El documento electrónico **resumido** de la operación (JSON de Factura Segura).

    Es lo que recibe ``calcular_de``, que devuelve el documento completo con
    los montos e impuestos calculados según el SIFEN.

    Raises:
        FacturaInvalida: si al cliente le falta el RUC o no es válido.
    """
    emisor = settings.FACTURA_SEGURA_EMISOR
    numeracion = settings.FACTURA_SEGURA_NUMERACION
    venta_de_la_casa = transaccion.tipo == Transaccion.Tipo.COMPRA
    return {
        "iTipEmi": "1",
        "iTiDE": "1",  # factura electrónica
        "dNumTim": numeracion["timbrado"],
        "dFeIniT": numeracion["timbrado_inicio"],
        "dEst": numeracion["establecimiento"],
        "dPunExp": numeracion["punto_expedicion"],
        "dNumDoc": f"{numero:07d}",
        "dFeEmiDE": timezone.localtime().strftime("%Y-%m-%dT%H:%M:%S"),
        "iTipTra": "5" if venta_de_la_casa else "6",  # venta / compra de divisas
        "iTImp": "1",
        "cMoneOpe": "PYG",
        "dCondTiCam": "1",
        "dTiCam": "1",
        "dRucEm": emisor["ruc"],
        "dDVEmi": emisor["dv"],
        "iTipCont": emisor["tipo_contribuyente"],
        "dNomEmi": emisor["nombre"],
        "dDirEmi": emisor["direccion"],
        "dNumCas": emisor["numero_casa"],
        "cDepEmi": emisor["departamento_codigo"],
        "dDesDepEmi": emisor["departamento"],
        "cCiuEmi": emisor["ciudad_codigo"],
        "dDesCiuEmi": emisor["ciudad"],
        "dTelEmi": emisor["telefono"],
        "dEmailE": emisor["email"],
        "gActEco": [{"cActEco": emisor["actividad_codigo"], "dDesActEco": emisor["actividad"]}],
        **_receptor(transaccion.cliente),
        "iIndPres": "2",  # operación electrónica
        "iCondOpe": "1",  # contado
        "gPaConEIni": [_pago(transaccion, transaccion.total_guaranies)],
        "iCondCred": "1",
        "dPlazoCre": "0",
        "gCamItem": _items(transaccion),
        "CDC": "0",
        "dCodSeg": "0",
        "dDVId": "0",
        "dSisFact": "1",
        "dInfAdic": f"Global Exchange - Operación #{transaccion.pk}",
    }


def _validar_configuracion():
    """Antes de llamar a Factura Segura: que estén los datos del emisor y el timbrado."""
    faltan = [
        clave
        for grupo in (settings.FACTURA_SEGURA_EMISOR, settings.FACTURA_SEGURA_NUMERACION)
        for clave, valor in grupo.items()
        if valor in ("", None)
    ]
    if faltan:
        raise FacturaInvalida(
            "Faltan datos del emisor en backend/.env.facturasegura: " + ", ".join(faltan) + "."
        )


# --- Numeración ---------------------------------------------------------------

def numeros_libres():
    """Los números del rango asignado que todavía no usó ninguna factura."""
    numeracion = settings.FACTURA_SEGURA_NUMERACION
    usados = set(Factura.objects.exclude(numero=None).values_list("numero", flat=True))
    return [
        numero
        for numero in range(numeracion["factura_desde"], numeracion["factura_hasta"] + 1)
        if numero not in usados
    ]


def _siguiente_numero():
    libres = numeros_libres()
    if not libres:
        numeracion = settings.FACTURA_SEGURA_NUMERACION
        raise FacturaInvalida(
            "Se acabaron los números de factura asignados "
            f"({numeracion['factura_desde']} a {numeracion['factura_hasta']})."
        )
    return libres[0]


# --- Emisión ------------------------------------------------------------------

def facturar(transaccion):
    """Genera la factura de una operación pagada. Se puede llamar más de una vez.

    Nunca lanza una excepción: la operación ya está pagada y un problema con
    la factura no la puede deshacer. Lo que haya pasado queda en el ``estado``
    y el ``detalle`` de la factura, y se puede reintentar.

    Returns:
        Factura: la factura de la operación, o ``None`` si no está pagada.
    """
    if transaccion.estado != Transaccion.Estado.PAGADA:
        return None
    factura = Factura.objects.filter(transaccion=transaccion).first()
    if factura is None:
        factura = Factura(transaccion=transaccion)
    elif not factura.se_puede_reintentar:
        return factura
    return _emitir(factura)


def reintentar(factura):
    """Vuelve a emitir una factura que falló (por ejemplo, después de cargarle
    el RUC al cliente), o emite una simulada cuando la emisión está prendida.
    Reusa el número que ya tenía reservado, si tenía.

    Raises:
        FacturaInvalida: si la factura no está en un estado que se pueda reintentar.
    """
    if not se_puede_emitir(factura):
        raise FacturaInvalida(
            f"La factura está {factura.get_estado_display().lower()}: no hay nada que reintentar."
        )
    return _emitir(factura)


def se_puede_emitir(factura):
    """Si tiene sentido (re)emitirla: falló, o es simulada y ahora la emisión
    está prendida. Las simuladas no se emiten solas al prender la emisión,
    para que nadie gaste números sin darse cuenta."""
    return factura.se_puede_reintentar or (
        factura.estado == Factura.Estado.SIMULADA and emite()
    )


def _emitir(factura):
    transaccion = factura.transaccion
    factura.receptor_nombre = transaccion.cliente.nombre
    factura.receptor_documento = transaccion.cliente.ruc
    factura.total = transaccion.total_guaranies
    factura.cdc = ""
    try:
        if emite():
            _emitir_de_verdad(factura)
        else:
            _simular(factura)
    except (FacturaInvalida, ErrorFacturaSegura) as error:
        # Un "no" claro libera el número. Si no se sabe qué pasó, se conserva:
        # el reintento manda el mismo número y no gasta otro.
        sin_confirmar = isinstance(error, SinConfirmar)
        if not sin_confirmar:
            factura.numero = None
        factura.estado = Factura.Estado.SIN_CONFIRMAR if sin_confirmar else Factura.Estado.ERROR
        factura.detalle = str(error)[:500]
    factura.save()
    return factura


def _simular(factura):
    """Arma la factura sin emitirla. Con token, la valida con ``calcular_de``."""
    libres = numeros_libres()
    de = armar_de(factura.transaccion, libres[0] if libres else 0)
    factura.numero = None
    factura.estado = Factura.Estado.SIMULADA
    if habilitado():
        _validar_configuracion()
        de = _calcular(de)
        factura.detalle = "Validada por Factura Segura. No se emitió: la emisión está apagada."
    else:
        factura.detalle = "No se emitió: Factura Segura no está configurado."
    factura.de = de


def _emitir_de_verdad(factura):
    _validar_configuracion()
    with transaccion_bd.atomic():
        if factura.numero is None:
            factura.numero = _siguiente_numero()
        factura.estado = Factura.Estado.SIN_CONFIRMAR
        factura.detalle = ""
        factura.save()  # reserva el número antes de salir a la red
    de = _calcular(armar_de(factura.transaccion, factura.numero))
    factura.de = de
    resultados = _pedir("generar_de", {"DE": de})
    factura.cdc = resultados[0]["CDC"]
    factura.estado = Factura.Estado.ENVIADA
    factura.detalle = "Enviada al SIFEN. El resultado se consulta un minuto después."


def _calcular(de):
    """``calcular_de``: completa los montos según el SIFEN. No genera ningún documento."""
    try:
        return _pedir("calcular_de", {"DE": de})[0]["DE"]
    except SinConfirmar as error:
        # Acá no hay nada "sin confirmar": calcular no emite.
        raise ErrorFacturaSegura(str(error)) from error


# --- Estado y descargas -------------------------------------------------------

def actualizar_estado(factura):
    """Le pregunta a Factura Segura cómo quedó la factura en el SIFEN (``get_estado_sifen``).

    Sigue el orden que indica la especificación: primero la cancelación y
    después la aprobación.

    Raises:
        ErrorFacturaSegura: si no se pudo consultar.
    """
    if not factura.emitida:
        return factura
    resultado = _pedir("get_estado_sifen", {
        "CDC": factura.cdc,
        "dRucEm": settings.FACTURA_SEGURA_EMISOR["ruc"],
    })[0]

    def detalle(sufijo):
        partes = (resultado.get(f"desc_{sufijo}"), resultado.get(f"error_{sufijo}"))
        return " ".join(parte for parte in partes if parte)[:500]

    estado = resultado.get("estado_sifen") or ""
    if resultado.get("estado_can") == "Aprobado" or resultado.get("estado_inu") == "Aprobado":
        factura.estado = Factura.Estado.CANCELADA
        factura.detalle = detalle("can") or detalle("inu")
    elif estado.startswith("Aprobado"):
        factura.estado = Factura.Estado.APROBADA
        factura.detalle = detalle("sifen")
    elif estado in ("Rechazado", "Reingresado"):
        factura.estado = Factura.Estado.RECHAZADA
        factura.detalle = detalle("sifen") or estado
    else:
        # SOL.APROBACION, ENVIADO_A_SIFEN o un error de conexión con el SIFEN:
        # todavía no hay resultado.
        factura.estado = Factura.Estado.ENVIADA
        factura.detalle = detalle("sifen") or estado
    factura.save()
    return factura


FORMATOS = {
    "kude": ("dwn_kude", "application/pdf", "pdf"),
    "xml": ("dwn_xml", "application/xml", "xml"),
}


def descargar(factura, formato):
    """El KuDE (PDF) o el XML firmado de una factura emitida.

    Returns:
        tuple: ``(contenido, content_type, nombre_de_archivo)``.

    Raises:
        FacturaInvalida: si la factura no se emitió (no hay nada que descargar).
        ErrorFacturaSegura: si falló la descarga.
    """
    if not factura.emitida:
        raise FacturaInvalida("Esta factura no se emitió: no tiene KuDE ni XML para descargar.")
    operation, content_type, extension = FORMATOS[formato]
    return _bajar(operation, factura), content_type, f"factura-{factura.numero_completo}.{extension}"
