import json
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from django.db import transaction
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST
from django.utils import timezone

from clientes.models import Cliente
from cuentas.decorators import rol_requerido
from cotizaciones.models import Cotizacion
from medios_pago.models import MedioPago, TipoMedioPago
from monedas.models import Denominacion, Moneda
from pagos import servicio as stripe_servicio
from pagos.servicio import PagoRechazado

from .models import (
    AperturaCaja,
    CierreCaja,
    CompraCaja,
    DetalleAperturaDenominacion,
    VentaCaja,
)


def _json(request):
    try:
        return json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return None


def _cajero_id(request):
    return (
        request.session.get("keycloak_claims", {}).get("sub")
        or str(request.user.pk)
    )


def _numero(value):
    return float(value)


def _totales(detalles):
    return {
        codigo: _numero(total)
        for codigo, total in detalles.items()
    }


def _cantidad_entera(valor):
    if isinstance(valor, bool):
        raise ValueError("La cantidad de unidades debe ser un entero positivo.")
    cantidad = int(valor)
    if str(valor).strip() != str(cantidad):
        raise ValueError("La cantidad de unidades debe ser un entero positivo.")
    return cantidad


def _hoy():
    return timezone.localdate()


def _apertura_hoy(request, activa=True):
    filtros = {
        "cajero_id": str(_cajero_id(request)),
        "fecha_hora_apertura__date": _hoy(),
    }
    if activa:
        filtros["estado"] = AperturaCaja.Estado.ACTIVA
    return AperturaCaja.objects.filter(**filtros).order_by("-fecha_hora_apertura").first()


def _medio_efectivo():
    return MedioPago.objects.filter(alias__iexact="Efectivo", activo=True).order_by("id").first()


def _entrada_operacion(request, tipo):
    datos = _json(request)
    if datos is None:
        return None, JsonResponse({"error": "El cuerpo debe ser JSON válido."}, status=400)
    apertura_obj = _apertura_hoy(request)
    if apertura_obj is None:
        return None, JsonResponse({"error": "Debe realizar el arqueo de apertura del día."}, status=400)
    cliente = Cliente.objects.filter(pk=datos.get("cliente_id") or datos.get("clienteId")).select_related("segmento").first()
    moneda = Moneda.objects.filter(
        codigo=datos.get("moneda") or "", activo=True
    ).first()
    if cliente is None or moneda is None:
        return None, JsonResponse({"error": "El cliente y la moneda son obligatorios."}, status=400)
    if moneda.es_local:
        return None, JsonResponse({"error": f"{moneda.codigo} es la moneda local: no se compra ni se vende."}, status=400)
    try:
        monto = Decimal(str(datos.get("monto_divisa", datos.get("monto"))))
    except (InvalidOperation, TypeError, ValueError):
        return None, JsonResponse({"error": "El monto debe ser numérico."}, status=400)
    if monto <= 0:
        return None, JsonResponse({"error": "El monto debe ser mayor que cero."}, status=400)
    cotizacion = Cotizacion.objects.filter(moneda=moneda, activa=True).first()
    if cotizacion is None:
        return None, JsonResponse({"error": "La moneda no tiene una cotización vigente."}, status=400)
    tipo_pago_nombre = None
    forma_pago = EFECTIVO
    medio_id = datos.get("medio_pago_id", datos.get("medioPagoId"))
    medio = MedioPago.objects.filter(pk=medio_id, activo=True).first() if medio_id else None
    if medio_id and medio is None:
        return None, JsonResponse({"error": "Debe seleccionar un medio de pago activo."}, status=400)
    if medio and medio.stripe_payment_method_id:
        # Tarjeta de Stripe: tiene que ser de un usuario asociado al cliente.
        if not cliente.usuarios.filter(pk=medio.usuario_id).exists():
            return None, JsonResponse({"error": "Esa tarjeta no pertenece a un usuario del cliente."}, status=400)
        tipo_pago_nombre = _nombre_tarjeta(medio)
        forma_pago = TARJETA_STRIPE
    elif tipo == "compra":
        medio = _medio_efectivo()  # opcional: se usa si existe, pero no bloquea
    else:
        tipo_pago_clave = datos.get("tipo_pago", datos.get("tipoPago"))
        if medio:
            tipo_pago_nombre = medio.alias
            forma_pago = medio.tipo or medio.alias
        elif tipo_pago_clave == EFECTIVO:
            medio = _medio_efectivo()
            tipo_pago_nombre = "Efectivo"
        elif tipo_pago_clave:
            tipo_obj = TipoMedioPago.objects.filter(clave=tipo_pago_clave, activo=True).first()
            if tipo_obj is None:
                return None, JsonResponse({"error": "Debe seleccionar un medio de pago activo."}, status=400)
            tipo_pago_nombre = tipo_obj.nombre
            forma_pago = tipo_obj.clave
            # medio queda None: VentaCaja.medio_pago es nullable
        else:
            return None, JsonResponse({"error": "Debe seleccionar un medio de pago."}, status=400)
    porcentaje = Decimal("0")
    if cliente.segmento_id is not None:
        porcentaje = Decimal(cliente.segmento.porcentaje_comision)
    base = Decimal(cotizacion.precio_compra if tipo == "compra" else cotizacion.precio_venta)
    final = base * (Decimal("1") + porcentaje / 100) if tipo == "compra" else base * (Decimal("1") - porcentaje / 100)
    final = final.quantize(Decimal("0.0001"), ROUND_HALF_UP)
    total = (monto * final).quantize(Decimal("1"), ROUND_HALF_UP)
    calculo = {
        "tasa_base": base,
        "tasa_aplicada": final,
        "tasa_preferencial": porcentaje,
        "total_guaranies": total,
        "tipo_pago_nombre": tipo_pago_nombre,
        "forma_pago": forma_pago,
    }
    return (datos, apertura_obj, cliente, moneda, cotizacion, monto, calculo, medio), None


