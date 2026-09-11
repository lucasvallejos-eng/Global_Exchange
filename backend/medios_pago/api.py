"""API JSON de métodos de pago con CRUD por usuario y control administrativo."""
import json
import secrets

from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

from cuentas.decorators import rol_requerido

from .models import (
    BilleteraDigital,
    MedioPago,
    TarjetaCredito,
    TipoMedioPago,
    TransferenciaBancaria,
)

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
    if _administrador(usuario):
        return MedioPago.objects.all()
    return MedioPago.objects.filter(usuario=usuario, tipo__in=_tipos_activos())


def _tokenizar(valor):
    valor = str(valor or "").strip()
    return f"tok_{secrets.token_urlsafe(18)}_{valor[-4:]}" if valor else ""


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
    if medio.tipo == "TARJETA_CREDITO":
        _upsert_child(
            TarjetaCredito, medio, {
                "nombre_titular": datos.get("nombreTitular", ""),
                "alias_tarjeta": datos.get("aliasTarjeta") or medio.alias,
                "numero_tarjeta": _tokenizar(datos.get("numeroTarjeta")),
                "fecha_vencimiento": datos.get("fechaVencimiento", ""),
                "codigo_seguridad": _tokenizar(datos.get("codigoSeguridad")),
            }
        )
    elif medio.tipo == "TRANSFERENCIA":
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
    return {
        "id": medio.id,
        "tipo": medio.tipo,
        "tipoTexto": TIPOS.get(medio.tipo, ("Sin tipo", None))[0],
        "alias": medio.alias,
        "activo": medio.activo,
        "usuario": medio.usuario.get_username(),
        "detalle": detalle,
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
        medio.delete()
        return JsonResponse({}, status=204)

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
        "nombreTitular", "aliasTarjeta", "numeroTarjeta", "fechaVencimiento",
        "codigoSeguridad", "numeroCuentaOrigen", "bancoOrigen", "titularOrigen",
        "numeroCuentaDestino", "bancoDestino", "titularDestino", "plataforma",
        "identificadorCuenta", "titular",
    )):
        _guardar_detalle(medio, datos)
    return JsonResponse(_a_dict(medio))
