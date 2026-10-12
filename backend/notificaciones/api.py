"""API de la campanita: las notificaciones del usuario logueado."""
import json

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from monedas.models import Moneda

from .models import Notificacion, PreferenciaNotificaciones

CANTIDAD = 30


def _a_dict(n):
    return {
        "id": n.id,
        "tipo": n.tipo,
        "titulo": n.titulo,
        "mensaje": n.mensaje,
        "datos": n.datos,
        "leida": n.leida,
        "fecha": n.fecha.isoformat(),
    }


@require_GET
@login_required
def lista(request):
    """Las últimas notificaciones del usuario y cuántas tiene sin leer."""
    propias = Notificacion.objects.filter(usuario=request.user)
    return JsonResponse({
        "noLeidas": propias.filter(leida=False).count(),
        "notificaciones": [_a_dict(n) for n in propias[:CANTIDAD]],
    })


@require_POST
@login_required
def marcar_leidas(request):
    """Marca como leídas las indicadas en ``ids``, o todas si no se manda ``ids``."""
    try:
        datos = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"error": "El cuerpo debe ser JSON válido."}, status=400)
    propias = Notificacion.objects.filter(usuario=request.user, leida=False)
    if isinstance(datos.get("ids"), list):
        propias = propias.filter(pk__in=datos["ids"])
    propias.update(leida=True)
    return JsonResponse({"noLeidas": Notificacion.objects.filter(usuario=request.user, leida=False).count()})


def _preferencias_a_dict(usuario):
    preferencia = PreferenciaNotificaciones.objects.filter(usuario=usuario).first()
    return {
        "compras": preferencia.compras if preferencia else True,
        "ventas": preferencia.ventas if preferencia else True,
        "cotizaciones": preferencia.cotizaciones if preferencia else True,
        # Vacío = todas las divisas.
        "monedas": sorted(m.codigo for m in preferencia.monedas.all()) if preferencia else [],
        # Las divisas que se pueden seguir (la moneda local no cotiza).
        "monedasDisponibles": [
            {"codigo": m.codigo, "nombre": m.nombre}
            for m in Moneda.objects.filter(activo=True, es_local=False).order_by("codigo")
        ],
    }


@require_http_methods(["GET", "PUT"])
@login_required
def preferencias(request):
    """Las suscripciones del usuario: qué notificaciones quiere recibir.

    ``PUT`` con ``{"compras", "ventas", "cotizaciones", "monedas": ["USD"]}``
    (``monedas`` vacío = todas las divisas). Los campos que no vienen no cambian.
    """
    if request.method == "GET":
        return JsonResponse(_preferencias_a_dict(request.user))
    try:
        datos = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"error": "El cuerpo debe ser JSON válido."}, status=400)
    preferencia, _ = PreferenciaNotificaciones.objects.get_or_create(usuario=request.user)
    for campo in ("compras", "ventas", "cotizaciones"):
        if campo in datos:
            setattr(preferencia, campo, bool(datos[campo]))
    preferencia.save()
    if "monedas" in datos:
        codigos = datos["monedas"] if isinstance(datos["monedas"], list) else []
        elegidas = list(Moneda.objects.filter(codigo__in=codigos, es_local=False))
        if len(elegidas) != len(set(codigos)):
            return JsonResponse({"error": "Alguna de las divisas elegidas no existe."}, status=400)
        preferencia.monedas.set(elegidas)
    return JsonResponse(_preferencias_a_dict(request.user))
