"""API JSON de métodos de pago con CRUD por usuario y control administrativo."""
import json

from django.db import transaction
from django.db.models import ProtectedError

from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_http_methods

from cuentas.decorators import rol_requerido
from pagos import servicio as stripe_servicio
from pagos.servicio import PagoRechazado

from .models import (
    BilleteraDigital,
    MedioPago,
    TarjetaCredito,
    TipoMedioPago,
    TransferenciaBancaria,
)

# Las tarjetas se cargan solo con Stripe Elements (ver tarjetas_registrar):
# el número y el CVV no pasan por este backend.
TARJETAS = ("TARJETA_CREDITO", "TARJETA_DEBITO")

TIPOS = {
    "TARJETA_CREDITO": ("Tarjeta de Crédito", TarjetaCredito),
    "TRANSFERENCIA": ("Transferencia Bancaria", TransferenciaBancaria),
    "BILLETERA_DIGITAL": ("Billetera Digital", BilleteraDigital),
}


def _cuerpo(request):
    try:
        return json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return {}


def _administrador(usuario):
    return usuario.groups.filter(name="administrador").exists()


def _tipos_activos():
    return TipoMedioPago.objects.filter(activo=True).values_list("clave", flat=True)


def _bool_value(value):
    return value if isinstance(value, bool) else str(value).lower() == "true"


def _visibles_para(usuario):
    # El administrador ve también los inactivos para poder reactivarlos; el
    # cajero solo los activos, que son los que puede usar en la caja.
    if _administrador(usuario):
        return MedioPago.objects.all()
    if usuario.groups.filter(name="cajero").exists():
        return MedioPago.objects.filter(activo=True)
    return MedioPago.objects.filter(usuario=usuario, tipo__in=_tipos_activos())


def _upsert_child(model, medio, defaults):
    try:
        detalle = model.objects.get(mediopago_ptr_id=medio.pk)
        for campo, valor in defaults.items():
            setattr(detalle, campo, valor)
        detalle.save(update_fields=list(defaults))
    except model.DoesNotExist:
        detalle = model(mediopago_ptr_id=medio.pk, **defaults)
        detalle.save_base(raw=True, force_insert=True)
    return detalle


def _guardar_detalle(medio, datos):
    if medio.tipo == "TRANSFERENCIA":
        _upsert_child(TransferenciaBancaria, medio, {
                "numero_cuenta_origen": datos.get("numeroCuentaOrigen", ""),
                "banco_origen": datos.get("bancoOrigen", ""),
                "titular_origen": datos.get("titularOrigen", ""),
                "numero_cuenta_destino": datos.get("numeroCuentaDestino", ""),
                "banco_destino": datos.get("bancoDestino", ""),
                "titular_destino": datos.get("titularDestino", ""),
        })
    elif medio.tipo == "BILLETERA_DIGITAL":
        _upsert_child(BilleteraDigital, medio, {
                "plataforma": datos.get("plataforma", ""),
                "identificador_cuenta": datos.get("identificadorCuenta", ""),
                "titular": datos.get("titular", ""),
        })


def _a_dict(medio):
    detalle = {}
    if medio.tipo == "TARJETA_CREDITO" and hasattr(medio, "tarjetacredito"):
        item = medio.tarjetacredito
        detalle = {
            "nombreTitular": item.nombre_titular,
            "aliasTarjeta": item.alias_tarjeta,
            "numeroTarjeta": item.numero_tarjeta[-4:].rjust(len(item.numero_tarjeta), "*"),
            "fechaVencimiento": item.fecha_vencimiento,
        }
    elif medio.tipo == "TRANSFERENCIA" and hasattr(medio, "transferenciabancaria"):
        item = medio.transferenciabancaria
        detalle = {
            "numeroCuentaOrigen": item.numero_cuenta_origen,
            "bancoOrigen": item.banco_origen,
            "titularOrigen": item.titular_origen,
            "numeroCuentaDestino": item.numero_cuenta_destino,
            "bancoDestino": item.banco_destino,
            "titularDestino": item.titular_destino,
        }
    elif medio.tipo == "BILLETERA_DIGITAL" and hasattr(medio, "billeteradigital"):
        item = medio.billeteradigital
        detalle = {
            "plataforma": item.plataforma,
            "identificadorCuenta": item.identificador_cuenta,
            "titular": item.titular,
        }
    tarjeta = None
    if medio.stripe_payment_method_id:
        tarjeta = {
            "marca": medio.banco_o_proveedor or "",
            "ultimos4": medio.numero_cuenta_o_tarjeta,
            "vencimiento": medio.tarjeta_vencimiento,
        }
    return {
        "id": medio.id,
        "tipo": medio.tipo,
        "tipoTexto": medio.get_tipo_display() or "Sin tipo",
        "alias": medio.alias,
        "activo": medio.activo,
        "usuario": medio.usuario.get_username(),
        "detalle": detalle,
        # Tarjeta de Stripe: se puede cobrar con ella. None para los demás medios.
        "tarjeta": tarjeta,
    }