EFECTIVO = "EFECTIVO"
TARJETA_STRIPE = "TARJETA_STRIPE"


def _movimientos_del_cajon(apertura_obj):
    """Lo que entró y salió del cajón por moneda, para el arqueo del cierre.

    - **Compra de caja** (la casa compra divisa): entra la divisa, salvo que se
      haya cobrado con tarjeta (entró por Stripe); salen los guaraníes que se
      le pagan al cliente.
    - **Venta de caja** (la casa vende divisa): sale la divisa; entran los
      guaraníes solo si el cliente pagó en efectivo (con tarjeta o
      transferencia no pasan por el cajón).

    Los guaraníes se anotan en la moneda local; si no está cargada, no se
    siguen (como antes de que existiera).

    Returns:
        dict: ``{codigo: {"entradas", "salidas", "cantidadEntradas", "cantidadSalidas"}}``.
    """
    local = Moneda.local()
    movimientos = {}

    def anotar(codigo, campo, monto):
        item = movimientos.setdefault(codigo, {
            "entradas": Decimal("0"), "salidas": Decimal("0"),
            "cantidadEntradas": 0, "cantidadSalidas": 0,
        })
        item[campo] += Decimal(monto)
        item["cantidad" + campo.capitalize()] += 1

    for compra in CompraCaja.objects.filter(apertura=apertura_obj).select_related("moneda"):
        if not compra.stripe_payment_intent_id:
            anotar(compra.moneda.codigo, "entradas", compra.monto_divisa)
        if local:
            anotar(local.codigo, "salidas", compra.monto_local_total)
    for venta in VentaCaja.objects.filter(apertura=apertura_obj).select_related("moneda"):
        anotar(venta.moneda.codigo, "salidas", venta.monto_divisa)
        if local and venta.forma_pago == EFECTIVO:
            anotar(local.codigo, "entradas", venta.monto_local_total)
    return movimientos


