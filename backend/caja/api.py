import json
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from django.db import transaction
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST
from django.utils import timezone

from clientes.models import Cliente
from cotizaciones.models import Cotizacion
from medios_pago.models import MedioPago, TipoMedioPago
from monedas.models import Denominacion, Moneda

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
    if tipo == "compra":
        medio = _medio_efectivo()  # opcional: se usa si existe, pero no bloquea
    else:
        medio_id = datos.get("medio_pago_id", datos.get("medioPagoId"))
        tipo_pago_clave = datos.get("tipo_pago", datos.get("tipoPago"))
        medio = None
        if medio_id:
            medio = MedioPago.objects.filter(pk=medio_id, activo=True).first()
            tipo_pago_nombre = medio.alias if medio else None
        elif tipo_pago_clave:
            tipo_obj = TipoMedioPago.objects.filter(clave=tipo_pago_clave, activo=True).first()
            if tipo_obj is None:
                return None, JsonResponse({"error": "Debe seleccionar un medio de pago activo."}, status=400)
            tipo_pago_nombre = tipo_obj.nombre
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
    }
    return (datos, apertura_obj, cliente, moneda, cotizacion, monto, calculo, medio), None


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
    }


@require_GET
@login_required
def denominaciones_por_moneda(request):
    monedas = Moneda.objects.filter(activo=True).prefetch_related("denominaciones").order_by("codigo")
    return JsonResponse([
        {
            "id": moneda.id,
            "codigo": moneda.codigo,
            "nombre": moneda.nombre,
            "simbolo": moneda.simbolo,
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
                cajero_id=str(cajero_id), totales_consolidado=_totales(totales)
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
def compra(request):
    entrada, error = _entrada_operacion(request, "compra")
    if error:
        return error
    datos, apertura_obj, cliente, moneda, cotizacion, monto, calculo, medio = entrada
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
    )
    return JsonResponse(_operacion_dict(obj, calculo), status=201)


@require_POST
@login_required
def venta(request):
    entrada, error = _entrada_operacion(request, "venta")
    if error:
        return error
    datos, apertura_obj, cliente, moneda, cotizacion, monto, calculo, medio = entrada
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
    )
    return JsonResponse(_operacion_dict(obj, calculo), status=201)


@require_GET
@login_required
def resumen_cierre(request):
    apertura_obj = _apertura_hoy(request)
    if apertura_obj is None:
        return JsonResponse({"error": "Arqueo aún no realizado."}, status=400)
    codigos = set(apertura_obj.totales_consolidado)
    compras = CompraCaja.objects.filter(apertura=apertura_obj).values("moneda__codigo", "monto_divisa")
    ventas = VentaCaja.objects.filter(apertura=apertura_obj).values("moneda__codigo", "monto_divisa")
    acumulado = {
        codigo: {"moneda": codigo, "saldoInicial": float(apertura_obj.totales_consolidado[codigo]), "compras": 0, "ventas": 0}
        for codigo in codigos
    }
    for item in compras:
        acumulado.setdefault(item["moneda__codigo"], {"moneda": item["moneda__codigo"], "saldoInicial": 0, "compras": 0, "ventas": 0})
        acumulado[item["moneda__codigo"]]["compras"] += float(item["monto_divisa"])
    for item in ventas:
        acumulado.setdefault(item["moneda__codigo"], {"moneda": item["moneda__codigo"], "saldoInicial": 0, "compras": 0, "ventas": 0})
        acumulado[item["moneda__codigo"]]["ventas"] += float(item["monto_divisa"])
    for item in acumulado.values():
        item["saldoTeorico"] = item["saldoInicial"] + item["compras"] - item["ventas"]
    return JsonResponse({"aperturaId": apertura_obj.id, "resumen": list(acumulado.values())})


@require_POST
@login_required
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
    for operacion in CompraCaja.objects.filter(apertura=apertura_obj).select_related("moneda"):
        esperados[operacion.moneda.codigo] = esperados.get(operacion.moneda.codigo, Decimal("0")) + operacion.monto_divisa
    for operacion in VentaCaja.objects.filter(apertura=apertura_obj).select_related("moneda"):
        esperados[operacion.moneda.codigo] = esperados.get(operacion.moneda.codigo, Decimal("0")) - operacion.monto_divisa
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