@require_http_methods(["GET", "POST"])
@rol_requerido("cliente", "administrador", "cajero")
def medios_lista(request):
    if request.method == "GET":
        tipos = TipoMedioPago.objects.all()
        if not _administrador(request.user):
            tipos = tipos.filter(activo=True)
        medios = _visibles_para(request.user).select_related("usuario")
        return JsonResponse({
            "tipos": [
                {"valor": tipo.clave, "texto": tipo.nombre, "activo": tipo.activo}
                for tipo in tipos
            ],
            "medios": [_a_dict(medio) for medio in medios],
        })

    if not (_administrador(request.user) or request.user.groups.filter(name="cliente").exists()):
        return JsonResponse({"error": "No autorizado."}, status=403)
    datos = _cuerpo(request)
    tipo = datos.get("tipo")
    alias = (datos.get("alias") or "").strip()
    if tipo not in set(_tipos_activos()):
        return JsonResponse({"error": "Debe seleccionar un tipo válido y activo."}, status=400)
    if tipo in TARJETAS:
        return JsonResponse(
            {"error": "Las tarjetas se cargan con el formulario seguro de Stripe."}, status=400
        )
    if not alias:
        return JsonResponse({"error": "El nombre es obligatorio."}, status=400)
    medio = MedioPago.objects.create(
        usuario=request.user,
        tipo=tipo,
        alias=alias,
        activo=True,
    )
    _guardar_detalle(medio, datos)
    return JsonResponse(_a_dict(medio), status=201)


@require_http_methods(["PATCH"])
@rol_requerido("administrador")
def tipo_detalle(request, clave):
    try:
        tipo = TipoMedioPago.objects.get(clave=clave)
    except TipoMedioPago.DoesNotExist:
        return JsonResponse({"error": "No existe esa categoría."}, status=404)
    datos = _cuerpo(request)
    if "activo" not in datos:
        return JsonResponse({"error": "Debe indicar el nuevo estado."}, status=400)
    tipo.activo = _bool_value(datos["activo"])
    tipo.save(update_fields=["activo"])
    return JsonResponse({"valor": tipo.clave, "texto": tipo.nombre, "activo": tipo.activo})


@require_http_methods(["GET", "PATCH", "DELETE"])
@rol_requerido("cliente", "administrador")
def medios_detalle(request, pk):
    try:
        medio = _visibles_para(request.user).get(pk=pk)
    except MedioPago.DoesNotExist:
        return JsonResponse({"error": "No existe ese medio de pago."}, status=404)

    if request.method == "GET":
        return JsonResponse(_a_dict(medio))
    if request.method == "DELETE":
        if medio.stripe_payment_method_id:
            stripe_servicio.desvincular_tarjeta(medio.stripe_payment_method_id)
        try:
            with transaction.atomic():
                medio.delete()
        except ProtectedError:
            # Ya se usó en operaciones de caja: se conserva para el historial,
            # desactivado (y si era tarjeta, ya no se puede cobrar con ella).
            medio.activo = False
            medio.save(update_fields=["activo"])
        return HttpResponse(status=204)

    datos = _cuerpo(request)
    if "alias" in datos:
        medio.alias = (datos["alias"] or "").strip()
    if "tipo" in datos and datos["tipo"] in TIPOS:
        medio.tipo = datos["tipo"]
    if "activo" in datos:
        if not _administrador(request.user):
            return JsonResponse({"error": "Solo un administrador puede cambiar el estado."}, status=403)
        medio.activo = _bool_value(datos["activo"])
    medio.save()
    if any(key in datos for key in (
        "numeroCuentaOrigen", "bancoOrigen", "titularOrigen",
        "numeroCuentaDestino", "bancoDestino", "titularDestino", "plataforma",
        "identificadorCuenta", "titular",
    )):
        _guardar_detalle(medio, datos)
    return JsonResponse(_a_dict(medio))


@require_http_methods(["POST"])
@rol_requerido("cliente", "administrador")
def tarjetas_preparar(request):
    """Primer paso para cargar una tarjeta: el ``client_secret`` de un
    SetupIntent, con el que Stripe Elements guarda la tarjeta en Stripe."""
    try:
        return JsonResponse({"clientSecret": stripe_servicio.preparar_tarjeta(request.user)})
    except PagoRechazado as error:
        return JsonResponse({"error": str(error)}, status=400)


@require_http_methods(["POST"])
@rol_requerido("cliente", "administrador")
def tarjetas_registrar(request):
    """Segundo paso: registra como medio de pago la tarjeta que Stripe guardó.

    Espera ``{"setupIntentId", "tipo": "TARJETA_CREDITO"|"TARJETA_DEBITO",
    "alias"}``. Los datos de la tarjeta (marca, últimos 4, vencimiento) se
    leen de Stripe, no del navegador.
    """
    datos = _cuerpo(request)
    tipo = datos.get("tipo")
    alias = (datos.get("alias") or "").strip()
    if tipo not in TARJETAS or tipo not in set(_tipos_activos()):
        return JsonResponse({"error": "Debe seleccionar un tipo de tarjeta válido y activo."}, status=400)
    if not alias:
        return JsonResponse({"error": "El nombre es obligatorio."}, status=400)
    try:
        tarjeta = stripe_servicio.tarjeta_registrada(request.user, datos.get("setupIntentId") or "")
    except PagoRechazado as error:
        return JsonResponse({"error": str(error)}, status=400)
    medio = MedioPago.objects.create(
        usuario=request.user,
        tipo=tipo,
        alias=alias,
        activo=True,
        stripe_payment_method_id=tarjeta["payment_method_id"],
        banco_o_proveedor=tarjeta["marca"],
        numero_cuenta_o_tarjeta=tarjeta["ultimos4"],
        tarjeta_vencimiento=tarjeta["vencimiento"],
    )
    return JsonResponse(_a_dict(medio), status=201)
