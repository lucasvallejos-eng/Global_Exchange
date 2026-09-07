"""Vistas de la API de Clientes (CRUD) y del listado de usuarios asociables."""
import json

from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_http_methods

from cuentas.decorators import rol_requerido

from .models import Cliente


def _cliente_a_dict(cliente):
    # "segmento" y "porcentajeComision" se agregaron después: son campos
    # nuevos que se suman a la respuesta, así que la maqueta que no los
    # conoce los ignora y sigue funcionando igual.
    return {
        "id": cliente.id,
        "nombre": cliente.nombre,
        "tipo": cliente.tipo,
        "direccion": cliente.direccion,
        "cuentaAcreditar": cliente.cuenta_acreditar,
        "correo": cliente.correo,
        "usuarios": list(cliente.usuarios.values_list("id", flat=True)),
        "segmento": cliente.segmento_id,
        "porcentajeComision": (
            str(cliente.porcentaje_comision)
            if cliente.porcentaje_comision is not None else None
        ),
    }


def _body_json(request):
    try:
        return json.loads(request.body or b"{}")
    except json.JSONDecodeError:
        return {}


@login_required
@require_http_methods(["GET", "POST"])
@csrf_protect
def clientes_lista(request):
    if request.method == "GET":
        clientes = Cliente.objects.prefetch_related("usuarios").all()
        return JsonResponse([_cliente_a_dict(c) for c in clientes], safe=False)

    return _crear_cliente(request)


@rol_requerido("administrador")
def _crear_cliente(request):
    datos = _body_json(request)
    cliente = Cliente.objects.create(
        nombre=datos.get("nombre", ""),
        tipo=datos.get("tipo", Cliente.Tipo.FISICA),
        direccion=datos.get("direccion", ""),
        cuenta_acreditar=datos.get("cuentaAcreditar", ""),
        correo=datos.get("correo", ""),
        segmento_id=datos.get("segmento") or None,
    )
    cliente.usuarios.set(datos.get("usuarios", []))
    return JsonResponse(_cliente_a_dict(cliente), status=201)


@login_required
@require_http_methods(["GET", "PATCH", "DELETE"])
@csrf_protect
def clientes_detalle(request, pk):
    try:
        cliente = Cliente.objects.get(pk=pk)
    except Cliente.DoesNotExist:
        return JsonResponse({"detail": "No encontrado."}, status=404)

    if request.method == "GET":
        return JsonResponse(_cliente_a_dict(cliente))
    if request.method == "PATCH":
        return _actualizar_cliente(request, cliente)
    return _borrar_cliente(request, cliente)


@rol_requerido("administrador")
def _actualizar_cliente(request, cliente):
    datos = _body_json(request)
    for campo, atributo in (
        ("nombre", "nombre"),
        ("tipo", "tipo"),
        ("direccion", "direccion"),
        ("cuentaAcreditar", "cuenta_acreditar"),
        ("correo", "correo"),
        ("segmento", "segmento_id"),
    ):
        if campo not in datos:
            continue
        valor = datos[campo]
        # El segmento admite null (o cadena vacía) para dejar al cliente sin
        # segmento asignado; el resto de los campos se copia tal cual.
        if campo == "segmento" and not valor:
            valor = None
        setattr(cliente, atributo, valor)
    cliente.save()
    if "usuarios" in datos:
        cliente.usuarios.set(datos["usuarios"])
    return JsonResponse(_cliente_a_dict(cliente))


@rol_requerido("administrador")
def _borrar_cliente(request, cliente):
    cliente.delete()
    return JsonResponse({}, status=204)


@login_required
def usuarios_lista(request):
    """Usuarios que se pueden asociar como 'usuarios asociados' de una empresa."""
    User = get_user_model()
    usuarios = User.objects.all().order_by("username")
    data = [
        {
            "id": u.id,
            "username": u.username,
            "nombre": u.get_full_name() or u.username,
            "email": u.email,
        }
        for u in usuarios
    ]
    return JsonResponse(data, safe=False)