def _compras_con_tarjeta(apertura_obj):
    """Compras de la apertura cobradas con tarjeta, por moneda: ``{codigo: {cantidad, monto}}``."""
    resultado = {}
    compras = CompraCaja.objects.filter(apertura=apertura_obj, stripe_payment_intent_id__isnull=False)
    for compra in compras.select_related("moneda"):
        item = resultado.setdefault(compra.moneda.codigo, {"cantidad": 0, "monto": Decimal("0")})
        item["cantidad"] += 1
        item["monto"] += compra.monto_divisa
    return resultado


def _valor_en_moneda_local(codigo, monto):
    """``monto`` de la moneda ``codigo`` en guaraníes (precio de compra vigente)."""
    moneda = Moneda.objects.filter(codigo=codigo).first()
    if moneda is None:
        return None
    if moneda.es_local:
        return monto
    cotizacion = Cotizacion.objects.filter(moneda=moneda, activa=True).order_by("-fecha").first()
    if cotizacion is None:
        return None
    return (monto * cotizacion.precio_compra).quantize(Decimal("1"), ROUND_HALF_UP)


def _nombre_tarjeta(medio):
    return f"{medio.alias} ({medio.banco_o_proveedor} •••• {medio.numero_cuenta_o_tarjeta})"


def _cobrar_si_es_tarjeta(datos, tipo, cliente, moneda, monto, calculo, medio):
    """Cobra con Stripe si el medio es una tarjeta.

    En la venta de caja la casa vende divisa: el cliente paga el total en
    guaraníes. En la compra de caja la casa compra divisa: se cobra el monto de
    divisa que entrega el cliente, en esa moneda.

    La operación se registra solo con el cobro aprobado. Si el banco pide 3D
    Secure se responde 202 con el ``client_secret``; el navegador completa la
    verificación y vuelve a mandar la operación con ``payment_intent_id``.

    Returns:
        tuple: ``(payment_intent_id o None, respuesta o None)``. Si hay
        respuesta, la vista la devuelve tal cual (202 o error).
    """
    if not (medio and medio.stripe_payment_method_id):
        return None, None
    if tipo == "venta":
        importe, codigo = calculo["total_guaranies"], "PYG"
    else:
        importe, codigo = monto, moneda.codigo
    cobro_id = datos.get("payment_intent_id", datos.get("paymentIntentId"))
    try:
        if cobro_id:
            if CompraCaja.objects.filter(stripe_payment_intent_id=cobro_id).exists() or \
                    VentaCaja.objects.filter(stripe_payment_intent_id=cobro_id).exists():
                return None, JsonResponse({"error": "Ese pago ya se usó en otra operación."}, status=400)
            cobro = stripe_servicio.verificar_cobro(cobro_id, importe, codigo)
        else:
            cobro = stripe_servicio.cobrar(
                medio, importe, codigo,
                descripcion=f"Global Exchange - Caja: {tipo} de {monto} {moneda.codigo}",
                metadata={"cliente_id": cliente.pk, "operacion": f"caja_{tipo}"},
            )
    except PagoRechazado as error:
        return None, JsonResponse({"error": str(error)}, status=400)
    if cobro.estado == "requiere_accion":
        return None, JsonResponse({
            "pagoPendiente": {"clientSecret": cobro.client_secret, "paymentIntentId": cobro.id},
        }, status=202)
    return cobro.id, None


def _operacion_dict(obj, calculo):
    return {
        "id": obj.id,
        "aperturaId": obj.apertura_id,
        "cliente": {"id": obj.cliente_id, "nombre": obj.cliente.nombre},
        "moneda": obj.moneda.codigo,
        "montoDivisa": float(obj.monto_divisa),
        "cotizacionAplicada": float(obj.cotizacion_aplicada),
        "cotizacionBase": float(obj.cotizacion_base or obj.cotizacion_aplicada),
        "tasaPreferencialAplicada": float(obj.tasa_preferencial_aplicada),
        "cotizacionFinal": float(obj.cotizacion_final or obj.cotizacion_aplicada),
        "montoLocalTotal": float(obj.monto_local_total),
        "tasaAplicada": float(calculo["tasa_aplicada"]),
        "tipoPagoNombre": calculo.get("tipo_pago_nombre"),
        "pagoConTarjeta": bool(obj.stripe_payment_intent_id),
    }


