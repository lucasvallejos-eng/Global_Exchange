"""API JSON de medios de pago para la maqueta.

Espeja lo que ya hace ``medios_pago/views.py`` con plantillas, incluida la
regla de visibilidad: un **cliente** ve solo los suyos; administrador y cajero
ven todos.

La maqueta original listaba un catálogo inventado ("Transferencia Bancaria",
"TC", "Billetera Digital") que no existe como tabla. Lo que sí existe son los
medios de pago cargados por cada usuario, con su tipo tomado de
``MedioPago.TIPO_CHOICES``; eso es lo que se expone acá.
"""
import json

from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

from cuentas.decorators import rol_requerido

from .models import MedioPago


def _a_dict(medio):
    return {
        "id": medio.id,
        "tipo": medio.tipo,
        "tipoTexto": medio.get_tipo_display(),
        "alias": medio.alias,
        "numero": medio.numero_cuenta_o_tarjeta,
        "banco": medio.banco_o_proveedor or "",
        "activo": medio.activo,
        "usuario": medio.usuario.get_username(),
    }


def _cuerpo(request):
    try:
        return json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return {}


def _visibles_para(usuario):
    """Un cliente ve solo sus medios; administrador y cajero ven todos."""
    if usuario.groups.filter(name="cliente").exists() and not usuario.groups.filter(
        name__in=("administrador", "cajero")
    ).exists():
        return MedioPago.objects.filter(usuario=usuario)
    return MedioPago.objects.all()


@require_http_methods(["GET", "POST"])
@rol_requerido("cliente", "administrador", "cajero")
def medios_lista(request):
    if request.method == "GET":
        medios = _visibles_para(request.user).select_related("usuario")
        return JsonResponse(
            {
                "tipos": [{"valor": v, "texto": t} for v, t in MedioPago.TIPO_CHOICES],
                "medios": [_a_dict(m) for m in medios],
            }
        )
    return _crear(request)


@rol_requerido("cliente", "administrador")
def _crear(request):
    datos = _cuerpo(request)
    alias = (datos.get("alias") or "").strip()
    tipo = (datos.get("tipo") or "").strip()

    if not alias or not tipo:
        return JsonResponse({"error": "El alias y el tipo son obligatorios."}, status=400)
    if tipo not in dict(MedioPago.TIPO_CHOICES):
        return JsonResponse({"error": f"Tipo no válido: {tipo}."}, status=400)

    medio = MedioPago.objects.create(
        usuario=request.user,
        tipo=tipo,
        alias=alias,
        numero_cuenta_o_tarjeta=(datos.get("numero") or "").strip(),
        banco_o_proveedor=(datos.get("banco") or "").strip() or None,
        activo=bool(datos.get("activo", True)),
    )
    return JsonResponse(_a_dict(medio), status=201)


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
    if "tipo" in datos:
        if datos["tipo"] not in dict(MedioPago.TIPO_CHOICES):
            return JsonResponse({"error": f"Tipo no válido: {datos['tipo']}."}, status=400)
        medio.tipo = datos["tipo"]
    if "numero" in datos:
        medio.numero_cuenta_o_tarjeta = (datos["numero"] or "").strip()
    if "banco" in datos:
        medio.banco_o_proveedor = (datos["banco"] or "").strip() or None
    if "activo" in datos:
        medio.activo = bool(datos["activo"])

    medio.save()
    return JsonResponse(_a_dict(medio))