@require_GET
@login_required
@rol_requerido("cajero")
def denominaciones_por_moneda(request):
    monedas = Moneda.objects.filter(activo=True).prefetch_related("denominaciones").order_by("codigo")
    return JsonResponse([
        {
            "id": moneda.id,
            "codigo": moneda.codigo,
            "nombre": moneda.nombre,
            "simbolo": moneda.simbolo,
            # La moneda local se cuenta en la apertura y el cierre, pero no se
            # compra ni se vende.
            "esLocal": moneda.es_local,
            "tieneDenominaciones": moneda.denominaciones.exists(),
            "denominaciones": [
                {"id": d.id, "valor": _numero(d.valor), "codigo": moneda.codigo}
                for d in moneda.denominaciones.all().order_by("valor")
            ],
        }
        for moneda in monedas
    ], safe=False)


@require_GET
@login_required
@rol_requerido("cajero")
def estado_diario(request):
    apertura_obj = _apertura_hoy(request, activa=False)
    # Máquina de estados del cajero:
    #   ESPERANDO_ARQUEO → no hay apertura hoy
    #   EN_SERVICIO      → apertura activa (no cerrada)
    #   CAJA_CERRADA     → apertura cerrada (cierre ya registrado)
    if apertura_obj is None:
        estado_caja = "ESPERANDO_ARQUEO"
    elif apertura_obj.estado == AperturaCaja.Estado.ACTIVA:
        estado_caja = "EN_SERVICIO"
    else:
        estado_caja = "CAJA_CERRADA"
    hora = (
        timezone.localtime(apertura_obj.fecha_hora_apertura).strftime("%H:%M")
        if apertura_obj else None
    )
    return JsonResponse({
        # Campos legacy (compatibilidad hacia atrás)
        "aperturada": apertura_obj is not None,
        "activa": bool(apertura_obj and apertura_obj.estado == AperturaCaja.Estado.ACTIVA),
        "horaApertura": hora,
        "hora_apertura": hora,
        # Máquina de estados explícita
        "estadoCaja": estado_caja,
    })


@require_POST
@login_required
@rol_requerido("cajero")
def apertura(request):
    datos = _json(request)
    if datos is None:
        return JsonResponse({"error": "El cuerpo debe ser JSON válido."}, status=400)
    entradas = datos.get("denominaciones", [])
    if not entradas:
        return JsonResponse({"error": "Debe ingresar al menos una denominación."}, status=400)
    cajero_id = _cajero_id(request)
    if not cajero_id:
        return JsonResponse({"error": "El token no contiene el identificador del cajero."}, status=403)
    if AperturaCaja.objects.filter(
        cajero_id=str(cajero_id), fecha_hora_apertura__date=_hoy()
    ).exists():
        return JsonResponse({"error": "La apertura de caja ya fue realizada hoy."}, status=400)

    try:
        with transaction.atomic():
            detalles = []
            totales = {}
            ids = [item.get("denominacion_id") for item in entradas]
            denominaciones = {
                d.id: d for d in Denominacion.objects.select_related("moneda").filter(id__in=ids)
            }
            if len(denominaciones) != len(set(ids)):
                raise ValueError("Una denominación indicada no existe.")
            for item in entradas:
                denominacion = denominaciones.get(item.get("denominacion_id"))
                cantidad = _cantidad_entera(item.get("cantidad_unidades", 0))
                if cantidad <= 0:
                    raise ValueError("La cantidad de unidades debe ser un entero positivo.")
                subtotal = denominacion.valor * cantidad
                detalles.append((denominacion, cantidad, subtotal))
                totales[denominacion.moneda.codigo] = (
                    totales.get(denominacion.moneda.codigo, Decimal("0")) + subtotal
                )
            apertura_obj = AperturaCaja.objects.create(
                cajero_id=str(cajero_id), usuario=request.user, totales_consolidado=_totales(totales)
            )
            DetalleAperturaDenominacion.objects.bulk_create([
                DetalleAperturaDenominacion(
                    apertura=apertura_obj,
                    denominacion=denominacion,
                    cantidad_unidades=cantidad,
                    subtotal=subtotal,
                )
                for denominacion, cantidad, subtotal in detalles
            ])
    except (ValueError, TypeError, InvalidOperation) as error:
        return JsonResponse({"error": str(error)}, status=400)

    return JsonResponse({
        "id": apertura_obj.id,
        "cajeroId": apertura_obj.cajero_id,
        "estado": apertura_obj.estado,
        "totalesConsolidado": apertura_obj.totales_consolidado,
    }, status=201)


@require_POST
@login_required
@rol_requerido("cajero")
def compra(request):
    entrada, error = _entrada_operacion(request, "compra")
    if error:
        return error
    datos, apertura_obj, cliente, moneda, cotizacion, monto, calculo, medio = entrada
    cobro_id, respuesta = _cobrar_si_es_tarjeta(datos, "compra", cliente, moneda, monto, calculo, medio)
    if respuesta:
        return respuesta
    obj = CompraCaja.objects.create(
        apertura=apertura_obj,
        cajero_id=str(_cajero_id(request)),
        cliente=cliente,
        moneda=moneda,
        monto_divisa=monto,
        cotizacion_aplicada=calculo["tasa_aplicada"],
        monto_local_total=calculo["total_guaranies"],
        medio_pago=medio,
        cotizacion_base=calculo["tasa_base"],
        tasa_preferencial_aplicada=calculo["tasa_preferencial"],
        cotizacion_final=calculo["tasa_aplicada"],
        stripe_payment_intent_id=cobro_id,
        forma_pago=calculo["forma_pago"],
    )
    return JsonResponse(_operacion_dict(obj, calculo), status=201)


@require_POST
@login_required
@rol_requerido("cajero")
def venta(request):
    entrada, error = _entrada_operacion(request, "venta")
    if error:
        return error
    datos, apertura_obj, cliente, moneda, cotizacion, monto, calculo, medio = entrada
    cobro_id, respuesta = _cobrar_si_es_tarjeta(datos, "venta", cliente, moneda, monto, calculo, medio)
    if respuesta:
        return respuesta
    obj = VentaCaja.objects.create(
        apertura=apertura_obj,
        cajero_id=str(_cajero_id(request)),
        cliente=cliente,
        moneda=moneda,
        monto_divisa=monto,
        cotizacion_aplicada=calculo["tasa_aplicada"],
        monto_local_total=calculo["total_guaranies"],
        medio_pago=medio,
        cotizacion_base=calculo["tasa_base"],
        tasa_preferencial_aplicada=calculo["tasa_preferencial"],
        cotizacion_final=calculo["tasa_aplicada"],
        stripe_payment_intent_id=cobro_id,
        forma_pago=calculo["forma_pago"],
    )
    return JsonResponse(_operacion_dict(obj, calculo), status=201)


@require_GET
@login_required
@rol_requerido("cajero")
def resumen_cierre(request):
    apertura_obj = _apertura_hoy(request)
    if apertura_obj is None:
        return JsonResponse({"error": "Arqueo aún no realizado."}, status=400)
    movimientos = _movimientos_del_cajon(apertura_obj)
    con_tarjeta = _compras_con_tarjeta(apertura_obj)
    total_local = Decimal("0")
    resumen = []
    for codigo in sorted(set(apertura_obj.totales_consolidado) | set(movimientos)):
        inicial = Decimal(str(apertura_obj.totales_consolidado.get(codigo, 0)))
        mov = movimientos.get(codigo, {})
        entradas = mov.get("entradas", Decimal("0"))
        salidas = mov.get("salidas", Decimal("0"))
        saldo = inicial + entradas - salidas
        valor = _valor_en_moneda_local(codigo, saldo)
        if valor is not None:
            total_local += valor
        tarjeta = con_tarjeta.get(codigo, {"cantidad": 0, "monto": Decimal("0")})
        resumen.append({
            "moneda": codigo,
            "saldoInicial": float(inicial),
            # "compras" y "ventas" son lo que entra y sale del cajón (para el
            # guaraní, las entradas vienen de las ventas de divisa y viceversa).
            "compras": float(entradas),
            "ventas": float(salidas),
            "cantidadCompras": mov.get("cantidadEntradas", 0),
            "cantidadVentas": mov.get("cantidadSalidas", 0),
            "saldoTeorico": float(saldo),
            # Compras cobradas con tarjeta: la divisa llegó por Stripe, no al
            # cajón. Se informan aparte para que la operación no "desaparezca".
            "comprasConTarjeta": {"cantidad": tarjeta["cantidad"], "monto": float(tarjeta["monto"])},
            # El saldo teórico en guaraníes, al precio de compra vigente (lo
            # que la casa pagaría por esa divisa). None si no tiene cotización.
            "valorEnLocal": float(valor) if valor is not None else None,
        })
    local = Moneda.local()
    return JsonResponse({
        "aperturaId": apertura_obj.id,
        "resumen": resumen,
        "monedaLocal": local.codigo if local else None,
        "totalEnLocal": float(total_local),
    })


@require_POST
@login_required
@rol_requerido("cajero")
def cierre(request):
    datos = _json(request)
    if datos is None:
        return JsonResponse({"error": "El cuerpo debe ser JSON válido."}, status=400)
    cajero_id = _cajero_id(request)
    apertura_obj = _apertura_hoy(request)
    if apertura_obj is None:
        return JsonResponse({"error": "No hay una apertura activa para este cajero."}, status=400)
    if CierreCaja.objects.filter(apertura=apertura_obj).exists():
        return JsonResponse({"error": "La apertura ya tiene un cierre registrado."}, status=400)

    reales = datos.get("totales_reales", {})
    esperados = {codigo: Decimal(str(total)) for codigo, total in apertura_obj.totales_consolidado.items()}
    for codigo, mov in _movimientos_del_cajon(apertura_obj).items():
        esperados[codigo] = esperados.get(codigo, Decimal("0")) + mov["entradas"] - mov["salidas"]
    try:
        reales_decimal = {codigo: Decimal(str(total)) for codigo, total in reales.items()}
        diferencia = {
            codigo: _numero(reales_decimal.get(codigo, Decimal("0")) - esperado)
            for codigo, esperado in esperados.items()
        }
        for codigo, total in reales_decimal.items():
            if codigo not in diferencia:
                diferencia[codigo] = _numero(total)
    except (InvalidOperation, TypeError, ValueError):
        return JsonResponse({"error": "Los totales reales deben ser números válidos."}, status=400)
    esperados_json = _totales(esperados)
    with transaction.atomic():
        cierre_obj = CierreCaja.objects.create(
            apertura=apertura_obj,
            cajero_id=str(cajero_id),
            totales_esperados=esperados_json,
            totales_reales=reales,
            diferencia=diferencia,
        )
        apertura_obj.estado = AperturaCaja.Estado.CERRADA
        apertura_obj.save(update_fields=["estado"])
    return JsonResponse({
        "id": cierre_obj.id,
        "aperturaId": apertura_obj.id,
        "totalesEsperados": esperados_json,
        "totalesReales": reales,
        "diferencia": diferencia,
    }, status=201)


@require_GET
@login_required
@rol_requerido("cajero")
def tarjetas_del_cliente(request, pk):
    """Tarjetas de Stripe con las que se le puede cobrar al cliente en caja:
    las de los usuarios asociados al cliente (las cargan ellos en Medios de Pago)."""
    cliente = Cliente.objects.filter(pk=pk).first()
    if cliente is None:
        return JsonResponse({"error": "No existe ese cliente."}, status=404)
    tarjetas = MedioPago.objects.filter(
        usuario__in=cliente.usuarios.all(), activo=True,
    ).exclude(stripe_payment_method_id="").select_related("usuario")
    return JsonResponse([
        {
            "id": medio.id,
            "nombre": _nombre_tarjeta(medio),
            "titular": medio.usuario.get_full_name() or medio.usuario.get_username(),
            "vencimiento": medio.tarjeta_vencimiento,
        }
        for medio in tarjetas
    ], safe=False)


# Roles que ven el historial de todas las cajas; el cajero ve solo las suyas.
VEN_TODAS_LAS_CAJAS = ("administrador", "analista_cambiario")


def _operacion_historial(obj, tipo):
    return {
        "id": obj.id,
        "tipo": tipo,
        "fechaHora": obj.fecha_hora.isoformat(),
        "cliente": {"id": obj.cliente_id, "nombre": obj.cliente.nombre},
        "moneda": obj.moneda.codigo,
        "montoDivisa": float(obj.monto_divisa),
        "cotizacion": float(obj.cotizacion_final or obj.cotizacion_aplicada),
        "totalGuaranies": float(obj.monto_local_total),
        "formaPago": obj.forma_pago or None,
        "medioPago": _nombre_tarjeta(obj.medio_pago) if obj.medio_pago and obj.medio_pago.stripe_payment_method_id
                     else (obj.medio_pago.alias if obj.medio_pago else None),
        "pagoConTarjeta": bool(obj.stripe_payment_intent_id),
    }


@require_GET
@login_required
@rol_requerido("cajero", *VEN_TODAS_LAS_CAJAS)
def historial(request):
    """Historial de las cajas: cada apertura con sus compras y ventas.

    El cajero ve solo las cajas que abrió él; administrador y analista, todas.
    Filtros opcionales por la URL: ``desde`` y ``hasta`` (``AAAA-MM-DD``).
    Devuelve las últimas 50 aperturas, la más reciente primero.
    """
    aperturas = AperturaCaja.objects.select_related("usuario", "cierre").order_by("-fecha_hora_apertura")
    if not request.user.groups.filter(name__in=VEN_TODAS_LAS_CAJAS).exists():
        aperturas = aperturas.filter(cajero_id=str(_cajero_id(request)))
    if request.GET.get("desde"):
        aperturas = aperturas.filter(fecha_hora_apertura__date__gte=request.GET["desde"])
    if request.GET.get("hasta"):
        aperturas = aperturas.filter(fecha_hora_apertura__date__lte=request.GET["hasta"])

    resultado = []
    for apertura_obj in aperturas[:50]:
        relacionados = ("cliente", "moneda", "medio_pago")
        operaciones = (
            [_operacion_historial(o, "COMPRA") for o in apertura_obj.compras.select_related(*relacionados)]
            + [_operacion_historial(o, "VENTA") for o in apertura_obj.ventas.select_related(*relacionados)]
        )
        operaciones.sort(key=lambda o: o["fechaHora"], reverse=True)
        cierre_obj = getattr(apertura_obj, "cierre", None)
        usuario = apertura_obj.usuario
        resultado.append({
            "id": apertura_obj.id,
            "cajero": (usuario.get_full_name() or usuario.get_username()) if usuario else None,
            "fechaHoraApertura": apertura_obj.fecha_hora_apertura.isoformat(),
            "estado": apertura_obj.estado,
            "fechaHoraCierre": cierre_obj.fecha_hora_cierre.isoformat() if cierre_obj else None,
            "saldoInicial": apertura_obj.totales_consolidado,
            "diferenciaCierre": cierre_obj.diferencia if cierre_obj else None,
            "operaciones": operaciones,
        })
    return JsonResponse({"aperturas": resultado})
